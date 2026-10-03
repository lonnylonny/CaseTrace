"""M3-07 汇总提取（只读）：从已验收的结果 JSON 打印身份、配置、指标与逐 Query 表格。

只读已有产物：不读 qrels、不跑检索、不改任何文件，也不修改报告对象。
用途是让汇总报告里的每个数字都能从本脚本输出复算，避免手工抄写。
运行：uv run python tmp/m3_07_summary.py
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 四类方法：交付方法的结果文件（同 dev-v3 qrels revision 2）。
METHODS = [
    ("BM25", "results/dev-v3-bm25-m3-04-fixed.json"),
    ("Embedding", "results/dev-v3-embedding-m3-04-fixed.json"),
    ("Hybrid", "results/dev-v3-hybrid-m3-04-fixed.json"),
    ("Rerank", "results/dev-v3-rerank-m3-05.json"),
]
# M3-06 的 BM25 变体运行（实验方法，尚未选型）。
VARIANTS = [
    ("R0", "results/dev-v3-m3-06-r0.json"),
    ("R1", "results/dev-v3-m3-06-r1.json"),
    ("R2", "results/dev-v3-m3-06-r2.json"),
    ("R3", "results/dev-v3-m3-06-r3.json"),
]
SUMMARY_KEYS = (
    "recall@1", "recall@3", "recall@4",
    "precision@1", "precision@3", "precision@4",
    "ndcg@1", "ndcg@3", "ndcg@4", "mrr@4",
)
IDENTITY_KEYS = ("qrels_version", "qrels_sha256", "split", "confirmed_on")


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def benchmark_identity(report: dict) -> dict:
    """取可比较性检查需要的 benchmark 身份字段；不判断是否一致。"""
    benchmark = report["benchmark"]
    identity = {key: benchmark[key] for key in IDENTITY_KEYS}
    identity["qrels_path"] = benchmark["qrels_path"]
    identity["dataset_path"] = benchmark["dataset"]["path"]
    identity["dataset_sha256"] = benchmark["dataset"]["sha256"]
    identity["reference_path"] = benchmark["reference"]["path"]
    identity["reference_sha256"] = benchmark["reference"]["sha256"]
    identity["dataset_review_status"] = benchmark["dataset_review_status"]
    identity["schema_version"] = report["schema_version"]
    return identity


def print_identity(rows: list[tuple[str, str]]) -> None:
    print("\n## 结果文件身份与配置\n")
    for label, path in rows:
        report = load(path)
        retrieval, timing = report["retrieval"], report["timing"]
        identity = benchmark_identity(report)
        print(f"### {label} — {path}")
        print(f"- SHA-256：`{sha256(path)}`")
        print(f"- schema：`{identity['schema_version']}`；方法：`{retrieval['method']}`；"
              f"实现：`{retrieval.get('implementation')}`")
        print(f"- benchmark：`{identity['qrels_version']}` / {identity['split']} / "
              f"确认日 {identity['confirmed_on']}；qrels `{identity['qrels_sha256'][:16]}…`、"
              f"语料 `{identity['dataset_sha256'][:16]}…`")
        print(f"- 语料 {retrieval['corpus_size']} 条；请求 top_k {retrieval['requested_top_k']}")
        print(f"- 耗时：index_build {timing['index_build_seconds']:.4f}s、"
              f"逐 Query 合计 {timing['queries_total_seconds']:.4f}s、"
              f"total {timing['total_seconds']:.4f}s")
        config = {key: value for key, value in retrieval.items()
                  if key not in ("implementation", "method", "note", "document_builder",
                                 "corpus_size", "requested_top_k", "libraries", "vector_dtype")}
        print(f"- 配置：`{json.dumps(config, ensure_ascii=False)}`")
        print()


def print_summary_table(rows: list[tuple[str, str]]) -> None:
    print("\n## 汇总指标（dev-v3 r2，同一 benchmark）\n")
    print("| 指标 | " + " | ".join(label for label, _ in rows) + " |")
    print("| --- |" + " --- |" * len(rows))
    reports = [load(path) for _, path in rows]
    for key in SUMMARY_KEYS:
        values = []
        for report in reports:
            value = report["summary"]["metrics"][key]["value"]
            values.append("不适用" if value is None else f"{value:.4f}")
        print(f"| {key} | " + " | ".join(values) + " |")
    print()


def print_per_query(rows: list[tuple[str, str]]) -> None:
    print("\n## 逐 Query 前 4 名与正例命中数\n")
    for label, path in rows:
        report = load(path)
        print(f"### {label}（{report['retrieval']['method']}）")
        for query in report["queries"]:
            top4 = [item["case_id"] for item in query["ranked"][:4]]
            relevant = set(query["relevant_case_ids"])
            hits = sum(1 for case_id in top4 if case_id in relevant)
            print(f"- {query['query_id']}：正例 {' '.join(query['relevant_case_ids']) or '无'}"
                  f"（{len(relevant)}）→ {' '.join(top4)}（命中 {hits}/{len(relevant)}）")
        print()


def main() -> None:
    print("# M3-07 汇总提取（只读）")
    print_identity(METHODS)
    print_identity(VARIANTS)
    print_summary_table(METHODS + VARIANTS)
    print_per_query(METHODS + VARIANTS)


if __name__ == "__main__":
    main()
