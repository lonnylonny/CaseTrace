"""Hybrid 计分、检索接线和报告元数据的回归测试。

纯计分测试使用小常数（常数=1 → 名次 1/2/3 分别贡献 1/2、1/3、1/4），
接线测试使用替身，不加载模型。
"""

import pytest

from casetrace.retrieval.hybrid import (
    CANDIDATES_PER_ROUTE,
    RRF_RANK_CONSTANT,
    ROUTE_METHODS,
    HybridRetriever,
    reciprocal_rank_fusion,
)
from casetrace.retrieval.base import SearchHit


def test_fusion_parameters_are_fixed_before_running():
    """融合常数、每路候选数与参与的两路在运行前固定；改动必须整体重跑再比较。"""
    assert RRF_RANK_CONSTANT == 60
    assert CANDIDATES_PER_ROUTE == 10
    assert ROUTE_METHODS == ("bm25", "embedding")


def test_overlapping_cases_merge_and_sum_both_routes():
    """两路都出现：名次互换后两条 Case 的融合分数相等（合并去重并逐路求和）。"""
    fused = reciprocal_rank_fusion([["C1", "C2"], ["C2", "C1"]], rrf_rank_constant=1)

    assert set(fused) == {"C1", "C2"}
    assert fused["C1"] == pytest.approx(1 / 2 + 1 / 3)
    assert fused["C2"] == pytest.approx(1 / 3 + 1 / 2)


def test_case_present_in_one_route_only_gets_that_route_contribution():
    """单路出现：只拿该路名次的贡献，不虚构另一路的名次。"""
    fused = reciprocal_rank_fusion([["C1"], ["C2"]], rrf_rank_constant=1)

    assert set(fused) == {"C1", "C2"}
    assert fused["C1"] == pytest.approx(1 / 2)
    assert fused["C2"] == pytest.approx(1 / 2)


def test_empty_route_still_lets_the_other_route_contribute():
    """一路无候选：结果等价于另一路单独的名次贡献，不整体作废。"""
    fused = reciprocal_rank_fusion([[], ["C1", "C2"]], rrf_rank_constant=1)

    assert set(fused) == {"C1", "C2"}
    assert fused["C1"] == pytest.approx(1 / 2)
    assert fused["C2"] == pytest.approx(1 / 3)


def test_all_routes_empty_returns_no_candidates():
    assert reciprocal_rank_fusion([[], []], rrf_rank_constant=1) == {}


def test_repeated_case_in_one_route_counts_only_its_first_rank():
    """同一路内重复 ID 只按首次出现的名次计一次，不重复加分。"""
    fused = reciprocal_rank_fusion([["C1", "C2", "C1"], ["C3"]], rrf_rank_constant=1)

    assert set(fused) == {"C1", "C2", "C3"}
    assert fused["C1"] == pytest.approx(1 / 2)
    assert fused["C2"] == pytest.approx(1 / 3)
    assert fused["C3"] == pytest.approx(1 / 2)


@pytest.mark.parametrize("constant", [0, -1, True, 1.5])
def test_non_positive_integer_constant_is_rejected(constant):
    """融合常数必须是正整数；bool 与小数也算非法，与既有 top_k 校验风格一致。"""
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["C1"]], rrf_rank_constant=constant)


def test_ranks_start_at_one_and_inputs_are_not_mutated():
    """名次从 1 开始（第一名贡献 1/(常数+1)，不是 1/常数）；不改动传入的 rankings。"""
    rankings = [["C1", "C2"], ["C2"]]
    snapshot = [list(route) for route in rankings]

    fused = reciprocal_rank_fusion(rankings, rrf_rank_constant=1)

    assert fused["C1"] == pytest.approx(1 / 2)
    assert fused["C2"] == pytest.approx(1 / 3 + 1 / 2)
    assert all(isinstance(score, float) for score in fused.values())
    assert rankings == snapshot


def test_inputs_may_be_any_sequence_not_only_lists():
    """只要求 Sequence：由 tuple 组成的排名同样可用。"""
    fused = reciprocal_rank_fusion((("C1",), ("C1",)), rrf_rank_constant=1)

    assert set(fused) == {"C1"}
    assert fused["C1"] == pytest.approx(1 / 2 + 1 / 2)


class StubRoute:
    """按固定顺序返回命中，并记录调用时的 top_k，用于验证融合接线。"""

    def __init__(self, case_ids):
        self.case_ids = list(case_ids)
        self.requested_top_k = None

    def search(self, query, *, top_k):
        self.requested_top_k = top_k
        return [SearchHit(case_id, 1.0) for case_id in self.case_ids[:top_k]]

    def describe(self):
        return {"method": "stub-route"}


