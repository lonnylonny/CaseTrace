"""M5-02 数据源接缝：核心接受已读回快照，CLI 负责连接与参数。

这里的 `LoadedSnapshot` 由文件对象合成，用来检查接缝行为，不连接数据库；
真实 PostgreSQL 上的文件／DB 对照放在 `tests/storage/test_answer_integration.py`。
"""

from dataclasses import replace
from datetime import date, datetime
import json
from pathlib import Path

import pytest

from casetrace import main
from casetrace.answer import cli
from casetrace.answer import context as context_module
from casetrace.answer.cli import (
    EXIT_USAGE,
    STATUS_OK,
    AnswerOutcome,
    format_answer_text,
    run_answer_question,
)
from casetrace.answer.context import (
    DATA_SOURCE_FILE,
    DATA_SOURCE_POSTGRES,
    DEV_V3_SNAPSHOT,
    prepare_answer_run,
)
from casetrace.answer.model import ModelCallError, OfflineChatModel, TokenUsage
from casetrace.demo import load_validated_dataset
from casetrace.storage import LoadedSnapshot, StoredSnapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_KNOWN_AT = date(2026, 9, 15)


@pytest.fixture
def loaded_snapshot(answer_dataset, reference_path):
    """把文件对象装进公开的 `LoadedSnapshot`，模拟一次数据库读回的结果。

    身份字段用记录在案的 `DEV_V3_SNAPSHOT`（CLI 数据库路线的默认请求），
    records / reference / payload 则来自三条 Case 的自造语料，便于检查接缝行为。
    """

    dataset_path, _ = answer_dataset
    records, payload, reference = load_validated_dataset(dataset_path, reference_path)
    return LoadedSnapshot(
        records=records, reference=reference, payload=payload,
        snapshot=StoredSnapshot(
            snapshot_id=DEV_V3_SNAPSHOT.snapshot_id,
            known_at=DEV_V3_SNAPSHOT.known_at,
            # 库内保存的是原始导入路径：表示来源位置，不代表本次读了这些文件。
            dataset_path=str(dataset_path),
            dataset_sha256=DEV_V3_SNAPSHOT.dataset_sha256,
            reference_path=str(reference_path),
            reference_sha256=DEV_V3_SNAPSHOT.reference_sha256,
            split=payload["split"],
            review_status=payload["review_status"],
            basis=DEV_V3_SNAPSHOT.basis,
            content_digest="test-content-digest",
            digest_version="content-digest-v2",
            imported_at=datetime(2026, 10, 5, 12, 0, 0),
        ),
        counts={"cases": len(records["cases"])},
    )


def _file_run(answer_dataset, reference_path, make_snapshot, query, **kwargs):
    dataset_path, _ = answer_dataset
    return prepare_answer_run(
        query, kwargs.pop("known_at", SNAPSHOT_KNOWN_AT),
        dataset_path=dataset_path, reference_path=reference_path,
        snapshot=make_snapshot(dataset_path), **kwargs,
    )


def _db_run(loaded_snapshot, query, **kwargs):
    return prepare_answer_run(
        query, kwargs.pop("known_at", SNAPSHOT_KNOWN_AT),
        loaded_snapshot=loaded_snapshot, **kwargs,
    )


# ── 核心接缝：两条路线汇入同一次检索 ────────────────────────────────────

def test_db_route_reuses_ranking_and_records_source_metadata(
    answer_dataset, reference_path, make_snapshot, answer_query, loaded_snapshot,
):
    file_run = _file_run(answer_dataset, reference_path, make_snapshot, answer_query)
    db_run = _db_run(loaded_snapshot, answer_query, db_schema="casetrace_test")

    assert db_run.run_metadata["ranking"] == file_run.run_metadata["ranking"]
    assert db_run.inputs.hits == file_run.inputs.hits
    assert db_run.run_metadata["retrieval"] == file_run.run_metadata["retrieval"]
    # 快照描述用库内实际读回值，与请求的 DEV_V3_SNAPSHOT 一致。
    assert db_run.run_metadata["snapshot"] == {
        "snapshot_id": DEV_V3_SNAPSHOT.snapshot_id,
        "known_at": DEV_V3_SNAPSHOT.known_at.isoformat(),
        "basis": DEV_V3_SNAPSHOT.basis,
        "dataset_sha256": DEV_V3_SNAPSHOT.dataset_sha256,
        "reference_sha256": DEV_V3_SNAPSHOT.reference_sha256,
    }

    corpus = db_run.run_metadata["corpus"]
    assert corpus["data_source"] == DATA_SOURCE_POSTGRES
    assert corpus["schema"] == "casetrace_test"
    assert corpus["content_digest"] == "test-content-digest"
    assert corpus["digest_version"] == "content-digest-v2"
    assert corpus["case_count"] == file_run.run_metadata["corpus"]["case_count"]
    assert file_run.run_metadata["corpus"]["data_source"] == DATA_SOURCE_FILE
    # 未显式指定 schema 时用项目默认值，只作记录。
    assert _db_run(loaded_snapshot, answer_query).run_metadata["corpus"]["schema"] == "casetrace"


