# M2 — Evaluation 交付摘要

状态：**accepted（2026-09-22）**。当前交付见 [Current Plan](../current-plan.md)。

## Codex Plan

交付已确认 dev-v2 上的输入校验、BM25 全排名、Recall / Precision / RR / nDCG、跨 Query 汇总、CLI 报告与错误分析。指标及数据规则统一见 [Current Plan 第 4 节](../current-plan.md#4-retrieval--ground-truth--evaluation-约定)。

## Handoff Baseline

已验收，无活动基线。历史起点、快照清单与逐步差异通过 Git 查阅；本摘要不为后续交付提供实施基线。

## Cline Report

- 已交付从输入校验到正式结果落盘的评估链路，以及 [BM25 错误分析](../../../results/dev-v2-bm25-error-analysis.md)。正式产物与复现入口见 [results](../../../results/README.md)。
- RR 讲解于 2026-09-20 accepted，用户确认理解；nDCG 实现与讲解已完成并纳入 M2 总审。后续评估功能教学已取得用户确认；验收不额外认证全部概念的掌握程度。
- 后续实验保留泛词、背景话术、否定表达、产品信号与阅读顺序问题；不因分析改变二值标签。已纠正的解释以当前错误分析为准。

## Codex Acceptance

- **Spec：** 0 open findings，含 nDCG；阅读判断与 BM25 归因的文字问题已关闭。
- **Standards：** 0 open findings；执行源码清单已补全，支持未提交工作区的版本核对。
- **实际验证（2026-09-22）：** runner/CLI 29 passed；全套 278 passed、169 subtests passed、1 failed；evaluate、demo、隔离重建与排名/分数/指标一致性验证成功。最后文字收尾未重跑测试。
- **保留限制：** 旧 dev-v1 归档哈希失败按[用户决定](../../../data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)非阻塞，原文件、预期哈希和失败测试均保留。6 × 3 仅支撑开发流程，不证明泛化。
- **Verdict：accepted。** 无待交付 M2 功能。
