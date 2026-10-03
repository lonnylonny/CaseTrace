# M3-07 — 汇总选型

状态：**accepted（2026-09-30）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

用户选择 R3（`bm25_drop_negation_labels`，H1+H2）交给 Grounded Answer；其他方法与实验产物保留。最终结果见 [final JSON](../../../results/dev-v3-m3-07-final.json)，理由、逐 Query 差异与耗时边界见 [选型报告](../../../results/dev-v3-m3-07-selection.md)。

比较前检查 benchmark 内容身份与指标口径，模型差异允许，路径差异不等于数据不同；不兼容时停止汇总。该选择基于旧口径 Development，不能解释为新规则 GT 或 Locked Test 结论。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Agent 完成四方法/R0–R3 汇总、选型落盘与检索交接；`demo` 和 `evaluate` 的隐式默认值未随选型切换。
- 用户完成 `_report_field`、`check_comparable` 循环主体及正常/只读性测试；Cline 经授权补字段清单、错误消息及拒绝测试。复核通过。
- 学习未结项：汇总/差值、复跑可比字段及交接链路已讲，最终理解确认未完整记录，不由验收补记。

## Codex Acceptance

- **Spec：通过。** 汇总遇不兼容结果即停止，来源示例与复现路径已核对。
- **Standards：通过。** 没有重写检索或改标签，文档示例可执行。
- **历史验证：** 全套 440 passed、169 subtests passed，ruff 通过；R3 独立复跑六面板一致，Recall@4 = 0.96。九份原实验 JSON 未变，未重跑全部模型实验。
- **Verdict：accepted。** 当前复用入口已由 [M5 交接](../handoffs/m4-04-m5-handoff.md)承接。
