# M4-01 — 回答契约与证据上下文

状态：**accepted（2026-10-02）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

固定 R3，从命中 Case 组装含原文与来源的 `EvidenceContext`，保留原始 Query、否定和排名；校验语料/主数据快照及已知时点，不要求 qrels。最终约束见 Current Plan §§4、7，接口见 [M5 交接](../handoffs/m4-04-m5-handoff.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Cline 完成上下文主体与周边加载/测试；Codex 补齐工序映射、主数据哈希校验及固定 R3 约束。
- 用户贡献：首版守卫/循环/返回骨架与 `background` 调用；经用户明确要求，Cline 补齐索引、白名单及对象组装。最终函数记为 Cline 完成、用户参与，检查通过。
- 用户已确认理解四类输入、来源链及白名单取舍（2026-10-01～02），不再要求重复学习。

## Codex Acceptance

### 2026-10-02 最终验收

- **Spec：通过。** 来源字段白名单、快照身份、固定 R3 及用户学习确认齐备。
- **Standards：通过。** 保持数据/检索/上下文职责，无新增抽象。
- **历史验证：** answer 27 passed；全套 469 passed、169 subtests passed；ruff 通过。Q005 上下文及泄漏检查通过，R3 六个可比面板一致。
- **Verdict：accepted。** 不改变 Case draft 或 GT 状态。
