"""M4-03 `casetrace answer`：状态、退出码、文本／JSON 同源与运行记录。

模型一律用离线替身注入，不访问网络、不需要凭据；真实调用证据另行记录，
不能用本文件替代。失败路径同样重要：失败不能伪装成「没有相关案例」或成功回答。
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import pytest

from casetrace import main
from casetrace.answer import cli
from casetrace.answer.cli import (
    EXIT_USAGE,
    STATUS_CITATION_FAILED,
    STATUS_FORMAT_FAILED,
    STATUS_MODEL_FAILED,
    STATUS_NO_HITS,
    STATUS_OK,
    format_answer_text,
    run_answer_question,
)
from casetrace.answer.model import (
    API_KEY_ENV,
    ModelCallError,
    OfflineChatModel,
    TokenUsage,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_KNOWN_AT = date(2026, 9, 15)
DEV_V3_RECORD_STRATEGY = "bm25_drop_negation_labels"


def answer_text(case_id="C1", *, checkpoint=None, sources=None, skipped=()) -> str:
    """符合回答契约的最小回答；参数用来制造伪造引用等失败场景。"""

    checkpoint = checkpoint or f"E{case_id[1:]}"
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
                {"case_id": item, "field": field}
                for item, field in (sources if sources is not None else [
                    (case_id, "abnormal_description"), (case_id, f"checkpoint:{checkpoint}"),
                ])
            ],
        }],
        "skipped_candidates": [{"case_id": item, "reason": "证据不足"} for item in skipped],
        "current_gaps": ["当前未提供客户批号"],
        "insufficiency": None,
    }, ensure_ascii=False)


class FailingModel:
    """调用直接失败的替身；用来确认失败不会被当成「没有候选」吞掉。"""

    model_id = "failing-stub"

    def complete(self, messages, *, max_tokens=None, temperature=None):
        raise ModelCallError("DeepSeek 调用失败：模拟超时")


class CannedModel(OfflineChatModel):
    """离线替身：回放固定回答，并带有真实适配器才有的请求参数属性。"""

    def __init__(self, text, *, model_id="offline-stub"):
        super().__init__(text, model_id=model_id,
                           usage=TokenUsage(prompt_tokens=120, completion_tokens=60,
                                            total_tokens=180))
        self.max_tokens = 2048
        self.temperature = 0.0


@pytest.fixture
def run_inputs(answer_dataset, reference_path, answer_query, make_snapshot):
    """自造语料上的运行参数：路径、测试快照与 Query。"""

    dataset_path, _ = answer_dataset
    return {
        "query": answer_query,
        "known_at": SNAPSHOT_KNOWN_AT,
        "dataset_path": dataset_path,
        "reference_path": reference_path,
        "snapshot": make_snapshot(dataset_path),
    }


def _invoke_cli(monkeypatch, capsys, *arguments):
    """在仓库根目录调用 CLI；返回 (退出码, stdout, stderr)。"""

    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr(sys, "argv", ["casetrace", *arguments])
    try:
        code = main()
    except SystemExit as exit_info:
        code = exit_info.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def stub_model(monkeypatch):
    """把真实模型工厂换成离线替身；返回一个可改内容的容器。"""

    holder = {"model": CannedModel(q005_answer_text())}

    def factory(name):
        holder["requested"] = name
        return holder["model"]

    monkeypatch.setattr(cli, "build_model", factory)
    return holder


def q005_answer_text():
    """Q005 的两个不同产品、同族候选均须采用；不靠待测匹配器造期望。"""
    payload = json.loads(answer_text("C007", checkpoint="E007"))
    payload["case_answers"].extend(json.loads(answer_text("C003", checkpoint="E003"))["case_answers"])
    return json.dumps(payload, ensure_ascii=False)


# ── 应用层：状态、记录与文本／JSON 同源 ──────────────────────────────────

def test_ok_run_records_answer_and_text_matches_record(run_inputs):
    model = CannedModel(answer_text("C1"))
    outcome = run_answer_question(model_factory=lambda: model, **run_inputs)

    assert outcome.status == STATUS_OK and outcome.exit_code == 0
    record = outcome.record
    assert record["status"] == STATUS_OK
    assert record["request"]["model_alias"] == "offline-stub"
    assert record["request"]["prompt_version"] == "grounded_answer_v10"
    assert record["request"]["max_tokens"] == 2048
    # 模型身份取响应字段；用量与耗时一起记录，便于复现。
    assert record["response"]["model"] == "offline-stub"
    assert record["response"]["called_model"] is True
    assert record["response"]["usage"]["total_tokens"] == 180
    assert record["response"]["elapsed_seconds"] >= 0
    assert record["citations"] == {"checked": 4, "issue_count": 0, "issues": []}
    assert record["answer"]["case_answers"][0]["case_id"] == "C1"
    assert record["answer_text"] == model.response_text

    text = format_answer_text(outcome)
    assert record["answer"]["case_answers"][0]["relevance_reason"] in text
    assert "C1:abnormal_description" in text and "C1:checkpoint:E1" in text
    assert "引用校验：检查 4 条，问题 0 条" in text
    assert "运行状态：ok" in text and "限制与边界：" in text
    # 记录可序列化，且不含凭据与审阅元数据。
    serialized = json.dumps(record, ensure_ascii=False)
    assert "api_key" not in serialized.lower()
    assert API_KEY_ENV not in serialized


def test_historical_action_is_preserved_cited_and_displayed(run_inputs):
    payload = json.loads(answer_text())
    item = payload["case_answers"][0]
    action = "增加清洁检查，不代表当前建议"
    item["historical_corrective_action"] = action
    item["sources"].append({"case_id": "C1", "field": "case.corrective_action"})
    model = CannedModel(json.dumps(payload, ensure_ascii=False))
    outcome = run_answer_question(model_factory=lambda: model, **run_inputs)

    assert outcome.status == STATUS_OK
    assert outcome.record["answer"]["case_answers"][0]["historical_corrective_action"] == action
    assert f"历史改善措施（该 Case 的记录，不是当前建议）：{action}" in format_answer_text(outcome)


@pytest.mark.parametrize("text, status", [
    (answer_text(), STATUS_OK), ("not json", STATUS_FORMAT_FAILED),
])
def test_run_keeps_exact_sent_messages_and_source_identity(run_inputs, text, status):
    model = CannedModel(text)
    outcome = run_answer_question(model_factory=lambda: model, **run_inputs)
    record = outcome.record

    assert outcome.status == status
    sent = record["request"]["sent_messages"]
    assert sent == [{"role": message.role, "content": message.content}
                    for message in model.calls[0]["messages"]]
    assert record["request"]["rendered_prompt_sha256"] == hashlib.sha256(
        sent[0]["content"].encode("utf-8")
    ).hexdigest()
    hashes = record["implementation"]["files_sha256"]
    for path in ["src/casetrace/answer/generation.py", "src/casetrace/answer/prompt.py",
                 "src/casetrace/answer/prompts/grounded_answer_v10.md", "uv.lock"]:
        assert hashes[path] == hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
    assert ".env" not in hashes


def test_call_failure_still_keeps_sent_messages(run_inputs):
    outcome = run_answer_question(model_factory=FailingModel, **run_inputs)
    assert outcome.status == STATUS_MODEL_FAILED
    assert outcome.record["request"]["sent_messages"][1]["content"].startswith(run_inputs["query"])


def test_historical_action_without_its_source_is_rejected(run_inputs):
    payload = json.loads(answer_text())
    payload["case_answers"][0]["historical_corrective_action"] = "历史措施"
    outcome = run_answer_question(
        model_factory=lambda: CannedModel(json.dumps(payload)), **run_inputs,
    )
    assert outcome.status == STATUS_CITATION_FAILED
    assert outcome.record["citations"]["issues"][0]["kind"] == "missing_source"


def test_relevance_without_corresponding_source_is_rejected(run_inputs):
    outcome = run_answer_question(
        model_factory=lambda: CannedModel(answer_text(sources=[("C1", "root_cause")])),
        **run_inputs,
    )
    assert outcome.status == STATUS_CITATION_FAILED
    assert outcome.record["citations"]["issues"][0]["kind"] == "missing_source"


def test_empty_hits_skip_model_and_report_gap(answer_dataset, reference_path, make_snapshot):
    dataset_path, _ = answer_dataset
    created = []

    def factory():
        created.append(True)
        return FailingModel()

    outcome = run_answer_question(
        "zzz 与语料没有词项重合 qqqq", SNAPSHOT_KNOWN_AT,
        dataset_path=dataset_path, reference_path=reference_path,
        snapshot=make_snapshot(dataset_path), model_factory=factory,
    )

    assert outcome.status == STATUS_NO_HITS and outcome.exit_code == 0
    assert created == [], "没有候选时不构造模型，凭据缺失也不会变成模型失败"
    record = outcome.record
    assert record["ranking"] == []
    assert record["context"]["cases"] == []
    assert record["response"]["called_model"] is False
    assert record["error"] is None
    text = format_answer_text(outcome)
    assert "本次没有候选" in text and "不足说明：" in text
    assert "没有返回候选历史案例" in text


def test_model_call_error_is_a_failure_state(run_inputs):
    outcome = run_answer_question(model_factory=FailingModel, **run_inputs)

    assert outcome.status == STATUS_MODEL_FAILED and outcome.exit_code == 3
    assert outcome.record["error"]["type"] == "ModelCallError"
    assert outcome.record["response"]["called_model"] is True
    assert outcome.record["answer"] is None
    assert "调用失败" in outcome.message


def test_format_error_is_a_failure_state(run_inputs):
    outcome = run_answer_question(
        model_factory=lambda: CannedModel("这不是 JSON"), **run_inputs,
    )

    assert outcome.status == STATUS_FORMAT_FAILED and outcome.exit_code == 4
    assert outcome.record["error"]["type"] == "AnswerFormatError"
    assert outcome.record["answer"] is None


def test_format_failure_preserves_raw_response_and_metadata(run_inputs):
    """解析失败前模型已经返回的文本、身份、用量与耗时都要留作失败证据。"""

    outcome = run_answer_question(
        model_factory=lambda: CannedModel("这不是 JSON"), **run_inputs,
    )

    assert outcome.status == STATUS_FORMAT_FAILED
    record = outcome.record
    assert record["answer"] is None
    assert record["answer_text"] == "这不是 JSON"
    assert record["response"]["called_model"] is True
    assert record["response"]["model"] == "offline-stub"
    assert record["response"]["usage"]["total_tokens"] == 180
    assert record["response"]["elapsed_seconds"] >= 0


def test_citation_failure_keeps_answer_for_diagnosis_but_is_not_success(run_inputs):
    outcome = run_answer_question(
        model_factory=lambda: CannedModel(answer_text("C404", checkpoint="E404")), **run_inputs,
    )

    assert outcome.status == STATUS_CITATION_FAILED and outcome.exit_code == 5
    assert outcome.record["error"]["type"] == "CitationError"
    assert outcome.record["citations"]["issue_count"] >= 1
    # 原始回答按失败状态保留，便于排查；它不作为成功输出。
    assert outcome.record["answer_text"]
    assert "C404" in outcome.message


# ── CLI 层：参数、退出码、输出与运行记录 ─────────────────────────────────

def test_cli_ok_run_prints_text_and_writes_record(tmp_path, monkeypatch, capsys, stub_model):
    output = tmp_path / "m4-03-q005.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--output", str(output),
    )

    assert code == 0 and stderr == ""
    assert "候选排名：1.C007 > 2.C001 > 3.C004 > 4.C003" in stdout
    assert "来源：C007:abnormal_description、C007:checkpoint:E007" in stdout
    assert "引用校验：检查 8 条，问题 0 条" in stdout
    assert "运行状态：ok" in stdout
    assert f"运行记录：{output}" in stdout
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == STATUS_OK
    assert record["query"]["query_id"] == "Q005"
    assert record["retrieval"]["requested_method"] == DEV_V3_RECORD_STRATEGY
    assert [item["case_id"] for item in record["ranking"]] == ["C007", "C001", "C004", "C003"]
    assert record["corpus"]["source_cases_are_draft"] is True
    assert stub_model["requested"] == "deepseek-flash"


def test_cli_json_mode_shares_semantics_with_text_mode(tmp_path, monkeypatch, capsys, stub_model):
    text_record = tmp_path / "text.json"

    assert _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--output", str(text_record),
    )[0] == 0
    code, stdout, _ = _invoke_cli(monkeypatch, capsys, "answer", "--query-id", "Q005", "--json")

    assert code == 0
    payload = json.loads(stdout)
    written = json.loads(text_record.read_text(encoding="utf-8"))
    assert payload["status"] == written["status"] == STATUS_OK
    assert payload["ranking"] == written["ranking"]
    assert payload["citations"] == written["citations"]
    assert payload["answer"] == written["answer"]


def test_cli_json_with_output_keeps_stdout_as_single_json(tmp_path, monkeypatch, capsys, stub_model):
    """`--json --output` 组合：stdout 仍是单一合法 JSON，落盘路径提示移到 stderr。"""

    output = tmp_path / "json-output.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--json", "--output", str(output),
    )

    assert code == 0
    payload = json.loads(stdout)  # 若 stdout 被落盘提示污染会在此抛 Extra data
    written = json.loads(output.read_text(encoding="utf-8"))
    assert payload == written
    assert f"运行记录：{output}" in stderr


def test_cli_known_at_outside_snapshot_writes_no_record(tmp_path, monkeypatch, capsys, stub_model):
    output = tmp_path / "should-not-exist.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query", "焊线脱落", "--known-at", "2026-09-16",
        "--output", str(output),
    )

    assert code == EXIT_USAGE and stdout == ""
    assert "运行前提不满足" in stderr and "快照" in stderr
    assert not output.exists()


def test_cli_query_needs_known_at(monkeypatch, capsys, stub_model):
    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query", "焊线脱落",
    )

    assert code == EXIT_USAGE and stdout == ""
    assert "--known-at" in stderr


def test_cli_rejects_mixing_query_and_query_id(monkeypatch, capsys, stub_model):
    code, _, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query", "焊线脱落", "--known-at", "2026-09-15",
        "--query-id", "Q005",
    )

    assert code == EXIT_USAGE
    assert "只能给一个" in stderr


def test_cli_rejects_unknown_query_id(monkeypatch, capsys, stub_model):
    code, _, stderr = _invoke_cli(monkeypatch, capsys, "answer", "--query-id", "Q999")

    assert code == EXIT_USAGE
    assert "Q999" in stderr and "Q005" in stderr


def test_cli_failure_status_stays_out_of_stdout(tmp_path, monkeypatch, capsys, stub_model):
    payload = json.loads(q005_answer_text())
    payload["case_answers"].extend(json.loads(answer_text("C404", checkpoint="E404"))["case_answers"])
    stub_model["model"] = CannedModel(json.dumps(payload))
    output = tmp_path / "citation-failed.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--output", str(output),
    )

    assert code == 5 and stdout == ""
    assert f"运行状态：{STATUS_CITATION_FAILED}" in stderr
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == STATUS_CITATION_FAILED
    assert record["error"]["type"] == "CitationError"


def test_cli_same_family_skip_is_not_a_format_failure(
    tmp_path, monkeypatch, capsys, stub_model,
):
    old = json.loads((PROJECT_ROOT / "tests/fixtures/answer/dev-v3-answer-v7/q003.json").read_text())
    payload = json.loads(old["answer_text"])
    payload["skipped_candidates"][1]["reason"] = "C005 为塑封空洞，当前为 BGA 缺球；同族只是背景，不要求单独采用。"
    text = json.dumps(payload, ensure_ascii=False)
    stub_model["model"] = CannedModel(text)
    output = tmp_path / "family-background.json"
    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q003", "--output", str(output),
    )
    assert code == 0 and "运行状态：ok" in stdout
    record = json.loads(output.read_text())
    assert record["status"] == STATUS_OK
    assert record["answer_text"] == text
    assert record["response"]["usage"]["total_tokens"] == 180


def test_cli_model_failure_is_reported_with_exit_code(tmp_path, monkeypatch, capsys, stub_model):
    stub_model["model"] = FailingModel()
    output = tmp_path / "model-failed.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--output", str(output),
    )

    assert code == 3 and stdout == ""
    assert f"运行状态：{STATUS_MODEL_FAILED}" in stderr
    assert "模拟超时" in stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == STATUS_MODEL_FAILED


def test_cli_reports_missing_credentials_without_touching_the_network(
    monkeypatch, capsys,
):
    """不替换模型工厂：缺凭据时明确失败，且不把失败写成「没有相关案例」。"""

    monkeypatch.delenv(API_KEY_ENV, raising=False)

    code, stdout, stderr = _invoke_cli(monkeypatch, capsys, "answer", "--query-id", "Q005")

    assert code == 3 and stdout == ""
    assert API_KEY_ENV in stderr and "ModelConfigError" in stderr


def test_cli_check_only_does_not_call_model_or_write_record(
    tmp_path, monkeypatch, capsys, stub_model,
):
    output = tmp_path / "should-not-exist.json"
    stub_model["model"] = FailingModel()

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query-id", "Q005", "--check-only",
        "--output", str(output),
    )

    assert code == 0 and stderr == ""
    assert "候选排名：1.C007 > 2.C001 > 3.C004 > 4.C003" in stdout
    assert "上下文检查：" in stdout and "--check-only：未调用模型" in stdout
    assert not output.exists()


def test_cli_empty_hits_report_gap_without_model(
    tmp_path, monkeypatch, capsys, stub_model,
):
    """真实 dev-v3 路径上的空命中：不调用模型，退出码 0，并说明缺的是候选。"""

    output = tmp_path / "no-hits.json"

    code, stdout, stderr = _invoke_cli(
        monkeypatch, capsys, "answer", "--query", "zzz 与语料没有词项重合 qqqq",
        "--known-at", "2026-09-15", "--output", str(output),
    )

    assert code == 0 and stderr == ""
    assert "（本次没有候选）" in stdout
    assert "没有返回候选历史案例" in stdout
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == STATUS_NO_HITS
    assert record["response"]["called_model"] is False
