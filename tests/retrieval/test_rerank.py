"""Rerank 纯重排函数与流水线接线的回归测试。

纯重排测试使用可控的替身分数（不加载模型），验证 ID 与分数一一对应、同分稳定、
空输入、长度不匹配、非有限分数与候选边界。接线测试用替身注入候选段与重排段，
不加载模型、不联网；真实模型的运行证据见任务包与 results。
"""

import numpy as np
import pytest

from casetrace.retrieval.rerank import (
    CANDIDATE_COUNT,
    CANDIDATE_METHOD,
    RERANK_MODEL,
    RERANK_REVISION,
    RERANK_SCORING_DIRECTION,
    RerankRetriever,
    SentenceTransformerReranker,
    rerank_candidates,
)
from casetrace.retrieval.base import SearchHit


def _hits(*case_ids):
    """按输入顺序构造候选命中；原始分数统一 1.0，与重排分数无关。"""
    return [SearchHit(case_id, 1.0) for case_id in case_ids]


def test_fixed_parameters_are_decided_before_running():
    """候选方法、候选数、重排模型与模型版本在运行前固定；改动必须整体重跑再比较。"""
    assert CANDIDATE_METHOD == "embedding"
    assert CANDIDATE_COUNT == 9
    assert RERANK_MODEL == "BAAI/bge-reranker-base"
    assert RERANK_REVISION == "2cfc18c9415c912f9d8155881c133215df768a70"


def test_rerank_maps_ids_to_their_scores_and_reorders():
    """重排后 ID 与其重排分数一一对应且按分数降序；不凭空产生候选外条目。"""
    candidates = _hits("C1", "C2", "C3")
    reranked = rerank_candidates(candidates, [0.2, 0.9, 0.5], top_k=3)

    assert [hit.case_id for hit in reranked] == ["C2", "C3", "C1"]
    assert [hit.score for hit in reranked] == [0.9, 0.5, 0.2]


def test_rerank_returns_only_input_candidates():
    """输出只能是输入候选的子集：top_k 小于候选数时截断，不引入额外 ID。"""
    candidates = _hits("C1", "C2", "C3")
    reranked = rerank_candidates(candidates, [0.2, 0.9, 0.5], top_k=2)

    assert [hit.case_id for hit in reranked] == ["C2", "C3"]


def test_tie_scores_keep_candidate_original_rank():
    """同分时保持候选原名次（输入顺序），结果稳定确定。"""
    candidates = _hits("C1", "C2", "C3")
    reranked = rerank_candidates(candidates, [0.5, 0.5, 0.9], top_k=3)

    assert [hit.case_id for hit in reranked] == ["C3", "C1", "C2"]


def test_empty_candidates_return_empty_without_calling_model():
    """空候选返回空列表，不调用模型。"""
    assert rerank_candidates([], [], top_k=3) == []


def test_length_mismatch_is_rejected():
    """候选与重排分数数量不一致直接报错，不静默截断。"""
    with pytest.raises(ValueError, match="长度"):
        rerank_candidates(_hits("C1", "C2"), [0.5], top_k=2)


def test_duplicate_candidate_ids_are_rejected():
    with pytest.raises(ValueError, match="重复候选.*C1"):
        rerank_candidates(_hits("C1", "C1"), [0.2, 0.9], top_k=2)


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_non_positive_integer_top_k_is_rejected(top_k):
    """top_k 必须是正整数；bool 与小数也算非法，与既有检索风格一致。"""
    with pytest.raises(ValueError):
        rerank_candidates(_hits("C1"), [0.5], top_k=top_k)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_scores_are_rejected(bad):
    """非有限重排分数（NaN/Inf）直接报错，不静默回退。"""
    with pytest.raises(ValueError, match="有限"):
        rerank_candidates(_hits("C1"), [bad], top_k=1)


def test_rerank_does_not_mutate_inputs():
    """不改动传入的候选列表与分数序列。"""
    candidates = _hits("C1", "C2")
    scores = [0.2, 0.9]

    rerank_candidates(candidates, scores, top_k=2)

    assert [hit.case_id for hit in candidates] == ["C1", "C2"]
    assert scores == [0.2, 0.9]


