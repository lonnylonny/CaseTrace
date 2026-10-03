"""结果对照工具：把评估报告的逐 Query 指标读成可比映射，并按 Query 计算差值。

只做两件事：

1. `load_per_query_scores` 读取报告 `queries[].scores`，得到 `{query_id: {指标: 值}}`，
   并校验键集合与 M2 口径一致；指标口径本身仍由 runner 定义，这里不另算一遍。
2. `per_query_deltas` 按 Query 计算 `after − before`，供 M3-06 证据表与 M3-07 汇总复用。

本模块只接受已经生成好的报告对象：不读 qrels、不读文件、不改传入对象，
也不判断两份结果是否同一 benchmark（那是 M3-07 的对照前检查）。
`None` 表示该指标对这条 Query 不适用（例如无正例 Query 的 Recall），与 `0.0` 不同。
"""

from collections.abc import Mapping
import math
from typing import Any

from casetrace.evaluation.runner import SCORE_KEYS

# 逐 Query 指标的键集合（recall/precision/ndcg @1/3/4 与 rr@4）来自 runner，
# 这里不重新抄一份：口径变化时读取函数与应用它的分析脚本一起失效，而不是悄悄错位。
PER_QUERY_METRIC_KEYS = tuple(SCORE_KEYS)

# 报告对比前必须逐字段一致的清单：报告格式版本、benchmark 身份（qrels / 语料 / 主数据）与指标口径。
# 只收 sha256 这类实质判据，不收 .path：同一份文件换目录后 sha256 不变，路径变化不应判为不可比；
# 版本号、确认日期等可读字段保留是为了让报错直接说明差异，而不是只给两个哈希。
# 顺序即报错顺序：校验在第一个不一致的字段处停止，不汇总全部差异。
IDENTITY_PATHS = (
    "schema_version",
    "benchmark.qrels_version",
    "benchmark.qrels_sha256",
    "benchmark.split",
    "benchmark.confirmed_on",
    "benchmark.dataset.sha256",
    "benchmark.reference.sha256",
    "metrics.ks",
    "metrics.reciprocal_rank_k",
    "metrics.summary_metric_keys",
    "metrics.definitions",
    "metrics.no_relevant_policy",
)


def load_per_query_scores(report: Mapping[str, Any]) -> dict[str, dict[str, float | None]]:
    """从一份评估报告读出逐 Query 指标：`{query_id: {指标: 数值或 None}}`。

    行为契约（可执行版本见 tests/evaluation/test_compare.py）：

    - 只读 `report["queries"]`：必须是含 `query_id` 与 `scores` 的非空列表。
    - `query_id` 必须是非空字符串且不重复；重复会让同一 Query 被对照两次，直接报错。
    - 每条 Query 的 `scores` 键集合必须与 `runner.SCORE_KEYS` 完全一致（多、少都报错）。
    - 值必须是有限数值或 `None`；拒绝 bool（`True`/`False` 不是指标值）与非有限数。
    - 不修改传入的报告，返回新的字典。
    """
    if not isinstance(report, Mapping):
        raise ValueError("结果报告 | 顶层必须是 JSON 对象")

    rows = report.get("queries")
    if not isinstance(rows, list) or not rows:
        raise ValueError("结果报告 | queries | 必须是非空列表")

    expected_keys = set(PER_QUERY_METRIC_KEYS)
    scores_by_query: dict[str, dict[str, float | None]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"结果报告 | queries[{index}] | 必须是 JSON 对象")
        query_id = row.get("query_id")
        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError(f"结果报告 | queries[{index}] | query_id | 必须是非空字符串")
        if query_id in scores_by_query:
            raise ValueError(f"结果报告 | queries[{index}] | query_id | 重复：{query_id}")

        scores = row.get("scores")
        if not isinstance(scores, Mapping):
            raise ValueError(f"结果报告 | queries[{index}] | scores | 必须是 JSON 对象")
        actual_keys = set(scores)
        if actual_keys != expected_keys:
            raise ValueError(
                f"结果报告 | Query[{query_id}] | scores | 键集合与 M2 口径不符："
                f"期望 {sorted(expected_keys)}，实际 {sorted(actual_keys)}"
            )

        values: dict[str, float | None] = {}
        for key, value in scores.items():
            if value is None:
                values[key] = None
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"结果报告 | Query[{query_id}] | {key} | 必须是数值或 None，实际 {value!r}"
                )
            if not math.isfinite(float(value)):
                raise ValueError(
                    f"结果报告 | Query[{query_id}] | {key} | 必须是有限数值，实际 {value!r}"
                )
            values[key] = float(value)
        scores_by_query[query_id] = values

    return scores_by_query