def test_db_route_does_not_open_dataset_or_reference_files(
    answer_dataset, reference_path, make_snapshot, answer_query, loaded_snapshot, tmp_path,
):
    missing = tmp_path / "should-not-be-read.json"
    file_run = _file_run(answer_dataset, reference_path, make_snapshot, answer_query)

    db_run = prepare_answer_run(
        answer_query, SNAPSHOT_KNOWN_AT, dataset_path=missing,
        reference_path=missing.with_suffix(".xlsx"), loaded_snapshot=loaded_snapshot,
    )

    assert db_run.run_metadata["ranking"] == file_run.run_metadata["ranking"]
    assert not missing.exists()


def test_db_route_does_not_rerun_file_source_checks(
    answer_dataset, reference_path, make_snapshot, answer_query, loaded_snapshot, monkeypatch,
):
    """库内内容与来源已随导入和读回核对；回答准备阶段不再调用文件来源校验。"""

    def explode(*args, **kwargs):
        raise AssertionError("数据库路线不应重跑来源记录校验")

    monkeypatch.setattr(context_module, "check_source_records", explode)

    with pytest.raises(AssertionError):
        _file_run(answer_dataset, reference_path, make_snapshot, answer_query)
    assert _db_run(loaded_snapshot, answer_query).run_metadata["ranking"]


def test_file_route_still_needs_both_paths(answer_query, loaded_snapshot):
    with pytest.raises(ValueError, match="--data 与 --reference"):
        prepare_answer_run(answer_query, SNAPSHOT_KNOWN_AT)


@pytest.mark.parametrize("field, value", [
    ("snapshot_id", "other-snapshot"),
    ("known_at", date(2026, 9, 16)),
    ("dataset_sha256", "0" * 64),
    ("reference_sha256", "0" * 64),
    ("basis", "别的依据"),
])
def test_db_route_rejects_snapshot_not_matching_request(
    answer_query, loaded_snapshot, field, value,
):
    requested = replace(DEV_V3_SNAPSHOT, **{field: value})
    with pytest.raises(ValueError, match="库内描述与本次请求的快照不一致"):
        prepare_answer_run(answer_query, SNAPSHOT_KNOWN_AT, snapshot=requested,
                           loaded_snapshot=loaded_snapshot)


def test_db_route_rejects_known_at_outside_recorded_snapshot(answer_query, loaded_snapshot):
    with pytest.raises(ValueError, match="不被当前记录的可用性快照支持"):
        _db_run(loaded_snapshot, answer_query, known_at=date(2026, 9, 16))


def test_db_route_rejects_case_detected_after_snapshot(answer_query, loaded_snapshot):
    records = dict(loaded_snapshot.records)
    records["details"] = [replace(detail, detection_time=date(2026, 9, 16))
                          for detail in records["details"]]
    later = replace(loaded_snapshot, records=records)

    with pytest.raises(ValueError, match="时点一致性"):
        _db_run(later, answer_query)


# ── CLI 适配：参数、单次读取与前提失败 ─────────────────────────────────

def answer_text(case_id="C1") -> str:
    """符合回答契约的最小回答，用于让数据库路线跑到成功状态。"""

    checkpoint = f"E{case_id[1:]}"
    return json.dumps({
        "case_answers": [{
            "case_id": case_id,
            "relevance_reason": "同产品且异常描述相同",
            "query_facts": ["涉及产品 P1"],
            "case_facts": ["焊线脱落，表面污染"],
            "historical_root_cause": "表面污染",
            "historical_corrective_action": None,
            "historical_evidences": [{"checkpoint_id": checkpoint, "result": "观察到表面污染"}],
            "sources": [
                {"case_id": case_id, "field": "abnormal_description"},
                {"case_id": case_id, "field": f"checkpoint:{checkpoint}"},
            ],
        }],
        "skipped_candidates": [],
        "current_gaps": [],
        "insufficiency": None,
    }, ensure_ascii=False)


