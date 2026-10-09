"""M4-03 引用守卫：核对引用能否在本次上下文中定位。

这些测试只调用公共函数，用自造语料覆盖 Case 归属、实体 ID、字段与冲突，
再用 M4-02 的真实产物核对一条真实回答，并检查守卫不是空转的。

守卫**不判断**引用是否支持它所在的那句话，因此这里不断言语义支持；
语义支持属人工审阅，见 M4-04。
"""

from dataclasses import replace
import json
from datetime import date
from pathlib import Path

import pytest

from casetrace.answer.context import (
    RETRIEVAL_METHOD,
    build_evidence_context,
    prepare_answer_run,
)
from casetrace.answer.generation import parse_grounded_answer
from casetrace.answer.validation import (
    CONFLICTING_CASE,
    CROSS_CASE,
    DUPLICATE_CASE,
    INVALID_FIELD,
    MISSING_TARGET,
    UNKNOWN_CASE,
    UNKNOWN_FIELD,
    CitationError,
    ensure_answer_citations,
    validate_answer_citations,
)
from casetrace.demo import load_validated_dataset
from casetrace.evaluation.runner import build_retriever_from_records

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_V3_DATASET = PROJECT_ROOT / "data/dev/demo-v3.json"
REFERENCE_FILE = (
    PROJECT_ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
)
M4_02_RECORD = PROJECT_ROOT / "tests/fixtures/answer/m4-02-q005.json"


@pytest.fixture
def context(answer_dataset, reference_path, answer_query):
    """按固定 R3 检索自造语料并组装上下文；自造语料三条 Case 都会命中。"""

    dataset_path, _ = answer_dataset
    records, payload, reference = load_validated_dataset(dataset_path, reference_path)
    retriever = build_retriever_from_records(records, reference, method=RETRIEVAL_METHOD)
    hits = retriever.search(answer_query, top_k=4)
    return build_evidence_context(answer_query, hits, records, reference, payload["sources"])


def answer_text(case_id, *, sources=None, evidences=None, skipped=()) -> str:
    """构造一份回答 JSON；参数用来单独制造某一类引用问题，其余部分保持合法。"""

    index = case_id[1:]
    return json.dumps({
        "case_answers": [{
            "case_id": case_id,
            "relevance_reason": "同产品且异常描述相同",
            "query_facts": ["涉及产品 P1"],
            "case_facts": ["焊线脱落，表面污染"],
            "historical_root_cause": "表面污染",
            "historical_evidences": [
                {"checkpoint_id": item, "result": "观察到表面污染"}
                for item in (evidences if evidences is not None else [f"E{index}"])
            ],
            "sources": [
                {"case_id": item, "field": field}
                for item, field in (
                    sources if sources is not None
                    else [(case_id, "abnormal_description"), (case_id, f"checkpoint:E{index}")]
                )
            ],
        }],
        "skipped_candidates": [{"case_id": item, "reason": "证据不足"} for item in skipped],
        "current_gaps": ["当前未提供客户批号"],
        "insufficiency": None,
    }, ensure_ascii=False)


def kinds(report) -> set[str]:
    return {issue.kind for issue in report.issues}


def test_valid_answer_passes_and_counts_checked_references(context):
    """合法引用通过守卫；报告只说明检查条数，不表示语义支持。"""

    text = answer_text("C1", sources=[
        ("C1", "abnormal_description"),
        ("C1", "root_cause"),
        ("C1", "detail:D1"),
        ("C1", "checkpoint:E1"),
    ])
    report = validate_answer_citations(parse_grounded_answer(text), context)

    assert report.ok and report.issues == ()
    # 1 条 Case 归属 + 1 条历史检查 + 4 条来源字段。
    assert report.checked == 6
    assert report.to_payload() == {"checked": 6, "issue_count": 0, "issues": []}


def test_answer_for_case_outside_context_is_rejected(context):
    report = validate_answer_citations(parse_grounded_answer(answer_text("C404")), context)

    assert kinds(report) == {UNKNOWN_CASE}
    assert "C404" in report.issues[0].detail


def test_source_borrowed_from_another_candidate_is_cross_case(context):
    """字段存在但归属错误：引用的是另一个 Case 的字段，必须拒绝。"""

    text = answer_text("C1", sources=[("C2", "abnormal_description")])
    report = validate_answer_citations(parse_grounded_answer(text), context)

    assert kinds(report) == {CROSS_CASE}
    assert report.issues[0].location == "case_answers[0].sources[0]"


def test_case_in_corpus_but_not_retrieved_this_run_is_rejected(context):
    """语料里有这个 Case，但本次上下文没有它：未检索到的 Case 不能当来源。"""

    all_ids = [case.case_id for case in context.cases]
    assert len(all_ids) >= 2
    kept, excluded = all_ids[0], all_ids[1]
    narrowed = replace(
        context, cases=[case for case in context.cases if case.case_id == kept],
    )

    report = validate_answer_citations(parse_grounded_answer(answer_text(excluded)), context=narrowed)

    assert kinds(report) == {UNKNOWN_CASE}


@pytest.mark.parametrize("field", ["detail:D404", "checkpoint:E404"])
def test_missing_detail_or_checkpoint_is_rejected(context, field):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", field)])), context,
    )

    assert kinds(report) == {MISSING_TARGET}
    assert field.split(":")[1] in report.issues[0].detail


@pytest.mark.parametrize("field", ["detail:", "checkpoint:"])
def test_invalid_field_syntax_is_rejected(context, field):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", field)])), context,
    )

    assert kinds(report) == {INVALID_FIELD}