def test_rerank_candidates():
    """测试候选功能"""
    candidates = _hits("C1", "C2", "C3")
    rerank_scores = [0.2, 0.9, 0.5]

    reranked = rerank_candidates(candidates, rerank_scores, top_k=2)

    assert [hit.case_id for hit in reranked] == ["C2","C3"]
    assert [hit.score for hit in reranked] == [0.9, 0.5]
    for hit in reranked:
        assert hit.case_id in {"C1", "C2", "C3"}


class StubBase:
    """候选段替身：按固定顺序返回候选，并记录被请求的 top_k。"""

    def __init__(self, case_ids, scores=None):
        self.case_ids = list(case_ids)
        self.scores = list(scores) if scores is not None else [1.0] * len(self.case_ids)
        self.requested_top_k = None

    def search(self, query, *, top_k):
        self.requested_top_k = top_k
        pairs = list(zip(self.case_ids, self.scores))[:top_k]
        return [SearchHit(case_id, score) for case_id, score in pairs]

    def describe(self):
        return {"method": "stub-base"}


class StubReranker:
    """重排段替身：返回固定分数，并记录每次调用（用于验证空候选不调用模型）。"""

    def __init__(self, scores):
        self.scores = list(scores)
        self.calls = []

    def score(self, query, documents):
        self.calls.append((query, list(documents)))
        return list(self.scores[:len(documents)])


def _pipeline(case_ids, candidate_scores=None, rerank_scores=None):
    documents = {case_id: f"text-{case_id}" for case_id in case_ids}
    base = StubBase(case_ids, scores=candidate_scores)
    reranker = StubReranker([0.0] * len(case_ids) if rerank_scores is None else rerank_scores)
    return RerankRetriever(documents, base=base, reranker=reranker), base, reranker


def test_pipeline_requests_candidate_count_and_reranks():
    """候选段按 CANDIDATE_COUNT 取候选（不是 top_k），重排后只返回前 top_k。"""
    retriever, base, _ = _pipeline(["C1", "C2", "C3"], rerank_scores=[0.1, 0.9, 0.5])

    hits = retriever.search("q", top_k=2)

    assert base.requested_top_k == CANDIDATE_COUNT
    assert [hit.case_id for hit in hits] == ["C2", "C3"]
    assert [hit.score for hit in hits] == [0.9, 0.5]


def test_pipeline_rejects_duplicate_candidates_before_model_scoring():
    retriever, _, reranker = _pipeline(["C1", "C1"], rerank_scores=[0.2, 0.9])

    with pytest.raises(ValueError, match="重复候选.*C1"):
        retriever.search("q", top_k=2)

    assert reranker.calls == []
    assert retriever.query_traces() == []


def test_pipeline_skips_the_model_when_there_are_no_candidates():
    """空候选不调用模型：返回空，并记录一条与调用对应的空追溯。"""
    reranker = StubReranker([])
    retriever = RerankRetriever({"C1": "text-C1"}, base=StubBase([]), reranker=reranker)

    assert retriever.search("q", top_k=4) == []
    assert reranker.calls == []
    trace = retriever.query_traces()[0]
    assert trace["candidates"] == []
    assert trace["reranked_order"] == []


def test_pipeline_trace_keeps_candidate_and_rerank_ranks():
    """追溯保存候选原名次、原始分数、重排分数与重排后名次，且按候选原名次排列。"""
    retriever, _, _ = _pipeline(
        ["C1", "C2", "C3"], candidate_scores=[0.7, 0.6, 0.5], rerank_scores=[0.1, 0.9, 0.5],
    )

    retriever.search("q", top_k=9)
    trace = retriever.query_traces()[0]

    assert [item["case_id"] for item in trace["candidates"]] == ["C1", "C2", "C3"]
    assert [item["candidate_rank"] for item in trace["candidates"]] == [1, 2, 3]
    assert [item["candidate_score"] for item in trace["candidates"]] == [0.7, 0.6, 0.5]
    assert [item["rerank_score"] for item in trace["candidates"]] == [0.1, 0.9, 0.5]
    assert [item["rerank_rank"] for item in trace["candidates"]] == [3, 1, 2]
    assert trace["reranked_order"] == ["C2", "C3", "C1"]


