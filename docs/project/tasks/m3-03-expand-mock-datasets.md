# M3-03 — Development 数据扩充

状态：**accepted（2026-09-26）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

扩充 Development、完整配对及用户确认，并在同一版 benchmark 上重跑 BM25 / Embedding。最终数据身份、来源家族与时点依据见 [dev-v3 说明](../../../data/evaluation/dev-v3/README.md)；有效相关性规则见 Current Plan §4。

发布 dev-v3 revision 2：9 Case × 5 Query、45 对，正例 5 / 2 / 2 / 2 / 4；用户确认发生于旧口径，不代表 2026-10-03 新规则 GT。Case 文本仍为 draft，生成目标与来源家族不等于已验证的同义覆盖。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。 M3-03 原机器早期快照丢失，历史逐字节差异归属仍有限；本次快照不能恢复该证据。

## Cline Report

- Agent 完成数据准备、loader 版本接入及两份 `*-m3-03-r2.json`；原 dev-v2 与 r1 产物保留，入口见 [results](../../../results/README.md)。
- 用户编写缺失交叉配对测试；Cline 补正向对照。Codex 复核通过，测试能区分缺配对与哈希/确认状态失败。
- 用户于 2026-09-26 明确确认 SD5 学习；代码贡献、学习确认和 Ground Truth 确认分别记录。

## Codex Acceptance

- **Spec：通过。** 标签/理由及覆盖声明的发现已关闭，旧版保留与新版比较满足要求。
- **Standards：通过。** 原工作区与本包变更的归属按可用基线核对。
- **历史验证：** 最终定向 68 passed；BM25 / Embedding r2 均 exit 0、同版 Recall@4 均为 0.86。更早全套的 dev-v1 哈希失败属于历史记录，当前处理见[维护记录](dev-v1-archive-hash-reconciliation.md)。
- **Verdict：accepted。** 小样本开发结果不证明泛化。
