"""Rerank 检索：固定候选生成方法 → 候选原文与 Query 配对 → 重排模型重新排序。

职责分层（本模块只做三件事）：
1. 候选生成：交给固定的第一段检索方法（本版为 Embedding），取前 CANDIDATE_COUNT 条；
2. 重排计分：把 (Query, 候选原文) 逐对交给重排模型（cross-encoder），得到相关分数；
3. 重排输出：按重排分数重排候选，返回前 top_k 条，同时保存候选原名次、原始分数与重排分数。

重排是流水线组件，不是新的「召回」阶段：输出只能是输入候选的子集，候选外的正例无法被重排找回。
重排分数是模型给的相关性分数（越高越相关），不是相关概率，也不与候选段的原始分数可比。
相关性标签只参与计分，不进入候选生成或重排计分。
"""

from collections.abc import Sequence
import math
from time import perf_counter
from typing import Protocol

import numpy as np

from casetrace.retrieval.base import Retriever, SearchHit
from casetrace.retrieval.embedding import EmbeddingRetriever

# 候选生成方法：依据 M3-04 已验收结果固定（Embedding 的 Recall@3 / nDCG@4 高于 BM25，Hybrid 无收益）。
CANDIDATE_METHOD = "embedding"
# 候选数：本版语料 9 条，全量候选把「候选截断」与「重排排序」两个变量隔离；覆盖全部语料。
# 候选数通常覆盖主评估 K，以实际可用候选为准；本版 9 即全量，改动必须整体重跑再比较。
CANDIDATE_COUNT = 9
# 重排模型身份与评分方向：cross-encoder（真实重排模型），分数越高越相关。
RERANK_MODEL = "BAAI/bge-reranker-base"
# 模型 revision 必须在真实加载前绑定（固定 revision 才能让「同一结果可复现」成立）。
# 2026-09-27 绑定下载到本机 HF 缓存的提交号（官方站不可达，经 hf-mirror.com 取得，内容按该提交固定）。
RERANK_REVISION = "2cfc18c9415c912f9d8155881c133215df768a70"
RERANK_DEVICE = "cpu"
# 批量处理：一次交给模型的 (Query, 候选) 对数量；只影响速度，不改变分数与排序。
RERANK_BATCH_SIZE = 8
# 评分方向：分数越高越相关；报告如实记录，避免把分数当成概率或反向解读。
RERANK_SCORING_DIRECTION = "higher_is_more_relevant"
# 逐 Query 追溯字段名：评估器据此写入报告顶层（hybrid 用 fusion_trace，rerank 用自己的键）。
TRACE_KEY = "rerank_trace"


def _validate_unique_candidates(candidates: Sequence[SearchHit]) -> None:
    """拒绝候选段重复 ID，避免重复输出和歧义名次。"""
    seen: set[str] = set()
    for hit in candidates:
        if hit.case_id in seen:
            raise ValueError(f"重复候选 Case ID：{hit.case_id}")
        seen.add(hit.case_id)


def rerank_candidates(
    candidates: Sequence[SearchHit],
    rerank_scores: Sequence[float],
    *,
    top_k: int,
) -> list[SearchHit]:
    """把一条 Query 的候选按重排分数重新排序，返回前 top_k 条。

    行为契约（tests/retrieval/test_rerank.py 是这些条款的可执行版本）：

    - candidates 按候选原名次升序排列（第 1 名在前）；rerank_scores 与其一一对应、长度相等。
    - 输出只包含输入候选（ID 与重排分数一一对应），不虚构候选外条目；同分时保持候选原名次
      （即输入顺序），结果稳定且确定。
    - 空候选（与空分数）返回空列表，不调用模型；长度不匹配抛 ValueError；非有限分数抛 ValueError，
      不静默回退、不生成成功报告。
    - top_k 必须是正整数（bool、小数、0 或负数都算非法输入，抛 ValueError）。
    - 每条返回的 SearchHit 的 score 是重排分数，matched_terms 为 None（cross-encoder 不提供词项）。
    - 不修改传入的 candidates 与 rerank_scores。
    """
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k 必须是正整数")
    if len(candidates) != len(rerank_scores):
        raise ValueError("candidates 与 rerank_scores 长度必须一致")
    _validate_unique_candidates(candidates)
    if not candidates:
        return []

    scores = [float(score) for score in rerank_scores]
    for score in scores:
        if not math.isfinite(score):
            raise ValueError("重排分数必须是有限数值")

    # 同分时按候选原名次（enumerate 的下标，0 起）升序；下标唯一，结果确定。
    ranked = sorted(range(len(candidates)), key=lambda index: (-scores[index], index))
    return [
        SearchHit(candidates[index].case_id, scores[index], None)
        for index in ranked[:top_k]
    ]


class Reranker(Protocol):
    """重排模型需要提供的最小行为：Query 与候选文本 → 一一对应的相关分数。

    分数越高越相关；模型失败、数量不匹配或非有限分数由实现负责报错，不静默回退。
    """

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """返回与 documents 顺序一一对应的分数；空候选由调用方拦截，不调用模型。"""
        ...


