# M4-02 — 最小真实生成链路

状态：**accepted（2026-10-02）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

用 DeepSeek 非思考模式、版本化提示词和结构化契约实现一次生成；模型适配、生成与解析分离。空上下文不调用模型；保存响应实际模型身份，源文本指令只作数据。当前配置见 [M5 交接](../handoffs/m4-04-m5-handoff.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Cline 完成模型适配、契约、周边测试和复核。
- 用户实现 `generate_grounded_answer` 五段主流程并起草 `EVIDENCE_RULES`；Cline 修正 JSON 序列化、调用计时和提示词措辞。检查通过，主体用于实际运行。
- 用户完成 Q005 正常调用与删除 `C007:E007` 的真实对照，并确认理解：删除后不再引用该检查，其他历史依据仍可支撑回答。
- 学习未结项：模型别名与不可变版本、源文本提示注入边界，按下次接触代码时补讲。

## Codex Acceptance

### 2026-10-02 最终验收（含 SD3 专项复验）

- **Spec：通过。** 模型身份、源指令边界及真实证据移除对照均已验证。
- **Standards：通过。** 单次调用，职责分离，产物不含凭据，无工作流或自动重试。
- **历史验证：** answer 50 passed；全套 492 passed、169 subtests passed；ruff/lock/diff 通过。真实正常/对照运行分别 4255 / 4175 tokens，产物检查通过。
- **Verdict：accepted。** 一条开发 Query 的观察不证明普遍可靠；完整引用守卫由后续 M4-03 提供。
