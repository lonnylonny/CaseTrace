"""M5-02 真实 PostgreSQL 对照：文件与数据库两条回答路线必须等价。

只在真实测试库上运行（`CASETRACE_TEST_DATABASE_URL`），每个用例独占一个 schema；
缺库时为普通回归显式 skip，但本包验收要求这些对照真实执行。
"""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import uuid

import pytest
from psycopg import sql

from casetrace import main
from casetrace.answer import cli
from casetrace.answer.cli import (
    EXIT_USAGE,
    STATUS_MODEL_FAILED,
    STATUS_NO_HITS,
    STATUS_OK,
    format_answer_text,
    run_answer_question,
)
from casetrace.answer.context import (
    DEV_V3_SNAPSHOT,
    build_evidence_context,
    context_to_payload,
    prepare_answer_run,
)
from casetrace.answer.model import ModelCallError, OfflineChatModel
from casetrace.storage import (
    DATABASE_URL_ENV,
    TEST_DATABASE_URL_ENV,
    import_snapshot,
    initialize_schema,
    load_snapshot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "data/dev/demo-v3.json"
REFERENCE = PROJECT_ROOT / (
    "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
)
V10_DIR = PROJECT_ROOT / "results/m4/dev-v3-answer-v10"
QUERY_IDS = ("q001", "q002", "q003", "q004", "q005")


@pytest.fixture
def database_snapshot(storage_connection, scratch_schema):
    """在独占 schema 里导入 dev-v3 快照，返回 (连接, schema 名, 已读回快照)。"""

    initialize_schema(storage_connection, schema=scratch_schema)
    import_snapshot(
        storage_connection, DATASET, REFERENCE,
        snapshot=DEV_V3_SNAPSHOT, schema=scratch_schema,
    )
    loaded = load_snapshot(storage_connection, schema=scratch_schema)
    return storage_connection, scratch_schema, loaded


def saved_v10(query_id: str) -> dict:
    """M4-04 保存的 v10 运行记录：固定的输入、排名、上下文与实际消息。"""

    return json.loads((V10_DIR / f"{query_id}.json").read_text(encoding="utf-8"))


def query_of(record: dict) -> tuple[str, date]:
    return record["query"]["text"], date.fromisoformat(record["query"]["known_at"])


def context_payload(run) -> dict:
    return context_to_payload(build_evidence_context(
        run.inputs.query, run.inputs.hits, run.inputs.records,
        run.inputs.reference, run.inputs.sources,
    ))


def invoke_cli(monkeypatch, capsys, *arguments):
    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr("sys.argv", ["casetrace", *arguments])
    try:
        code = main()
    except SystemExit as exit_info:
        code = exit_info.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ── 1. 五 Query：文件与数据库排名、上下文、来源一致，并与 v10 对照 ──────

def test_five_queries_match_between_file_and_database(database_snapshot):
    _, schema, loaded = database_snapshot

    for query_id in QUERY_IDS:
        record = saved_v10(query_id)
        query, known_at = query_of(record)
        file_run = prepare_answer_run(
            query, known_at, dataset_path=DATASET, reference_path=REFERENCE,
        )
        db_run = prepare_answer_run(
            query, known_at, loaded_snapshot=loaded, db_schema=schema,
        )

        assert db_run.run_metadata["ranking"] == file_run.run_metadata["ranking"]
        assert db_run.run_metadata["ranking"] == record["ranking"]
        assert db_run.run_metadata["ranking"], f"{query_id} 应有候选"
        assert context_payload(db_run) == context_payload(file_run)
        assert context_payload(db_run) == record["context"]

        file_corpus = file_run.run_metadata["corpus"]
        db_corpus = db_run.run_metadata["corpus"]
        assert file_corpus["data_source"] == "file"
        assert db_corpus["data_source"] == "postgres"
        assert db_corpus["schema"] == schema
        assert db_corpus["content_digest"] == loaded.snapshot.content_digest
        assert db_corpus["digest_version"] == loaded.snapshot.digest_version
        assert db_corpus["case_count"] == file_corpus["case_count"] == 9
        # 数据库路线保存原始导入路径作为来源位置，但本次没有读取文件。
        assert db_corpus["dataset_path"] == str(DATASET)
        assert db_corpus["reference_path"] == str(REFERENCE)
        assert db_run.run_metadata["snapshot"] == file_run.run_metadata["snapshot"]


# ── 2. 响应回放：两条路线发送的消息与结果一致，并与 v10 对照 ─────────────

def body_without_source_line(text: str) -> str:
    """展示正文去掉「数据源」一行：该行按路线各自校验，其余必须一致。"""

    return "\n".join(line for line in text.splitlines() if not line.startswith("数据源："))


def test_offline_replay_of_v10_responses_is_equivalent(database_snapshot):
    _, schema, loaded = database_snapshot

    for query_id in QUERY_IDS:
        record = saved_v10(query_id)
        query, known_at = query_of(record)
        query_id_text = record["query"]["query_id"]
        file_model = OfflineChatModel(record["answer_text"])
        db_model = OfflineChatModel(record["answer_text"])

        file_outcome = run_answer_question(
            query, known_at, dataset_path=DATASET, reference_path=REFERENCE,
            model_factory=lambda: file_model, query_id=query_id_text,
        )
        db_outcome = run_answer_question(
            query, known_at, loaded_snapshot=loaded, db_schema=schema,
            model_factory=lambda: db_model, query_id=query_id_text,
        )

        assert file_outcome.status == db_outcome.status == STATUS_OK
        assert db_model.calls[0]["messages"] == file_model.calls[0]["messages"]
        assert db_outcome.record["request"]["sent_messages"] == record["request"]["sent_messages"]
        assert (db_outcome.record["request"]["sent_messages"]
                == file_outcome.record["request"]["sent_messages"])
        assert json.loads(json.dumps(db_outcome.record["answer"])) == record["answer"]
        assert db_outcome.record["answer_text"] == record["answer_text"]
        assert db_outcome.record["citations"] == record["citations"]
        assert db_outcome.record["citations"] == file_outcome.record["citations"]
        assert db_outcome.record["status"] == file_outcome.record["status"]
        assert (body_without_source_line(format_answer_text(db_outcome))
                == body_without_source_line(format_answer_text(file_outcome)))
        # 「数据源」一行按各自路线校验；没有这一行时上面的比较会是空比较。
        assert f"数据源：PostgreSQL schema={schema}" in format_answer_text(db_outcome)
        assert "数据源：文件" in format_answer_text(file_outcome)
        # 来源元数据按各自路线验证；记录可序列化且不含连接信息。
        assert db_outcome.record["corpus"]["schema"] == schema
        serialized = json.dumps(db_outcome.record, ensure_ascii=False)
        assert "postgresql://" not in serialized and "password" not in serialized.lower()


# ── 3. 数据库独立性与单次读取 ────────────────────────────────────────────

def test_cli_database_route_is_independent_of_files_and_reads_once(
    database_snapshot, tmp_path, monkeypatch, capsys,
):
    connection, schema, _ = database_snapshot
    calls = []

    def counting_loader(name):
        calls.append(name)
        return load_snapshot(connection, schema=name)

    monkeypatch.setattr(cli, "load_database_snapshot", counting_loader)
    missing = tmp_path / "no-such-file.json"

    code, stdout, stderr = invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--db-schema", schema, "--query-id", "Q005", "--check-only",
        "--data", str(missing), "--reference", str(missing),
    )

    assert code == 0 and stderr == ""
    assert calls == [schema]
    assert f"数据源：PostgreSQL schema={schema}" in stdout
    assert "候选排名：1.C007 > 2.C001 > 3.C004 > 4.C003" in stdout
    assert not missing.exists()

    # 完整回答同样只读回一次（示例解析与准备复用同一个快照对象）。
    saved = saved_v10("q005")
    monkeypatch.setattr(cli, "build_model",
                        lambda name: OfflineChatModel(saved["answer_text"]))
    output = tmp_path / "db-q005.json"
    code, _, stderr = invoke_cli(
        monkeypatch, capsys, "answer", "--data-source", "postgres",
        "--db-schema", schema, "--query-id", "Q005", "--output", str(output),
    )

    assert code == 0 and stderr == ""
    assert calls == [schema, schema]
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == STATUS_OK
    assert record["corpus"]["data_source"] == "postgres"
    assert record["corpus"]["schema"] == schema