def test_unknown_field_name_is_rejected(context):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", "root_cause_text")])), context,
    )

    assert kinds(report) == {UNKNOWN_FIELD}
    assert "root_cause_text" in report.issues[0].detail


def test_case_field_without_content_is_not_locatable(context):
    """自造语料的 investigation_others 为 None：引用一个没有内容的字段必须失败。"""

    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", "investigation_others")])), context,
    )

    assert kinds(report) == {UNKNOWN_FIELD}
    assert "没有内容" in report.issues[0].detail


def test_background_field_is_locatable(context):
    """产品背景随上下文一起提供（主数据名称与关系），模型引用它必须能定位。"""

    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", "background")])), context,
    )

    assert report.ok, report.to_payload()


def test_processes_field_is_locatable(context):
    """已确认异常工序随上下文一起提供，模型引用它必须能定位。"""

    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", "processes")])), context,
    )

    assert report.ok, report.to_payload()


@pytest.mark.parametrize("field", ["case.abnormal_description", "source.failure_mode_id"])
def test_container_prefixed_field_is_locatable(context, field):
    """模型按上下文 JSON 结构写出的 case./source. 前缀，等价于扁平写法。"""

    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", field)])), context,
    )

    assert report.ok, report.to_payload()


@pytest.mark.parametrize("field", [
    "source.abnormal_description", "case.failure_mode_id", "case.background",
    "source.processes", "case.detail:D1", "source.checkpoint:E1",
])
def test_field_in_wrong_container_is_rejected(context, field):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", sources=[("C1", field)])), context,
    )

    assert kinds(report) == {UNKNOWN_FIELD}


def test_checkpoint_of_another_case_is_rejected(context):
    """正确 ID 但错 Case：E2 属于 C2，C1 的回答不能引用它。"""

    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", evidences=["E2"])), context,
    )

    assert kinds(report) == {MISSING_TARGET}
    assert report.issues[0].location == "case_answers[0].historical_evidences[0].checkpoint_id"


def test_skipped_candidate_outside_context_is_rejected(context):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", skipped=["C404"])), context,
    )

    assert kinds(report) == {UNKNOWN_CASE}
    assert report.issues[0].location == "skipped_candidates[0].case_id"


def test_same_case_cannot_be_answered_and_skipped(context):
    report = validate_answer_citations(
        parse_grounded_answer(answer_text("C1", skipped=["C1"])), context,
    )

    assert kinds(report) == {CONFLICTING_CASE}


def test_duplicate_case_answers_are_rejected(context):
    payload = json.loads(answer_text("C1"))
    payload["case_answers"].append(payload["case_answers"][0])
    report = validate_answer_citations(parse_grounded_answer(json.dumps(payload)), context)

    assert kinds(report) == {DUPLICATE_CASE}
    assert report.issues[0].location == "case_answers[1].case_id"


def test_empty_context_rejects_any_answer(answer_query):
    """空上下文里没有任何历史材料，任何 Case 引用都无法定位。"""

    empty = build_evidence_context(
        answer_query, [], {"cases": [], "details": [], "evidences": []},
        reference=None, sources={},
    )
    report = validate_answer_citations(parse_grounded_answer(answer_text("C1")), empty)

    assert kinds(report) == {UNKNOWN_CASE}
    assert "本次没有候选" in report.issues[0].detail


def test_guard_reports_structure_only_not_semantic_support(context):
    """已知边界：检查 ID 存在但结果原文被改写，守卫仍然通过——语义支持要人工审阅。"""

    payload = json.loads(answer_text("C1"))
    payload["case_answers"][0]["historical_evidences"][0]["result"] = (
        "当前 Incident 的根本原因是参数漂移。"
    )
    report = validate_answer_citations(parse_grounded_answer(json.dumps(payload)), context)

    assert report.ok, "引用可定位即通过；本测试固定这一边界，防止把守卫当成事实核查"


def test_ensure_raises_citation_error_carrying_report(context):
    with pytest.raises(CitationError) as error:
        ensure_answer_citations(parse_grounded_answer(answer_text("C404")), context)

    assert error.value.report.issues[0].kind == UNKNOWN_CASE
    assert "C404" in str(error.value)


# ── 真实回答：M4-02 SD3 产物在本次上下文里的引用核对 ──────────────────────

def _real_context(query_index=4, *, drop_case=None):
    payload = json.loads(DEV_V3_DATASET.read_text(encoding="utf-8"))
    query = payload["queries"][query_index]
    run = prepare_answer_run(
        query["text"], date.fromisoformat(query["known_at"]),
        dataset_path=DEV_V3_DATASET, reference_path=REFERENCE_FILE,
    )
    inputs = run.inputs
    context = build_evidence_context(
        inputs.query, inputs.hits, inputs.records, inputs.reference, inputs.sources,
    )
    if drop_case is None:
        return context
    return replace(context, cases=[case for case in context.cases if case.case_id != drop_case])


def test_real_m4_02_answer_passes_guard_and_is_not_vacuous():
    """真实回答的引用都能定位；去掉它引用的一个候选后守卫必须失败。"""

    record = json.loads(M4_02_RECORD.read_text(encoding="utf-8"))
    assert record["run"]["query_id"] == "Q005"
    answer = parse_grounded_answer(record["answer_text"])

    report = validate_answer_citations(answer, _real_context())
    assert report.ok, report.to_payload()
    assert report.checked > 10

    broken = validate_answer_citations(answer, _real_context(drop_case="C003"))
    assert not broken.ok
    assert UNKNOWN_CASE in kinds(broken)