def test_hybrid_merges_and_sorts_two_routes():
    """两路重叠：融合分数等于各路名次贡献之和，排序为分数降序、同分按 Case ID 升序。"""
    retriever = HybridRetriever({}, bm25=StubRoute(["C1", "C2", "C3"]),
                                 embedding=StubRoute(["C3", "C1"]))

    hits = retriever.search("q", top_k=10)

    expected = reciprocal_rank_fusion(
        [["C1", "C2", "C3"], ["C3", "C1"]], rrf_rank_constant=RRF_RANK_CONSTANT,
    )
    expected_order = sorted(expected.items(), key=lambda pair: (-pair[1], pair[0]))
    assert [hit.case_id for hit in hits] == [case_id for case_id, _ in expected_order]
    assert [hit.score for hit in hits] == [pytest.approx(score) for _, score in expected_order]
    assert all(hit.matched_terms is None for hit in hits)


def test_hybrid_empty_route_still_lets_other_route_contribute():
    """一路无候选：结果等价于另一路单独的名次贡献。"""
    retriever = HybridRetriever({}, bm25=StubRoute([]), embedding=StubRoute(["C1", "C2"]))

    hits = retriever.search("q", top_k=10)

    assert [hit.case_id for hit in hits] == ["C1", "C2"]
    assert hits[0].score == pytest.approx(1 / (RRF_RANK_CONSTANT + 1))
    assert hits[1].score == pytest.approx(1 / (RRF_RANK_CONSTANT + 2))


def test_hybrid_requests_candidates_per_route_from_each_route():
    """候选截断：每一路都按 CANDIDATES_PER_ROUTE 取候选，而不是无限量。"""
    bm25 = StubRoute(["C1"])
    embedding = StubRoute(["C2"])

    HybridRetriever({}, bm25=bm25, embedding=embedding).search("q", top_k=5)

    assert bm25.requested_top_k == CANDIDATES_PER_ROUTE
    assert embedding.requested_top_k == CANDIDATES_PER_ROUTE


def test_hybrid_describe_reports_fixed_parameters():
    """describe() 如实记录融合方式与运行前固定的参数。"""
    description = HybridRetriever({}, bm25=StubRoute([]), embedding=StubRoute([])).describe()

    assert description["method"] == "hybrid"
    assert description["parameters"]["rrf_rank_constant"] == RRF_RANK_CONSTANT
    assert description["parameters"]["candidates_per_route"] == CANDIDATES_PER_ROUTE
    assert description["parameters"]["route_methods"] == list(ROUTE_METHODS)


def test_hybrid_query_traces_follow_call_order():
    """逐 Query 追溯按 search 调用顺序记录，含各路名次与融合分数。"""
    retriever = HybridRetriever({}, bm25=StubRoute(["C1"]), embedding=StubRoute(["C1"]))
    retriever.search("q1", top_k=5)
    retriever.search("q2", top_k=5)

    traces = retriever.query_traces()

    assert len(traces) == 2
    for trace in traces:
        assert set(trace) == {"routes", "fusion"}
        assert trace["routes"]["bm25"] == {"C1": 1}
        assert trace["routes"]["embedding"] == {"C1": 1}


def test_hybrid_duplicate_candidate_trace_uses_first_rank_for_fusion():
    retriever = HybridRetriever(
        {}, bm25=StubRoute(["C1", "C2", "C1"]), embedding=StubRoute([]),
    )

    hits = retriever.search("q", top_k=3)
    trace = retriever.query_traces()[0]

    assert trace["routes"]["bm25"] == {"C1": 1, "C2": 2}
    assert trace["routes"]["embedding"] == {}
    assert [hit.case_id for hit in hits] == ["C1", "C2"]
    for hit in hits:
        score_from_trace = sum(
            1 / (RRF_RANK_CONSTANT + ranks[hit.case_id])
            for ranks in trace["routes"].values() if hit.case_id in ranks
        )
        assert hit.score == pytest.approx(score_from_trace)
        assert trace["fusion"][hit.case_id] == pytest.approx(score_from_trace)


def test_hybrid_reports_actual_route_configuration_and_run_details():
    class DescribedRoute(StubRoute):
        def __init__(self, method, config, cache_status):
            super().__init__(["C1"])
            self.method = method
            self.config = config
            self.cache_status = cache_status

        def describe(self):
            return {"method": self.method, "config": self.config}

        def run_details(self):
            return {"cache": {"status": self.cache_status}}

    bm25 = DescribedRoute("bm25-custom", {"k1": 1.7}, "none")
    embedding = DescribedRoute("embedding-custom", {"revision": "test-revision"}, "miss")
    retriever = HybridRetriever({}, bm25=bm25, embedding=embedding)

    description = retriever.describe()
    assert description["routes"] == {
        "bm25": bm25.describe(), "embedding": embedding.describe(),
    }
    assert retriever.run_details() == {
        "routes": {"bm25": bm25.run_details(), "embedding": embedding.run_details()},
    }