# ── 4. 代表性边界：空命中、模型失败、快照与前提失败 ───────────────────────

class FailingModel:
    """调用直接失败的替身。"""

    model_id = "failing-stub"

    def complete(self, messages, *, max_tokens=None, temperature=None):
        raise ModelCallError("DeepSeek 调用失败：模拟超时")


def no_model():
    raise AssertionError("这条路线不应构造模型")


def test_database_route_empty_hits_skip_model(database_snapshot):
    _, schema, loaded = database_snapshot

    outcome = run_answer_question(
        "zzz 与语料没有词项重合 qqqq", DEV_V3_SNAPSHOT.known_at,
        loaded_snapshot=loaded, db_schema=schema, model_factory=no_model,
    )

    assert outcome.status == STATUS_NO_HITS
    assert outcome.record["response"]["called_model"] is False


def test_database_route_keeps_model_failure_status(database_snapshot):
    _, schema, loaded = database_snapshot

    outcome = run_answer_question(
        *query_of(saved_v10("q005")), loaded_snapshot=loaded, db_schema=schema,
        model_factory=FailingModel, query_id="Q005",
    )

    assert outcome.status == STATUS_MODEL_FAILED
    assert outcome.record["error"]["type"] == "ModelCallError"


def test_database_route_rejects_known_at_before_model(database_snapshot):
    _, schema, loaded = database_snapshot
    query, _ = query_of(saved_v10("q005"))

    with pytest.raises(ValueError, match="可用性快照"):
        prepare_answer_run(query, date(2026, 9, 16), loaded_snapshot=loaded, db_schema=schema)
    with pytest.raises(ValueError, match="可用性快照"):
        run_answer_question(query, date(2026, 9, 16), loaded_snapshot=loaded,
                            db_schema=schema, model_factory=no_model)


def test_cli_database_premise_failure_exits_before_model(
    database_snapshot, tmp_path, monkeypatch, capsys,
):
    """未导入快照的 schema：CLI 报可理解的前提错误，不调用模型、不写记录。"""

    connection, _, _ = database_snapshot
    empty_schema = f"casetrace_test_empty_{uuid.uuid4().hex[:6]}"
    initialize_schema(connection, schema=empty_schema)
    monkeypatch.setenv(DATABASE_URL_ENV, os.environ[TEST_DATABASE_URL_ENV])
    stub_calls = []
    monkeypatch.setattr(cli, "build_model", lambda name: stub_calls.append(name))
    output = tmp_path / "should-not-exist.json"

    try:
        code, stdout, stderr = invoke_cli(
            monkeypatch, capsys, "answer", "--data-source", "postgres",
            "--db-schema", empty_schema, "--query-id", "Q005", "--output", str(output),
        )
    finally:
        connection.execute(
            sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(empty_schema))
        )

    assert code == EXIT_USAGE and stdout == ""
    assert "运行前提不满足" in stderr and "没有已记录的快照" in stderr
    assert stub_calls == [] and not output.exists()