def test_pipeline_trace_returned_matches_top_k_result():
    retriever, _, _ = _pipeline(["C1", "C2", "C3"], rerank_scores=[0.1, 0.9, 0.5])

    hits = retriever.search("q", top_k=1)
    trace = retriever.query_traces()[0]

    assert trace["reranked_order"] == ["C2", "C3", "C1"]
    assert trace["returned"] == [hit.case_id for hit in hits] == ["C2"]


def test_pipeline_output_is_a_subset_of_candidates():
    """重排输出只包含输入候选：不越界、不重复。"""
    retriever, _, _ = _pipeline(["C1", "C2", "C3"], rerank_scores=[0.1, 0.9, 0.5])

    hits = retriever.search("q", top_k=9)

    returned = [hit.case_id for hit in hits]
    assert sorted(returned) == ["C1", "C2", "C3"]
    assert len(returned) == len(set(returned))


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_pipeline_rejects_non_positive_integer_top_k(top_k):
    retriever, _, _ = _pipeline(["C1"], rerank_scores=[0.5])

    with pytest.raises(ValueError):
        retriever.search("q", top_k=top_k)


def test_pipeline_describe_and_run_details_report_the_fixed_configuration():
    """describe() 记录候选段与重排口径；run_details() 分开记录候选段与重排耗时。"""
    retriever, _, _ = _pipeline(["C1"], rerank_scores=[0.5])

    retriever.search("q", top_k=1)
    description = retriever.describe()
    details = retriever.run_details()

    assert description["method"] == "rerank"
    assert description["candidate"]["method"] == CANDIDATE_METHOD
    assert description["candidate"]["count"] == CANDIDATE_COUNT
    assert description["candidate"]["covers_full_corpus"] is True
    assert description["candidate"]["retriever"] == {"method": "stub-base"}
    assert description["rerank"]["scoring_direction"] == RERANK_SCORING_DIRECTION
    assert description["rerank"]["tie_break"] == "重排分数降序，同分按候选原名次升序"
    assert "activation" in description["rerank"]
    assert description["rerank"]["model"] is None          # 替身未声明模型身份
    assert len(details["timing"]["candidate_retrieval_seconds"]) == 1
    assert len(details["timing"]["rerank_seconds"]) == 1


class _StubCrossEncoder:
    """cross-encoder 替身：按配置返回输出或抛错，用于验证适配器的失败处理。"""

    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error

    def predict(self, pairs, *, batch_size, convert_to_numpy):
        if self.error is not None:
            raise self.error
        return self.output


def _bare_reranker():
    """跳过真实加载的适配器实例：只验证打分前后的校验，不加载模型、不联网。"""
    adapter = SentenceTransformerReranker.__new__(SentenceTransformerReranker)
    adapter.model_name = "stub-model"
    adapter.batch_size = 8
    return adapter


def test_real_reranker_requires_pinned_revision():
    """未绑定 revision 时直接报错，不静默加载 latest（不可复现）。"""
    with pytest.raises(ValueError, match="revision"):
        SentenceTransformerReranker(revision=None)


def test_real_reranker_rejects_empty_documents():
    with pytest.raises(ValueError, match="空候选"):
        _bare_reranker().score("q", [])


def test_real_reranker_flattens_single_column_output():
    adapter = _bare_reranker()
    adapter._model = _StubCrossEncoder(output=np.array([[0.1], [0.9]]))

    assert adapter.score("q", ["a", "b"]) == [0.1, 0.9]
    assert adapter.max_seq_length is None
    assert adapter.activation is None


def test_real_reranker_reports_failures_without_silent_fallback():
    """模型抛错、分数数量不匹配、非有限分数都必须报错，不静默回退。"""
    adapter = _bare_reranker()

    adapter._model = _StubCrossEncoder(error=RuntimeError("boom"))
    with pytest.raises(ValueError, match="重排打分失败"):
        adapter.score("q", ["a"])

    adapter._model = _StubCrossEncoder(output=np.array([0.5]))
    with pytest.raises(ValueError, match="数量"):
        adapter.score("q", ["a", "b"])

    adapter._model = _StubCrossEncoder(output=np.array([0.5, float("nan")]))
    with pytest.raises(ValueError, match="有限"):
        adapter.score("q", ["a", "b"])
