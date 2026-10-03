"""验证 M3-06 的 Query 侧过滤规则与变体检索器：只改 Query 词项，索引与历史文本不变。"""

import pytest

from casetrace.evaluation.runner import (
    DEFAULT_METHOD,
    EXPERIMENTAL_RETRIEVER_FACTORIES,
    RETRIEVER_FACTORIES,
)
from casetrace.retrieval.bm25 import BM25Retriever, tokenize
from casetrace.retrieval.query_filter import (
    NEGATION_MARKERS,
    FilteredBM25Retriever,
    filtered_query_tokens,
    is_label_token,
    split_clauses,
    strip_negation_clauses,
)

# 取 Q005 的真实形态：开头是“已排除…的可能”小句，尾部是“原因尚未确认”。
NEGATED_QUERY = (
    "已排除外观碰伤与运输损伤的可能，检查重点在键合界面，"
    "OQC 拉力试验显示焊线自焊盘脱开，原因尚未确认。"
)


def test_splits_clauses_on_both_chinese_and_english_punctuation():
    assert split_clauses("已排除运输损伤的可能；检查重点在键合界面。") == [
        "已排除运输损伤的可能", "检查重点在键合界面",
    ]


def test_drops_only_the_clauses_that_carry_negation_markers():
    kept = strip_negation_clauses(NEGATED_QUERY)

    assert "碰伤" not in kept and "运输" not in kept
    assert "尚未确认" not in kept and "确认" not in kept
    assert "检查重点在键合界面" in kept and "焊线自焊盘脱开" in kept


def test_query_without_negation_markers_is_kept_intact():
    query = "OQC 发现焊线脱落，涉及客户 CUS_001。"

    assert strip_negation_clauses(query) == "OQC 发现焊线脱落，涉及客户 CUS_001"


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("prod_001", True), ("cus_002", True), ("dev_pl_014", True), ("dev_cl_014", True),
        ("客户", True), ("及客", True), ("产品", True), ("涉及", True), ("生产", True),
        ("焊线", False), ("碰伤", False), ("确认", False), ("prod", False),
    ],
)
def test_label_tokens_cover_ids_and_query_template_words(token, expected):
    assert is_label_token(token) is expected


def test_without_filters_tokens_match_plain_tokenize():
    assert filtered_query_tokens("焊线脱落 PROD_001") == tokenize("焊线脱落 PROD_001")


def test_negation_filter_drops_clause_terms_but_keeps_the_rest():
    tokens = filtered_query_tokens(NEGATED_QUERY, drop_negation_clauses=True)

    assert "碰伤" not in tokens and "运输" not in tokens
    assert "未确" not in tokens and "确认" not in tokens
    assert "焊线" in tokens and "焊盘" in tokens


def test_label_filter_drops_ids_and_template_words():
    tokens = filtered_query_tokens(
        "涉及客户 CUS_002、产品 PROD_004，焊线脱开。", drop_label_terms=True,
    )

    assert "cus_002" not in tokens and "prod_004" not in tokens
    assert not {"客户", "及客", "产品", "涉及"} & set(tokens)
    assert "焊线" in tokens and "脱开" in tokens


def test_variant_requires_at_least_one_filter():
    with pytest.raises(ValueError, match="至少要启用一条规则"):
        FilteredBM25Retriever({"C1": "wire lift"})


def test_variant_keeps_the_same_index_and_drops_filtered_terms_from_matches():
    documents = {"C1": "碰伤 焊线脱落", "C2": "塑封空洞"}
    plain = BM25Retriever(documents)
    filtered = FilteredBM25Retriever(documents, drop_negation_clauses=True)
    query = "已排除碰伤的可能，检查焊线"

    assert filtered.case_ids == plain.case_ids
    plain_matches = [term for hit in plain.search(query, top_k=2) for term in hit.matched_terms]
    filtered_hits = filtered.search(query, top_k=2)

    assert "碰伤" in plain_matches
    assert all("碰伤" not in hit.matched_terms for hit in filtered_hits)
    assert filtered_hits[0].case_id == "C1" and "焊线" in filtered_hits[0].matched_terms


def test_describe_records_the_enabled_filters_and_the_index_parameters():
    retriever = FilteredBM25Retriever({"C1": "wire lift"}, drop_label_terms=True)
    description = retriever.describe()

    assert description["method"] == "bm25_filtered_query_terms"
    assert description["query_filter"]["drop_negation_clauses"] is False
    assert description["query_filter"]["drop_label_terms"] is True
    assert description["query_filter"]["negation_markers"] == list(NEGATION_MARKERS)
    assert description["parameters"]["k1"] == 1.5


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("bm25_drop_negation", (True, False)),
        ("bm25_drop_labels", (False, True)),
        ("bm25_drop_negation_labels", (True, True)),
    ],
)
def test_registered_experiment_methods_build_the_intended_variants(method, expected):
    retriever = EXPERIMENTAL_RETRIEVER_FACTORIES[method]({"C1": "wire lift", "C2": "molding void"})

    assert isinstance(retriever, FilteredBM25Retriever)
    assert (retriever.drop_negation_clauses, retriever.drop_label_terms) == expected


def test_experiment_variants_stay_out_of_the_shipped_registry():
    """实验变体与生产方法分表登记：生产守卫只认交付方法。"""
    assert set(EXPERIMENTAL_RETRIEVER_FACTORIES) == {
        "bm25_drop_negation", "bm25_drop_labels", "bm25_drop_negation_labels",
    }
    assert not set(EXPERIMENTAL_RETRIEVER_FACTORIES) & set(RETRIEVER_FACTORIES)
    assert DEFAULT_METHOD == "bm25"
