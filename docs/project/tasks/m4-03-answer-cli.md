# M4-03 — 引用校验与 CLI

状态：**accepted（2026-10-02）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

提供 `run_answer_question`、引用守卫及文本/JSON CLI。输入输出适配与编排分开；成功、空命中、模型/格式/引用失败有独立状态。失败保留响应证据；JSON stdout 与落盘记录同源。最终状态与接口见 [M5 交接](../handoffs/m4-04-m5-handoff.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Cline 完成守卫、CLI、运行记录和回归修复。
- 用户运行失败样例并正确定位引用守卫阶段；经纠正确认“记录保留原文”与“终端不输出成功正文”的区别，以及引用可定位不等于语义支持。无新增必做编码题。
- JSON 输出提示写 stderr，解析失败保留原始文本、响应身份、耗时与用量。

## Codex Acceptance

### 2026-10-02 最终复验

- **Spec：通过。** 成功/格式失败时 `--json --output` 均输出单一合法 JSON，且与记录一致；失败不冒充成功。
- **Standards：通过。** 沿用现有职责和错误类型，无自动改写或重试。
- **历史验证：** 定向 95 passed；全套 528 passed、169 subtests passed，ruff/lock/diff 通过。真实 Q005 CLI、空命中、失败状态和 R3 排名证据齐备。
- **Verdict：accepted。** 引用验收只证明来源可定位，语义支持另由 M4-04 审阅。
