"""M3-07 SD3 汇总表复算（只读）：用 SD2 的兼容性检查与逐 Query 差值生成报告数字。

它同时做三件事：

1. 以 BM25 正式结果为基准，对四类方法与 M3-06 变体逐一调用 `check_comparable`，
   用代码确认它们属于同一 benchmark（而不是人工比对哈希）。
2. 用 `load_per_query_scores` / `per_query_deltas` 得到逐 Query 差值，直接指出退步。
3. 打印汇总指标、逐 Query 前 4、耗时与配置，供 `results/dev-v3-m3-07-selection.md` 抄录。

只读已有产物：不读 qrels、不跑检索、不写任何文件。
运行：uv run python scripts/m3_07_selection_tables.py
"""

import hashlib
import json
from pathlib import Path

from casetrace.evaluation.compare import (
    check_comparable,
    load_per_query_scores,
    per_query_deltas,
)

ROOT = Path(__file__).resolve().parents[1]

# 四类交付方法（同 dev-v3 qrels revision 2）。第一项同时作为差值基准。
METHODS = (
    ("BM25", "results/dev-v3-bm25-m3-04-fixed.json"),
    ("Embedding", "results/dev-v3-embedding-m3-04-fixed.json"),
    ("Hybrid", "results/dev-v3-hybrid-m3-04-fixed.json"),
    ("Rerank", "results/dev-v3-rerank-m3-05.json"),
)
# M3-06 的 BM25 Query 过滤变体：同一 benchmark 上的实验方法，是否采纳由 SD4 决定。
VARIANTS = (
    ("R0", "results/dev-v3-m3-06-r0.json"),
    ("R1", "results/dev-v3-m3-06-r1.json"),
    ("R2", "results/dev-v3-m3-06-r2.json"),
    ("R3", "results/dev-v3-m3-06-r3.json"),
)
# 变体引入前对 R0 的同配置复跑：用于回答 SD1 遗留的"9 份产物"问题，不作独立方法行。
RERUN = ("R0 复跑（变体引入前）", "results/dev-v3-m3-06-r0-pre-variant.json")

ALL = METHODS + VARIANTS
SUMMARY_KEYS = (
    "recall@1", "recall@3", "recall@4",
    "precision@1", "precision@3", "precision@4",
    "ndcg@1", "ndcg@3", "ndcg@4", "mrr@4",
)


