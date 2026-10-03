# M3-06 — 有限针对性实验

状态：**accepted（2026-09-29）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

围绕已观察问题做有限单变量实验：R0 原 BM25、R1 去否定小句、R2 去标签词、R3 两者组合；变更仅作用于检索 Query，不删生成器的原始 Query。产品族探针不形成硬规则。证据与边界见 [实验报告](../../../results/dev-v3-m3-06-targeted-experiments.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Cline 完成 R0–R3、探针、运行与报告；没有改语料/qrels，也没有在本包选型。
- 用户完成 `per_query_deltas` 的差值实现及两条测试；Cline 经授权补齐 Query/指标键集合校验。复核通过，`None` 明确表示不可比较。
- 学习未结项：退步分析、允许放弃调整及探针结论边界按需补讲；不把代码 accepted 当作全部教学确认。

## Codex Acceptance

- **Spec：通过。** 同基准对照、逐 Query 改善/退步与有界实验满足要求。
- **Standards：通过。** 复用指标定义，过滤配置可追溯；报告已区分观察与原因假设。
- **历史验证：** 定向 99 passed；R0 与原 BM25 五面板相同；R1/R2/R3 Recall@4 = 0.86 / 0.91 / 0.96。全套 431 passed、169 subtests passed、1 个后续已处理的 dev-v1 哈希失败。
- **Verdict：accepted。** 模板化 Query 与小样本限制保留，不构成泛化或生产表现。