def per_query_deltas(
    before: Mapping[str, Mapping[str, float | None]],
    after: Mapping[str, Mapping[str, float | None]],
) -> dict[str, dict[str, float | None]]:
    """逐 Query、逐指标计算 `after − before`，供本包与 M3-07 的证据表使用。

    契约（由用户实现与测试，对应 tests/evaluation/test_compare.py）：

    - 输入形态与 `load_per_query_scores` 的输出一致：`{query_id: {指标: 数值或 None}}`。
    - 返回 `{query_id: {指标: after − before}}`；键集合与输入一致，不修改传入的映射。
    - 两份结果的 Query 集合不一致（多、少或两侧都有对方没有的）时报 ValueError，
      错误信息要能指出两侧各自的差异，便于判断是不是拿错了两份报告。
    - 同一 Query 两侧的指标键集合不一致时报 ValueError，并指出缺失或多出的键。
    - 任一侧该指标的值为 `None` 时（该指标对这条 Query 不适用）结果记 `None`，
      表示“不可比较”；不得当成 0，也不参与均值。
    - 不做 benchmark 兼容性判断（语料、qrels、指标口径是否同一版本属于 M3-07）。

    提示：
    - Query 集合与指标键集合的差异用集合运算一次算出即可（例如 `set(a) ^ set(b)`）。
    - `None` 必须与 `0.0` 分开处理：`None` 参与算术会抛 TypeError，先判断再相减。
    - 差值直接用浮点相减，不在这里做四舍五入或阈值判断（展示精度留给调用方）。
    """

    only_in_before = sorted(set(before) - set(after))
    only_in_after = sorted(set(after) - set(before))
    if only_in_before or only_in_after:
        raise ValueError(
            "Query 集合不一致 | "
            f"仅 before 有 {only_in_before}，仅 after 有 {only_in_after}"
        )

    compare_result = {}
    for query_id, compare_scores in before.items():
        compare_result[query_id] = {}

        after_scores = after[query_id]
        only_in_before_keys = sorted(set(compare_scores) - set(after_scores))
        only_in_after_keys = sorted(set(after_scores) - set(compare_scores))
        if only_in_before_keys or only_in_after_keys:
            raise ValueError(
                f"Query[{query_id}] 指标键不一致 | "
                f"仅 before 有 {only_in_before_keys}，仅 after 有 {only_in_after_keys}"
            )

        for metric, before_value in compare_scores.items():
            after_value = after_scores[metric]
            if before_value is None or after_value is None:
                compare_result[query_id][metric] = None
                continue
            compare_result[query_id][metric] = after_value - before_value

    return compare_result

def _report_field(report:Mapping[str, Any], path:str, side:str) -> Any:
    """按 'a.b.c' 形式从报告里取值；字段缺失抛 ValueError，不修改传入的报告。"""
    current = report
    for part in path.split(".") :
        if not isinstance(current,Mapping) or part not in current:
            raise ValueError(f"结果报告 | {path} | {side}侧缺少该字段")
        current = current[part]
    return current



def check_comparable(left: Mapping[str, Any], right: Mapping[str, Any]) -> None:
    """两份报告在同一 Corpus / Query / qrels / 指标口径下可比时返回 None；否则抛 ValueError。"""

    for indentity_path in IDENTITY_PATHS:
        left_value = _report_field(left, indentity_path, "左")
        right_value = _report_field(right, indentity_path, "右")
        if left_value != right_value:
            raise ValueError(
                f"结果报告 | {indentity_path} | 两侧不一致：左 {left_value}，右 {right_value}"
            )
    return None





