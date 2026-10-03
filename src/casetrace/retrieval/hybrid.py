"""Hybrid 检索：把两路单方法的排名按名次融合成一路。

融合只用各路给出的**名次**，不用各路原始分数：BM25 分数与余弦相似度不在同一量纲，
相加等于把两种尺度混在一起。按排名的融合（RRF, Reciprocal Rank Fusion）对每个 Case
累加 1 /（融合常数 + 该路上的名次），因此：

- 两路都靠前的 Case 会得到两路贡献；只在一路出现的 Case 仍可能排在前面；
- 未在某一路出现的 Case 得不到那一路的贡献，也不虚构名次；
- 融合只处理两路候选的并集，两路都未出现的 Case 不会进入结果。

本模块只负责「各路排名 → 融合分数 → 融合排名」。各路自己的检索、语料与指标口径仍由既有实现负责，
相关性标签不参与融合（换 qrels 不改变候选与融合）。融合分数不是相关概率，也不与单方法分数可比。
"""

from collections.abc import Sequence

from casetrace.retrieval.base import Retriever, SearchHit
from casetrace.retrieval.bm25 import BM25Retriever
from casetrace.retrieval.embedding import EmbeddingRetriever

# 融合常数：只控制名次差异的衰减速度（越大越平缓），与指标里的 K 无关，因此分开命名。
# 运行前固定并写入报告；改动它必须整体重跑并重新比较，不能事后挑选。
RRF_RANK_CONSTANT = 60
# 每路候选上限：语料小于该值时即取全量。它决定融合能看到哪些名次，与最终返回数分开命名，
# 避免把「候选范围变化」误当成融合公式的单独效果。
CANDIDATES_PER_ROUTE = 10
# 参与融合的两路；顺序不影响计分结果。
ROUTE_METHODS = ("bm25", "embedding")


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], *, rrf_rank_constant: int,
) -> dict[str, float]:
    """把若干路的 Case ID 排名融合为 Case ID → 融合分数。

    行为契约（tests/retrieval/test_hybrid.py 是这些条款的可执行版本）：

    - 每一路的输入是按名次升序排列的 Case ID 列表，名次从 1 开始；
      单路第一名的贡献是 1/(常数+1)。
    - 一个 Case 的融合分数 = 它在每一路出现时各自算 1/(常数+该路名次)，再求和；
      未在某一路出现的 Case 不在那一路得分，也不替它编一个名次。
    - 同一路内重复出现的 Case ID 只按首次出现的名次计一次，不会重复加分。
    - 全部路都为空时返回空字典；只有一路有候选时，结果等价于该路单独的名次贡献。
    - 返回 dict[str, float]，键为去重合并后的 Case ID；字典顺序不构成契约，
      融合排名由调用方按「分数降序、同分按 Case ID 升序」确定。
    - rrf_rank_constant 必须是正整数（bool、小数、0 与负数都算非法输入，抛 ValueError）。
    - 不修改传入的 rankings 及其内部序列。
    """
    if type(rrf_rank_constant) is not int or rrf_rank_constant <= 0:
        raise ValueError("rrf_rank_constant 必须是正整数")

    fusion_result: dict[str, float] = {}

    for route in rankings:
        seen = set()
        for rank, case_id in enumerate(route, start=1):
            if case_id in seen:
                continue
            seen.add(case_id)
            fusion_result[case_id] = fusion_result.get(case_id, 0.0) + 1.0 / (rrf_rank_constant + rank)

    return fusion_result


class HybridRetriever:
    """把 BM25 与 Embedding 两路排名按名次融合成一路。

    构造时接收与其它检索器相同的 `documents`（case_id → 历史检索文本），
    默认在内部建两个真实检索器；测试可注入替身（bm25 / embedding 参数）避免加载模型。
    检索不接收相关性标签，只依赖各路对 Query 文本的排名，因此换 qrels 不改变候选与融合。

    逐 Query 的追溯信息（各路名次、融合分数）按 search 调用顺序记在 query_traces() 里，
    供评估器写入报告顶层；它不属于排名、分数或指标的可比面板。
    """

    def __init__(
        self,
        documents: dict[str, str],
        *,
        bm25: Retriever | None = None,
        embedding: Retriever | None = None,
    ) -> None:
        self._routes = {
            "bm25": BM25Retriever(documents) if bm25 is None else bm25,
            "embedding": EmbeddingRetriever(documents) if embedding is None else embedding,
        }
        self._traces: list[dict] = []

    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        """两路各取前 `CANDIDATES_PER_ROUTE`，按名次融合后返回前 top_k 条。

        每一路同一 Case 只按首次名次计一次；未在某一路出现的 Case 不得该路贡献。
        融合分数不是相关概率，也不与单方法分数可比。
        """
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k 必须是正整数")

        rankings: list[list[str]] = []
        route_ranks: dict[str, dict[str, int]] = {}
        for method in ROUTE_METHODS:
            hits = self._routes[method].search(query, top_k=CANDIDATES_PER_ROUTE)
            case_ids = [hit.case_id for hit in hits]
            rankings.append(case_ids)
            ranks: dict[str, int] = {}
            for rank, case_id in enumerate(case_ids, start=1):
                ranks.setdefault(case_id, rank)
            route_ranks[method] = ranks

        fused = reciprocal_rank_fusion(rankings, rrf_rank_constant=RRF_RANK_CONSTANT)
        # 融合排序：分数降序，同分按 Case ID 升序，结果不依赖各路输入顺序。
        ordered = sorted(fused.items(), key=lambda pair: (-pair[1], pair[0]))

        self._traces.append({
            "routes": route_ranks,
            "fusion": {case_id: score for case_id, score in ordered},
        })

        return [SearchHit(case_id, score) for case_id, score in ordered[:top_k]]

    def describe(self) -> dict:
        """报告用的方法元数据：融合方式、运行前固定的参数与口径。"""
        return {
            "method": "hybrid",
            "implementation": "casetrace.retrieval.hybrid.HybridRetriever",
            "fusion": "casetrace.retrieval.hybrid.reciprocal_rank_fusion",
            "parameters": {
                "rrf_rank_constant": RRF_RANK_CONSTANT,
                "candidates_per_route": CANDIDATES_PER_ROUTE,
                "route_methods": list(ROUTE_METHODS),
            },
            "routes": {
                method: self._routes[method].describe() for method in ROUTE_METHODS
            },
            "note": (
                "按名次融合 BM25 与 Embedding，不使用各路原始分数；融合分数不是相关概率；"
                "两路候选各取 candidates_per_route，融合同分按 Case ID 升序。"
            ),
        }

    def run_details(self) -> dict:
        """逐路保存可用的本次运行观测值，与固定配置分开。"""
        details = {}
        for method in ROUTE_METHODS:
            provider = getattr(self._routes[method], "run_details", None)
            if provider is not None:
                details[method] = provider()
        return {"routes": details}

    def query_traces(self) -> list[dict]:
        """逐 Query 追溯：按 search 调用顺序返回各路名次与融合分数，供报告顶层记录。"""
        return list(self._traces)