class CannedModel(OfflineChatModel):
    """离线替身：回放固定回答，并带真实适配器才有的请求参数属性。"""

    def __init__(self, text, *, model_id="offline-stub"):
        super().__init__(text, model_id=model_id,
                           usage=TokenUsage(prompt_tokens=120, completion_tokens=60,
                                            total_tokens=180))
        self.max_tokens = 2048
        self.temperature = 0.0


class FailingModel:
    """调用直接失败的替身；用来确认数据库路线的失败状态不变。"""

    model_id = "failing-stub"

    def complete(self, messages, *, max_tokens=None, temperature=None):
        raise ModelCallError("DeepSeek 调用失败：模拟超时")


@pytest.fixture
def stub_model(monkeypatch):
    """替换真实模型工厂，并记录是否真的构造过模型。"""

    holder = {"model": CannedModel(answer_text("C1")), "factory_calls": 0}

    def factory(name):
        holder["factory_calls"] += 1
        return holder["model"]

    monkeypatch.setattr(cli, "build_model", factory)
    return holder


@pytest.fixture
def counting_loader(monkeypatch, loaded_snapshot):
    """把数据库读回换成计数假实现，并记录传入的 schema。"""

    calls = []

    def loader(schema):
        calls.append(schema)
        return loaded_snapshot

    monkeypatch.setattr(cli, "load_database_snapshot", loader)
    return calls


def _invoke_cli(monkeypatch, capsys, *arguments):
    """在仓库根目录调用 CLI；返回 (退出码, stdout, stderr)。"""

    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr("sys.argv", ["casetrace", *arguments])
    try:
        code = main()
    except SystemExit as exit_info:
        code = exit_info.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ── CLI 适配：参数、单次读取与前提失败 ─────────────────────────────────

def test_cli_postgres_check_only_reads_database_once(
    tmp_path, monkeypatch, capsys, stub_model, counting_loader,
):
    missing = tmp_path / "no-such-file.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query-id", "Q-TEST", "--check-only",
        "--data", str(missing), "--reference", str(missing),
    )

    assert code == 0 and stderr == ""
    assert counting_loader == ["casetrace"]
    assert stub_model["factory_calls"] == 0
    assert "数据源：PostgreSQL schema=casetrace" in stdout
    assert "快照：dev-v3-2026-09-15" in stdout
    assert "--check-only：未调用模型，未写运行记录。" in stdout


def test_cli_postgres_full_run_reads_database_once_and_records_source(
    tmp_path, monkeypatch, capsys, stub_model, counting_loader, loaded_snapshot,
):
    output = tmp_path / "db-run.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--db-schema", "casetrace_test", "--query-id", "Q-TEST",
        "--output", str(output),
    )

    assert code == 0 and stderr == ""
    assert counting_loader == ["casetrace_test"]
    assert stub_model["factory_calls"] == 1
    assert "数据源：PostgreSQL schema=casetrace_test" in stdout
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == STATUS_OK
    assert record["corpus"]["data_source"] == DATA_SOURCE_POSTGRES
    assert record["corpus"]["schema"] == "casetrace_test"
    assert record["corpus"]["content_digest"] == "test-content-digest"
    # 记录里保留库内原始导入路径，来源字段完整，但不含连接信息。
    assert record["corpus"]["dataset_path"] == loaded_snapshot.snapshot.dataset_path
    serialized = json.dumps(record, ensure_ascii=False)
    assert "postgresql://" not in serialized and "password" not in serialized.lower()


def test_cli_postgres_explicit_query_needs_no_dataset_file(
    tmp_path, monkeypatch, capsys, stub_model, counting_loader,
):
    missing = tmp_path / "no-such-file.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query", "焊线脱落，已排除运输碰伤", "--known-at", "2026-09-15", "--check-only",
        "--data", str(missing), "--reference", str(missing),
    )

    assert code == 0 and stderr == ""
    assert counting_loader == ["casetrace"]
    assert "焊线脱落，已排除运输碰伤" in stdout


def test_cli_postgres_unknown_query_id_lists_available_queries(
    monkeypatch, capsys, stub_model, counting_loader,
):
    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query-id", "Q999", "--check-only",
    )

    assert code == EXIT_USAGE and stdout == ""
    assert "Q999" in stderr and "Q-TEST" in stderr


def test_cli_postgres_premise_failure_stops_before_model(
    tmp_path, monkeypatch, capsys, stub_model,
):
    output = tmp_path / "should-not-exist.json"

    def loader(schema):
        raise ValueError(f"schema {schema} 没有已记录的快照；请先运行 storage import")

    monkeypatch.setattr(cli, "load_database_snapshot", loader)

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query-id", "Q-TEST", "--output", str(output),
    )

    assert code == EXIT_USAGE and stdout == ""
    assert "运行前提不满足" in stderr and "没有已记录的快照" in stderr
    assert stub_model["factory_calls"] == 0
    assert not output.exists()


