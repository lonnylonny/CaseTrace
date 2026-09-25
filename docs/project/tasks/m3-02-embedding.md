# M3-02 — Embedding 首次接入

状态：**accepted（2026-09-25）**。当前交付见 [Current Plan](../current-plan.md)。

## Codex Plan

在 dev-v2 的同一历史文本上接入真实 Embedding，并与 BM25 比较；首次接入不等于最终选型。[选模决定](../research/m3-02-embedding-model-selection.md)保留选择理由，具体配置与版本见正式结果。

**后续沿用的决定：**

- 本地 BGE small、CPU、离线优先；Query 加模型检索 instruction，文档不加；归一化后点积，固定同分顺序。模型错误明确报告，不以伪向量或静默回退生成成功结果。
- 缓存绑定模型 revision、依赖、device/dtype、编码配置、文本哈希与 Case ID；损坏缓存标记 corrupt 并重建。缓存存工作矩阵，重新读取归一化可能产生末位浮点差；当前样例中排名与指标一致，不承诺跨硬件逐位一致。
- `describe()` 提供稳定配置，`run_details()` 提供观测值并写入顶层 `timing.method_details`。记录模型输出 float32 与工作矩阵 float64 的区别。

## Handoff Baseline

已验收，无活动基线；原始快照、修正过程和接手差异通过 Git 查阅。未验收的 M3-03 使用[自己的实施基线](m3-03-expand-mock-datasets.md#handoff-baseline)。

## Cline Report

- 已交付真实模型、向量检索、缓存、registry/CLI/报告接入、同版本 BM25 与 Embedding 结果及[差异分析](../../../results/dev-v2-bm25-vs-embedding-m3-02.md)。模型实际离线加载与编码成功，dev-v2 未触发 512-token 截断；未验证跨硬件复现。
- **用户代码：** 用户完成 `rank_by_similarity`，排序、同分、K 边界、不改入参与 search 链路检查通过。Cline 完成其余实现。
- **后续实验输入：** Q001 同产品正例 C002 从 BM25 第 4 名降至 Embedding 第 6 名；归因仍为假设，见差异分析。未调整标签或预定最终组合。
- **学习未结项：** SD4 指标差异与分数量纲已讲，用户确认未记录；缓存键/状态、冷暖浮点差、配置与计时职责分离及 registry 接入仍有待讲记录。不得用 accepted 替代学习确认。
- **环境约束：** 本机实测使用 CPU；模型权重缓存与项目向量缓存不同。依赖使用 uv 锁定，保留环境内学习工具时用 `uv sync --locked --inexact`。

## Codex Acceptance

- **Spec：** 0 open findings；缓存绑定与损坏重建问题已修复并验证。
- **Standards：** 0 open findings；自描述、计时路径和状态文档已对齐。
- **实际验证（2026-09-25）：** 定向 164 passed；全套 320 passed、169 subtests passed、1 failed（既有 dev-v1 归档哈希）。BM25 / Embedding evaluate 与 demo 均成功；未知 hybrid 退出 2 且不留文件。
- **复现结论：** 两方法各自正式报告的五个可比较面板与同条件复跑相等；冷暖缓存分数最大差 3.331e-16，排名与指标一致。M2 / M3-01 原产物保留。仅验证当前 dev-v2 与 CPU/依赖条件，不证明泛化或最终选型。
- **Verdict：accepted。** 后续范围由 Current Plan 与活动包确定。
