# M3-05 — Rerank

状态：**accepted（2026-09-28）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

固定 Embedding 候选，使用真实 `bge-reranker-base`；候选数配置为 10，本版 9 Case 全部进入候选。排序保持 ID/分数对应与唯一性，分别分析候选遗漏和排序错误；配置与证据见 [Rerank 报告](../../../results/dev-v3-rerank-m3-05.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Cline 完成模型适配、流水线、追踪与同版运行；Codex 完成必要修复复验。
- 用户编写 `test_rerank_candidates`，用可控分数检查 ID 次序、分数对应和候选范围；检查通过，能抓住只排序分数而未同步 ID 的错误。
- 学习未结项：全量候选下不同 K 的排名变化如何抵消，可按需补讲；不构成 M5 阻塞。

## Codex Acceptance

- **Spec：通过。** 候选唯一性、追踪与分析发现已关闭。
- **Standards：通过。** 保持原模型与数据口径，无新增业务规则。
- **历史验证：** 定向 88 passed；全套 374 passed、169 subtests passed、1 个既有 dev-v1 哈希失败。真实评估 exit 0，5/5 Query 追踪重建一致，十项指标与同版 Embedding 相同，Recall@4 = 0.86。
- **Verdict：accepted。** 重排无指标收益，结果保留；历史测试失败的后续处理见[维护记录](dev-v1-archive-hash-reconciliation.md)。
