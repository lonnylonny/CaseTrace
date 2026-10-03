# M3 → M4：已完成的检索交接

本交接已完成；当前应用入口与存储接缝见 [M5 交接](m4-04-m5-handoff.md)。本页仅保留检索选型和复现入口，不再以加载 qrels 作为回答运行前置。

- 用户选定 R3：`bm25_drop_negation_labels`（H1 去否定小句 + H2 去标签词），回答默认 top_k=4。报告的 `retrieval.method` 为 `bm25_filtered_query_terms`，区分变体须看 `query_filter`。
- 选择依据见 [M3-07 报告](../../../results/dev-v3-m3-07-selection.md)；最终产物为 [final JSON](../../../results/dev-v3-m3-07-final.json)。BM25、Embedding、Hybrid、Rerank 及 R0–R3 产物都保留。
- dev-v3 r2 旧口径 Development：Recall@4=0.96、Precision@4=0.70、nDCG@4=0.9839、MRR@4=1.0；不代表 2026-10-03 新规则 GT 或泛化。规则与数据状态统一见 [Current Plan §4](../current-plan.md#4-retrieval--ground-truth--evaluation-约定)。
- Query 模板依赖仍是限制。过滤只用于检索，回答保留原始 Query；分数不是相关概率，也不能跨方法比较。`demo` 仍是原 BM25，`evaluate` 默认 dev-v2 / BM25，R3 需显式选择。

```bash
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json \
  --method bm25_drop_negation_labels --output /tmp/casetrace-m4-retrieval-check.json
uv run python tmp/m3_07_final_recheck.py /tmp/casetrace-m4-retrieval-check.json
```

回归比较 `schema_version / benchmark / retrieval / metrics / queries / summary` 六个面板；运行时间、耗时与运行环境/源码身份另记，不将其当作排名变化。
