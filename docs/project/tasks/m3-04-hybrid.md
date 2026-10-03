# M3-04 — Hybrid

状态：**accepted（2026-09-27）**。本次仅精简记录，不重新验收；当前入口见 [Current Plan](../current-plan.md)。

## Codex Plan

两路 BM25 / Embedding 用 RRF 融合，保留候选来源、名次及分数追踪；固定 `k=60`、每路候选 10，同分按 Case ID。实验允许无收益；参数和结果见 [Hybrid 报告](../../../results/dev-v3-hybrid-m3-04.md)。

## Handoff Baseline

已验收，无活动实施基线。清理前全文（含原基线路径、未提交记录与历史检查）保存在 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline) 指定的 `before/` 目录；本摘要不替代历史实施基线。

## Cline Report

- Agent 完成融合实现、runner 接入、软件检查及同版三方法运行；正式产物为 `*-m3-04-fixed.json`，旧产物保留。
- RRF 函数由 Cline 示范写入，用户逐行复述确认理解，不能记作用户独立编码。用户完成 Q005 证据分析并经复核。

## Codex Acceptance

- **Spec：通过。** 唯一性、融合追踪及输入契约问题已修复复验。
- **Standards：通过。** 正式产物绑定同版配置与源码，没有按结果改标签或参数。
- **历史验证：** 三条正式评估命令 exit 0；BM25 / Embedding / Hybrid Recall@4 = 0.86 / 0.86 / 0.76，融合追踪可独立重算。原全套的 dev-v1 哈希失败已由后续维护处理。
- **Verdict：accepted。** Hybrid 未带来收益，保留实验结论，不作为最终回答检索方案。
