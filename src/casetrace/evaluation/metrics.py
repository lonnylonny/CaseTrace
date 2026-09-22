"""检索指标：只计算传入的排名，不读取文件或调用 BM25。"""

import math


def recall_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float | None:
    """计算一条 Query 的 Recall@K。

    输入：
        ranked_case_ids：按检索排名排列的 Case ID，第一项是第 1 名。
        relevant_case_ids：这条 Query 在整个评估语料中的全部相关 Case ID。
        k：只检查排名中的前 k 条，必须是正整数。

    输出：前 k 条中相关 Case 的数量 / 全部相关 Case 的数量。
        有正例但排名为空时返回 0.0；返回不足 k 条时使用实际返回条目。
        无正例时返回 None，后续由 runner 单列并排除 Recall 均值。
        非正整数 k 抛出 ValueError（也不接受 bool 或小数）。

    前提：runner 已校验排名 ID 唯一、属于语料，且 Query × Case 标签完整。
    只靠相关 ID 集合无法识别未标注，不能用此函数替代标注完整性校验。
    """
    if type(k) is not int or k < 1:
        raise ValueError("k 必须是正整数")
    if not relevant_case_ids:
        return None

    top_k_ids = set(ranked_case_ids[:k])
    relevant_hits = top_k_ids & relevant_case_ids
    return len(relevant_hits) / len(relevant_case_ids)


def precision_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float:
    """计算一条 Query 的 Precision@K：前 K 条中相关 Case 的数量 / K。

    三个输入含义与 recall_at_k 相同，排名和标签也须先经 runner 校验。
    返回不足 K 条时分母仍为 K；空返回或无正例均返回 0.0。
    无正例 Query 后续由 runner 单列分析，不代表标注缺失。
    非正整数 K 抛出 ValueError（也不接受 bool 或小数）。
    """
    if type(k) is not int or k < 1:
        raise ValueError("k 必须是正整数")

    top_k_ids = set(ranked_case_ids[:k])
    relevant_hits = top_k_ids & relevant_case_ids
    return len(relevant_hits) / k


def reciprocal_rank_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float | None:
    """计算一条 Query 的 RR@K：前 K 条中首个相关结果的倒数排名。

    输入与 recall_at_k 相同，保留排名顺序；排名和标签须先经 runner 校验。
    有正例但前 K 条未命中（含空返回）时返回 0.0；返回不足 K 条时按实际排名计算。
    无正例返回 None，后续由 runner 单列并排除 MRR 均值。
    K 必须是正整数；M2 使用 K=4，逐 Query 的 RR@4 等权平均得到 MRR@4。
    """
    if type(k) is not int or k < 1:
        raise ValueError("k 必须是正整数")
    if not relevant_case_ids:
        return None

    for rank, case_id in enumerate(ranked_case_ids[:k], start=1):
        if case_id in relevant_case_ids:
            return 1 / rank
    return 0.0


def ndcg_at_k(
    ranked_case_ids: list[str],
    relevant_case_ids: set[str],
    k: int,
) -> float | None:
    """计算一条 Query 的二值 nDCG@K：前 K 条相关结果的整体位置质量。

    输入与 recall_at_k 相同，保留排名顺序；排名和标签须先经 runner 校验。
    前 K 条中相关 Case 的 gain 为 1、不相关为 0，第 rank 名的贡献是
    gain / log2(rank + 1)，累加得到 DCG@K；只累加实际返回的条目（不足 K 条时
    用实际数量），但保留原排名位置，不跳过不相关项重新编号。
    IDCG@K 假设全部相关 Case 依次排在最前，累加第 1 至 min(K, 正例数) 名的贡献，
    因此分母不随漏检、少返回或本次命中数缩小。
    nDCG@K = DCG@K / IDCG@K；有正例但前 K 条命中为 0（含空返回）时返回 0.0。
    无正例返回 None，后续由 runner 单列并排除 nDCG 均值。
    非正整数 K 抛出 ValueError（也不接受 bool 或小数），先校验 K 再处理无正例。
    """
    if type(k) is not int or k < 1:
        raise ValueError("k 必须是正整数")
    if not relevant_case_ids:
        return None

    dcg = 0.0
    for rank, case_id in enumerate(ranked_case_ids[:k], start=1):
        if case_id in relevant_case_ids:
            dcg += 1 / math.log2(rank + 1)

    ideal_dcg = 0.0
    for rank in range(1, min(k, len(relevant_case_ids)) + 1):
        ideal_dcg += 1 / math.log2(rank + 1)

    return dcg / ideal_dcg
