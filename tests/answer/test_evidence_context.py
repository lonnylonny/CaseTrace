"""M4-01 证据上下文的边界行为（用户核心实践 A 的测试接缝）。

这些测试在 `build_evidence_context` 主体实现前是**红**的：它们描述契约，不描述写法。
只调用公共函数，不绑定内部私有实现。
"""

import json
from datetime import date
from pathlib import Path

import pytest

from casetrace.answer.context import (
    RETRIEVAL_METHOD,
    SOURCE_FIELDS,
    build_evidence_context,
    context_to_payload,
    prepare_answer_run,
    product_backgrounds,
)
from casetrace.demo import load_validated_dataset
from casetrace.evaluation.runner import build_retriever_from_records
from casetrace.retrieval.base import SearchHit

# CaseEvidence 的字段清单；序列化结果必须与它完全一致，不多不少。
CASE_EVIDENCE_FIELDS = (
    "rank", "case_id", "case", "details", "evidences", "source", "background", "processes",
)

# 主数据里未被任何 Case 选中的候选知识，出现在上下文就说明读了候选根因库。
CANDIDATE_ROOT_CAUSES = "表面污染; 参数异常"
CANDIDATE_ACTIONS = "改善清洁; 优化参数"


@pytest.fixture
def loaded(answer_dataset, reference_path, answer_query):
    """加载自造语料并按 R3 检索一次，返回组装上下文所需的全部输入。

    自造语料只有 3 条，BM25 在这种规模会给出负分（见 `retrieval/bm25.py` 的说明），
    所以具体名次不是重点；测试因此不依赖固定的命中顺序。
    """

    dataset_path, _ = answer_dataset
    records, payload, reference = load_validated_dataset(dataset_path, reference_path)
    retriever = build_retriever_from_records(records, reference, method=RETRIEVAL_METHOD)
    return dict(
        hits=retriever.search(answer_query, top_k=4), records=records,
        reference=reference, sources=payload["sources"], query=answer_query,
    )


def _build(loaded, hits=None, query=None):
    return build_evidence_context(
        loaded["query"] if query is None else query,
        loaded["hits"] if hits is None else hits,
        loaded["records"], loaded["reference"], loaded["sources"],
    )


def test_empty_hits_give_empty_cases(loaded):
    context = _build(loaded, hits=[])
    assert context.query == loaded["query"]
    assert context.cases == []


def test_keeps_hit_order_and_numbering(loaded):
    reversed_hits = list(reversed(loaded["hits"]))
    context = _build(loaded, hits=reversed_hits)
    assert [case.case_id for case in context.cases] == [hit.case_id for hit in reversed_hits]
    assert [case.rank for case in context.cases] == list(range(1, len(reversed_hits) + 1))


def test_keeps_original_text_and_source_ids(loaded):
    payload = context_to_payload(_build(loaded))
    assert payload["cases"], "自造语料的三条 Case 都应命中"
    for case in payload["cases"]:
        case_id = case["case_id"]
        assert case["case"]["case_id"] == case_id
        assert case["case"]["abnormal_description"]
        assert case["case"]["root_cause"]
        assert case["source"]["failure_mode_id"] == "00001"
        for detail in case["details"]:
            assert detail["case_id"] == case_id
            assert detail["detail_id"].startswith("D")
        for evidence in case["evidences"]:
            assert evidence["case_id"] == case_id
            assert evidence["checkpoint_id"].startswith("E")
            assert evidence["relevance"] in {"related", "not_related", "uncertain"}


def test_keeps_query_negation_and_identifiers(loaded):
    """检索时被删掉的否定小句与标识词，必须原样留在生成输入里。"""

    payload = context_to_payload(_build(loaded))
    assert payload["query"] == loaded["query"]
    assert "已排除运输碰伤的可能" in payload["query"]
    assert "DEV_PL_1" in payload["query"]


def test_background_comes_from_reference_data(loaded):
    context = _build(loaded)
    background = context.cases[0].background[0]
    assert background == {
        "product_id": "P1", "product_name": "演示产品", "product_family": "演示产品族",
        "package_route": "LF_WB", "customer_id": "CUS1",
    }
    assert product_backgrounds(loaded["reference"], context.cases[0].details)[0] == background


def test_query_product_mentions_supply_only_traceable_master_background(loaded):
    payload = context_to_payload(_build(loaded))
    mentions = payload["query_product_mentions"]
    assert len(mentions) == 1
    assert mentions[0] == {
        "query_mention": "P1", "product_id": "P1", "product_name": "演示产品",
        "product_family_id": loaded["reference"].products["P1"]["product_family_id"],
        "product_family": "演示产品族", "package_route": "LF_WB",
        "source": "reference.products/product_families",
    }
    assert "customer_id" not in mentions[0]  # 不把主数据归属反填为当前客户
    assert "process_id" not in mentions[0]   # 不由路线推定当前异常工序
    assert context_to_payload(_build(loaded, query="XP1 P1_suffix P404"))["query_product_mentions"] == []


def test_negated_product_mention_is_not_asserted_as_current_fact(loaded):
    context = _build(loaded, query="不涉及产品 P1，原因尚未确认")
    assert context.query.startswith("不涉及")
    assert context.query_product_mentions[0]["query_mention"] == "P1"
    # 这是名称查表，不是 Incident 产品抽取；否定上下文仍完整交给模型。
    assert "current_product" not in context_to_payload(context)