def _flatten_scores(raw: object) -> list[float]:
    """把模型输出整理成一条分数序列：每个 (Query, 候选) 输入对应一个分数。

    一维输出直接使用；(n, 1) 输出取最后一列；其余形状原样展开，交由调用方做数量校验。
    """
    array = np.asarray(raw, dtype=float)
    if array.ndim == 2 and array.shape[1] == 1:
        array = array[:, 0]
    return [float(value) for value in array.reshape(-1)]


class SentenceTransformerReranker:
    """sentence-transformers 的 CrossEncoder 适配器；库只在真正构造时导入，替身测试不需要它。

    默认 `local_files_only=True`（离线优先）：评估运行不联网解析 revision，也避免网络故障
    伪装成模型问题；首次下载用显式命令完成（见 SD4），或按需把该参数设为 False。
    未绑定 revision 时直接报错，不静默加载 latest。
    """

    def __init__(
        self,
        model_name: str = RERANK_MODEL,
        *,
        revision: str | None = RERANK_REVISION,
        device: str = RERANK_DEVICE,
        local_files_only: bool = True,
        batch_size: int = RERANK_BATCH_SIZE,
    ):
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.local_files_only = local_files_only
        self.batch_size = batch_size
        started = perf_counter()
        self._model = self._load_model()
        # 冷启动（首次读权重）明显更慢；这里只记录本次运行的观测值。
        self.load_seconds = perf_counter() - started

    def _load_model(self):
        """加载 cross-encoder 并把异常转成可执行的错误信息；未绑定 revision 直接报错。"""
        if not self.revision:
            raise ValueError(
                "重排模型必须固定 revision：未绑定版本时加载 latest 会让结果不可复现；"
                "请先下载模型并在 rerank.RERANK_REVISION 绑定具体版本"
            )
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:
            raise ValueError(
                "Rerank 依赖缺失：无法导入 sentence_transformers；"
                "请先按 pyproject.toml 安装依赖"
            ) from error
        try:
            return CrossEncoder(
                self.model_name,
                revision=self.revision,
                device=self.device,
                local_files_only=self.local_files_only,
            )
        except Exception as error:
            raise ValueError(
                f"重排模型加载失败 | {self.model_name}@{self.revision} | "
                f"{type(error).__name__}: {error}"
            ) from error

    @property
    def max_seq_length(self) -> int | None:
        """模型自带的最大输入长度（token 数）；截断记录用它，不另编一个常数。"""
        value = getattr(self._model, "max_length", None)
        return None if value is None else int(value)

    @property
    def activation(self) -> str | None:
        """模型输出上的默认激活函数名（本模型为 Sigmoid）。

        记它是因为分数经激活后落在 [0,1]，容易被误读成概率；本项目不赋予未校准的概率含义。
        """
        function = getattr(self._model, "default_activation_function", None)
        return None if function is None else type(function).__name__

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """逐对打分：(query, 每条候选文本) → 分数序列；校验数量与有限性，异常直接报错。"""
        if not documents:
            raise ValueError("空候选不调用重排模型")
        try:
            raw = self._model.predict(
                [(query, text) for text in documents],
                batch_size=self.batch_size,
                convert_to_numpy=True,
            )
        except Exception as error:
            raise ValueError(
                f"重排打分失败 | {self.model_name} | {type(error).__name__}: {error}"
            ) from error
        values = _flatten_scores(raw)
        if len(values) != len(documents):
            raise ValueError(
                f"重排分数数量与候选不一致：候选 {len(documents)} 条，分数 {len(values)} 个"
            )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("重排分数存在非有限值（NaN/Inf），无法用于排序")
        return values