def test_cli_postgres_invalid_connection_does_not_echo_password(
    tmp_path, monkeypatch, capsys, stub_model,
):
    password = "DUMMY%REVIEW_PASSWORD"
    url = f"postgresql://review_user:{password}@127.0.0.1:1/db"
    monkeypatch.setenv("CASETRACE_DATABASE_URL", url)
    monkeypatch.setattr("casetrace.storage.connection.load_local_env", lambda: None)
    output = tmp_path / "should-not-exist.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query-id", "Q005", "--output", str(output),
    )

    assert code == EXIT_USAGE and stdout == ""
    assert password not in stderr and url not in stderr
    assert "ProgrammingError" in stderr and "CASETRACE_DATABASE_URL" in stderr
    assert stub_model["factory_calls"] == 0
    assert not output.exists()


def test_cli_postgres_known_at_outside_snapshot_stops_before_model(
    monkeypatch, capsys, stub_model, counting_loader,
):
    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query", "焊线脱落", "--known-at", "2026-09-16", "--check-only",
    )

    assert code == EXIT_USAGE and stdout == ""
    assert "运行前提不满足" in stderr and "快照" in stderr
    assert stub_model["factory_calls"] == 0


def test_cli_postgres_empty_hits_do_not_call_model(
    monkeypatch, capsys, stub_model, counting_loader,
):
    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query", "zzz 与语料没有词项重合 qqqq", "--known-at", "2026-09-15",
    )

    assert code == 0 and stderr == ""
    assert "（本次没有候选）" in stdout
    assert stub_model["factory_calls"] == 0


def test_cli_postgres_keeps_model_failure_status(
    tmp_path, monkeypatch, capsys, stub_model, counting_loader,
):
    stub_model["model"] = FailingModel()
    output = tmp_path / "db-failed.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--query-id", "Q-TEST", "--output", str(output),
    )

    assert code == 3 and stdout == ""
    assert "运行状态：model_failed" in stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "model_failed"


def test_file_route_is_still_the_default(monkeypatch, capsys, stub_model):
    code, stdout, _ = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--check-only",
    )

    assert code == 0
    assert "数据源：文件" in stdout
    assert "快照：dev-v3-2026-09-15" in stdout


def test_cli_explicit_file_source_matches_default(
    monkeypatch, capsys, stub_model,
):
    """显式 `--data-source file` 与默认行为一致（保持旧调用兼容）。"""

    code, stdout, _ = _invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "file",
        "--query-id", "Q005", "--check-only",
    )

    assert code == 0 and "数据源：文件" in stdout


def test_file_route_does_not_need_database(monkeypatch, capsys, stub_model):
    """默认 file 路线不依赖数据库配置，也不会去连数据库。"""

    def unexpected_loader(schema):
        raise AssertionError("文件路线不应读取数据库")

    monkeypatch.delenv("CASETRACE_DATABASE_URL", raising=False)
    monkeypatch.setattr(cli, "load_database_snapshot", unexpected_loader)

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--check-only",
    )

    assert code == 0 and stderr == ""
    assert "数据源：文件" in stdout


def test_text_renderer_reads_old_record_without_data_source_as_file():
    """旧运行记录没有 data_source：仍可展示并按文件来源理解，不改写历史产物。"""

    record = json.loads(
        (PROJECT_ROOT / "results/m4/dev-v3-answer-v10/q001.json").read_text(encoding="utf-8")
    )
    assert "data_source" not in record["corpus"]

    text = format_answer_text(AnswerOutcome(status=record["status"], record=record,
                                            message="历史记录"))

    assert "数据源：文件" in text
    assert "运行状态：ok" in text


def test_application_run_records_database_source(
    answer_query, loaded_snapshot,
):
    """应用入口（API 可直接调用的那一层）也接受已读回快照并记录来源。"""

    outcome = run_answer_question(
        answer_query, SNAPSHOT_KNOWN_AT, loaded_snapshot=loaded_snapshot,
        db_schema="casetrace_test", query_id="Q-TEST",
        model_factory=lambda: CannedModel(answer_text("C1")),
    )

    assert outcome.status == STATUS_OK
    assert outcome.record["corpus"]["data_source"] == DATA_SOURCE_POSTGRES
    assert outcome.record["corpus"]["schema"] == "casetrace_test"
    assert "数据源：PostgreSQL schema=casetrace_test" in format_answer_text(outcome)