@pytest.fixture
def real_family_inputs():
    root = Path(__file__).resolve().parents[2]
    query = "客户收货后发现 BGA 锡球缺失，涉及客户 CUS_004、产品 PROD_006"
    return prepare_answer_run(
        query, date(2026, 9, 15), dataset_path=root / "data/dev/demo-v3.json",
        reference_path=root / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx",
    ).inputs


def test_product_family_background_does_not_create_adoption_directives(real_family_inputs):
    inputs = real_family_inputs
    context = build_evidence_context(
        inputs.query, [SearchHit("C005", 1.0, None), SearchHit("C001", 0.5, None)],
        inputs.records, inputs.reference, inputs.sources,
    )
    assert set(context_to_payload(context)) == {"query", "cases", "query_product_mentions"}
    assert context.query_product_mentions[0]["product_family"] == "Microcontroller"
    assert context.cases[0].background[0]["product_family"] == "Microcontroller"
    # C005 路线不同仍同族；C001 产品族不同不能因其它相似背景而匹配。
    assert context.query_product_mentions[0]["package_route"] != context.cases[0].background[0]["package_route"]
    same_route = build_evidence_context(
        "PROD_001 在 OQC 发现焊线脱落", [SearchHit("C003", 1.0, None)],
        inputs.records, inputs.reference, inputs.sources,
    )
    assert same_route.query_product_mentions[0]["package_route"] == same_route.cases[0].background[0]["package_route"]
    assert same_route.query_product_mentions[0]["product_family"] != same_route.cases[0].background[0]["product_family"]


@pytest.mark.parametrize("query", [
    "不涉及产品 PROD_006", "历史涉及产品 PROD_006", "如果涉及产品 PROD_006",
    "对比产品 PROD_006", "涉及产品 PROD_006 和 PROD_005", "涉及产品 PROD_006_suffix",
])
def test_noncurrent_product_keeps_original_query_and_background_only(real_family_inputs, query):
    inputs = real_family_inputs
    context = build_evidence_context(
        query, [SearchHit("C005", 1.0, None)], inputs.records, inputs.reference, inputs.sources,
    )
    assert context.query == query
    assert set(context_to_payload(context)) == {"query", "cases", "query_product_mentions"}


def test_payload_includes_traceable_process_names(loaded):
    cases = {case["case_id"]: case for case in context_to_payload(_build(loaded))["cases"]}
    assert cases["C1"]["processes"] == [
        {"process_id": "P004", "process_name": "Wire Bond"},
    ]
    assert cases["C3"]["processes"] == [
        {"process_id": "P007", "process_name": "Molding"},
    ]


def test_rejects_unknown_hit_id(loaded):
    hits = list(loaded["hits"]) + [SearchHit("C404", 1.0, None)]
    with pytest.raises(ValueError, match="C404"):
        _build(loaded, hits=hits)


def test_rejects_duplicate_hit_id(loaded):
    duplicate = [loaded["hits"][0], loaded["hits"][0]]
    with pytest.raises(ValueError, match=duplicate[0].case_id):
        _build(loaded, hits=duplicate)


def test_excludes_labels_generation_metadata_and_candidate_lists(loaded, answer_poison):
    """qrels、标注理由、生成/审阅元数据与候选根因库都不得进入模型上下文。"""

    serialized = json.dumps(context_to_payload(_build(loaded)), ensure_ascii=False)
    for poison in answer_poison.values():
        assert poison not in serialized
    assert CANDIDATE_ROOT_CAUSES not in serialized
    assert CANDIDATE_ACTIONS not in serialized
    assert "judgments" not in serialized and "relevance_label" not in serialized


# ── 真实入口（SD3）：dev-v3 的 Q005 走完整链路 ────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DEV_V3_DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE_FILE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"


def _real_context(query_index=4):
    """用真实语料与固定 R3 方案跑一遍，返回 (run, 组装好的上下文)。"""

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
    return run, context


def test_real_query_keeps_negation_and_rank_order():
    """Q005 的原始否定条件与命中顺序都要保留，构造前后排名一致。"""

    run, context = _real_context()
    assert context.query == run.inputs.query
    assert "排除" in context.query and "DEV_PL_014" in context.query
    assert [case.case_id for case in context.cases] == [hit.case_id for hit in run.inputs.hits]
    assert [case.rank for case in context.cases] == list(range(1, len(context.cases) + 1))
    assert context.cases


def test_real_query_source_chain_is_traceable():
    """每条来源只留允许字段，且原因原文确实能在 Case 正文与主数据里对回去。"""

    _, context = _real_context()
    for case in context.cases:
        assert set(case.source) <= set(SOURCE_FIELDS)
        assert case.source["failure_mode_id"]
        # 来源原文是 Case 正文的子串，这是 check_source_records 已经核对过的关系。
        assert case.source["root_cause"] in case.case.root_cause
        assert case.source["corrective_action"] in case.case.corrective_action
        assert case.details and case.evidences
        assert all(detail.case_id == case.case_id for detail in case.details)
        assert all(item.case_id == case.case_id for item in case.evidences)
        assert case.background[0]["product_family"]


def test_real_query_context_has_no_metadata_leak():
    """真实路径的上下文只含 query 与 cases，且不含任何生成／审阅／标签元数据。"""

    _, context = _real_context()
    payload = context_to_payload(context)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert set(payload) == {"query", "cases", "query_product_mentions"}
    assert all(set(case) == set(CASE_EVIDENCE_FIELDS) for case in payload["cases"])
    for forbidden in ("generation_note", "review_status", "rationale", "judgment", "qrels"):
        assert forbidden not in serialized