class RerankRetriever:
    """固定候选生成方法 + 重排模型组成的流水线：候选 → 配对打分 → 重排输出。

    构造时接收与其它检索器相同的 `documents`（case_id → 历史检索文本）：
    候选段默认用 CANDIDATE_METHOD 对应的真实检索器，重排段默认用真实 cross-encoder；
    测试可注入替身（base / reranker 参数）避免加载模型。

    检索不接收相关性标签：候选与重排都只依赖 Query 文本，换 qrels 不改变候选与重排。
    逐 Query 追溯（候选原名次、原始分数、重排分数与重排后名次）按 search 调用顺序记在
    query_traces() 里，供评估器写入报告顶层；它不属于排名、分数或指标的可比面板。
    """

    def __init__(
        self,
        documents: dict[str, str],
        *,
        base: Retriever | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        if not documents:
            raise ValueError("检索语料不能为空")
        blank = sorted(case_id for case_id, text in documents.items() if not text.strip())
        if blank:
            raise ValueError(f"每条历史案例必须有可检索的文本：{blank}")
        self.case_ids = sorted(documents)
        self.texts = {case_id: documents[case_id] for case_id in self.case_ids}
        # 先构造重排段：未绑定 revision 等配置错误在加载昂贵的候选模型之前就暴露出来。
        self._reranker = SentenceTransformerReranker() if reranker is None else reranker
        self._base = EmbeddingRetriever(documents) if base is None else base
        self._traces: list[dict] = []
        self.candidate_seconds: list[float] = []
        self.rerank_seconds: list[float] = []
        self.trace_key = TRACE_KEY

    @property
    def covers_full_corpus(self) -> bool:
        """候选数是否覆盖全部语料（候选数大于等于语料条数即视为覆盖）。"""
        return len(self.case_ids) <= CANDIDATE_COUNT

    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        """候选段取前 CANDIDATE_COUNT 条，重排后返回前 top_k 条；空候选不调用模型。"""
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k 必须是正整数")

        candidate_started = perf_counter()
        candidates = self._base.search(query, top_k=CANDIDATE_COUNT)
        self.candidate_seconds.append(perf_counter() - candidate_started)
        _validate_unique_candidates(candidates)

        if not candidates:
            # 空候选不调用模型：返回空并记录一条空追溯，保持与 search 调用一一对应。
            self.rerank_seconds.append(0.0)
            self._traces.append(self._trace_entry([], [], [], []))
            return []

        texts = [self.texts[hit.case_id] for hit in candidates]
        rerank_started = perf_counter()
        scores = self._reranker.score(query, texts)
        self.rerank_seconds.append(perf_counter() - rerank_started)

        # 一次算出全量重排顺序，返回的前 top_k 条从同一个结果切片，避免重复计分。
        ordered = rerank_candidates(candidates, scores, top_k=len(candidates))
        returned = ordered[:top_k]
        self._traces.append(self._trace_entry(candidates, scores, ordered, returned))
        return returned

    def _trace_entry(
        self, candidates: Sequence[SearchHit], scores: Sequence[float],
        ordered: Sequence[SearchHit], returned: Sequence[SearchHit],
    ) -> dict:
        """逐 Query 追溯：候选原名次 + 原始分数 + 重排分数 + 重排后名次。"""
        rerank_rank = {hit.case_id: rank for rank, hit in enumerate(ordered, start=1)}
        return {
            "candidate_method": CANDIDATE_METHOD,
            "candidate_count": CANDIDATE_COUNT,
            "covers_full_corpus": self.covers_full_corpus,
            "candidates": [
                {
                    "case_id": hit.case_id,
                    "candidate_rank": index,
                    "candidate_score": hit.score,
                    "rerank_score": scores[index - 1],
                    "rerank_rank": rerank_rank[hit.case_id],
                }
                for index, hit in enumerate(candidates, start=1)
            ],
            "reranked_order": [hit.case_id for hit in ordered],
            "returned": [hit.case_id for hit in returned],
        }

    def describe(self) -> dict:
        """报告用的方法元数据：候选段配置、重排模型身份与固定口径。"""
        return {
            "method": "rerank",
            "implementation": "casetrace.retrieval.rerank.RerankRetriever",
            "candidate": {
                "method": CANDIDATE_METHOD,
                "count": CANDIDATE_COUNT,
                "covers_full_corpus": self.covers_full_corpus,
                "retriever": self._base.describe(),
            },
            "rerank": {
                "model": getattr(self._reranker, "model_name", None),
                "model_revision": getattr(self._reranker, "revision", None),
                "device": getattr(self._reranker, "device", None),
                "batch_size": getattr(self._reranker, "batch_size", None),
                "max_seq_length": getattr(self._reranker, "max_seq_length", None),
                "activation": getattr(self._reranker, "activation", None),
                "scoring_direction": RERANK_SCORING_DIRECTION,
                "candidate_text": "候选文本使用候选段检索所用的同一条历史检索文本（build_documents）",
                "truncation": (
                    "超过模型 max_seq_length 的 (Query,候选) 文本由模型侧截断；"
                    "max_seq_length 已记入本字段，实际截断以模型配置为准"
                ),
                "tie_break": "重排分数降序，同分按候选原名次升序",
            },
            "note": (
                "重排只对候选段返回的候选排序，输出是候选的子集，候选外的正例无法被重排找回；"
                "重排分数不是相关概率，也不与候选段的原始分数可比。"
            ),
        }

    def run_details(self) -> dict:
        """本次运行的分阶段耗时与候选段观测值；不参与排名、分数与指标的比较。"""
        details: dict = {
            "timing": {
                "candidate_retrieval_seconds": list(self.candidate_seconds),
                "rerank_seconds": list(self.rerank_seconds),
                "candidate_total_seconds": sum(self.candidate_seconds),
                "rerank_total_seconds": sum(self.rerank_seconds),
                "rerank_model_load_seconds": getattr(self._reranker, "load_seconds", None),
                "note": "随机器、冷启动与缓存状态变化；比较方法时必须忽略。",
            },
        }
        provider = getattr(self._base, "run_details", None)
        if provider is not None:
            details["candidate"] = provider()
        return details

    def query_traces(self) -> list[dict]:
        """按 search 调用顺序返回逐 Query 追溯，供评估器写入报告顶层。"""
        return list(self._traces)