def load(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def print_comparability() -> None:
    """基准与其余产物的同 benchmark 检查：全部走 check_comparable，不人工比对。"""
    print("\n## 1 基准与同 benchmark 检查\n")
    baseline_label, baseline_path = METHODS[0]
    baseline = load(baseline_path)
    benchmark = baseline["benchmark"]
    print(f"- 基准：{baseline_label} `{baseline_path}`")
    print(f"- qrels：`{benchmark['qrels_version']}` / {benchmark['split']} / "
          f"确认日 {benchmark['confirmed_on']} / `{benchmark['qrels_sha256']}`")
    print(f"- 语料：`{benchmark['dataset']['path']}` "
          f"`{benchmark['dataset']['sha256']}`（{baseline['retrieval']['corpus_size']} 条）")
    print(f"- 主数据：`{benchmark['reference']['sha256']}`")
    print(f"- 指标口径：ks={baseline['metrics']['ks']}、"
          f"rr_k={baseline['metrics']['reciprocal_rank_k']}")
    print()
    print("| 产物 | 可比性检查 |")
    print("| --- | --- |")
    for label, path in ALL[1:] + (RERUN,):
        report = load(path)
        try:
            check_comparable(baseline, report)
        except ValueError as error:
            raise ValueError(f"{label} `{path}` 不可比：{error}") from error
        print(f"| {label} `{path}` | 可比（`check_comparable` 返回 None） |")


def print_summary_table() -> None:
    print("\n## 2 汇总指标（dev-v3 r2，同一 benchmark）\n")
    reports = [(label, load(path)) for label, path in ALL]
    print("| 指标 | " + " | ".join(label for label, _ in reports) + " |")
    print("| --- |" + " --- |" * len(reports))
    for key in SUMMARY_KEYS:
        row = []
        for _, report in reports:
            value = report["summary"]["metrics"][key]["value"]
            row.append("不适用" if value is None else f"{value:.4f}")
        print(f"| {key} | " + " | ".join(row) + " |")


def print_query_deltas() -> None:
    """逐 Query 差值直接用用户实现的 per_query_deltas，退步单独列出。"""
    print("\n## 3 逐 Query 差值（相对 BM25，正数=提升，负数=退步）\n")
    baseline_label, baseline_path = METHODS[0]
    baseline_scores = load_per_query_scores(load(baseline_path))
    for label, path in ALL[1:]:
        deltas = per_query_deltas(baseline_scores, load_per_query_scores(load(path)))
        print(f"### {label} − {baseline_label}")
        for query_id, metrics in deltas.items():
            value = metrics["recall@4"]
            # 0 差值不写正号，其余带符号：报告里的数字与本脚本输出逐字一致。
            shown = "不可比" if value is None else (f"{value:.4f}" if value == 0 else f"{value:+.4f}")
            mark = "（退步）" if value is not None and value < 0 else ""
            print(f"- {query_id}：recall@4 {shown}{mark}")
        drops = [q for q, m in deltas.items()
                 if m["recall@4"] is not None and m["recall@4"] < 0]
        print(f"- **退步 Query：{drops or '无'}**\n")


def print_top4() -> None:
    print("\n## 4 逐 Query 前 4 与正例命中数\n")
    for label, path in ALL + (RERUN,):
        report = load(path)
        print(f"### {label}（{report['retrieval']['method']}）")
        for query in report["queries"]:
            top4 = [item["case_id"] for item in query["ranked"][:4]]
            relevant = set(query["relevant_case_ids"])
            hits = sum(1 for case_id in top4 if case_id in relevant)
            print(f"- {query['query_id']}：正例 {' '.join(query['relevant_case_ids'])}"
                  f"（{len(relevant)}）→ {' '.join(top4)}（命中 {hits}/{len(relevant)}）")
        print()


def print_timing() -> None:
    print("\n## 5 耗时与产物哈希\n")
    print("| 产物 | index_build | 逐 Query 合计 | total | SHA-256（前 16） |")
    print("| --- | --- | --- | --- | --- |")
    for label, path in ALL + (RERUN,):
        timing = load(path)["timing"]
        print(f"| {label} | {timing['index_build_seconds']:.4f}s | "
              f"{timing['queries_total_seconds']:.4f}s | {timing['total_seconds']:.4f}s | "
              f"`{sha256(path)[:16]}…` |")


def print_complexity() -> None:
    """四类方法的分阶段耗时与额外产物；配置只打印顶层参数，避免整段 models 字典。"""
    print("\n## 6 分阶段耗时与方法配置（复杂度输入）\n")
    for label, path in METHODS:
        report = load(path)
        retrieval, timing = report["retrieval"], report["timing"]
        print(f"### {label} — `{retrieval['method']}` / `{retrieval['implementation']}`")
        top_level = {key: value for key, value in retrieval.items()
                     if key in ("parameters", "model", "model_revision", "device",
                                "dimension", "local_files_only", "batch_size")}
        print(f"- 顶层配置：`{json.dumps(top_level, ensure_ascii=False)}`")
        details = timing.get("method_details")
        if details:
            print(f"- 分阶段键：`{sorted(details)}`")
        print(f"- 索引构建 {timing['index_build_seconds']:.4f}s / "
              f"逐 Query 合计 {timing['queries_total_seconds']:.4f}s / "
              f"total {timing['total_seconds']:.4f}s")
        print()


def main() -> None:
    print("# M3-07 SD3 汇总表复算（只读）")
    print_comparability()
    print_summary_table()
    print_query_deltas()
    print_top4()
    print_timing()
    print_complexity()


if __name__ == "__main__":
    main()
