# M3-01 — 多方法评估入口

状态：**accepted（2026-09-23）**。当前交付见 [Current Plan](../current-plan.md)。

## Codex Plan

以 dev-v2 BM25 为回归基线，提供多方法入口、公共检索契约及可复现耗时报告，保持指标与标签不变。

**后续沿用的决定：** 公共契约为 `search(query, *, top_k)` 与 `describe()`，命中词项允许缺失；方法选择由 runner 注册表负责，CLI 透传。计分与输入守卫共用，评估器不读取 BM25 内部索引。稳定配置与运行耗时分开，计时边界随报告保存。

## Handoff Baseline

已验收，无活动基线；原始起点与差异通过 Git 查阅。后续包使用各自激活时的基线。

## Cline Report

- 已交付公共契约、方法选择、耗时与独立 `evaluation-result-v2` BM25 结果；M2 原产物保留，结果入口见 [results](../../../results/README.md)。
- **用户代码：** 用户完成 CLI `--method` 声明及 `method=args.method` 透传，已复核。Cline 完成其余接入与测试。
- **学习未结项：** 耗时边界与确定性比较已讲，原报告未记录用户最终确认；替身方法如何证明入口可替换可按需补讲。代码验收不替代学习确认。
- **非阻塞取舍：** CLI 与 runner 各自保留 BM25 默认值；报告使用实现自报名而非注册名。仅在后续实际需要时调整，不自动形成新任务。

## Codex Acceptance

- **Spec / Standards：** 分别 0 findings，公共接口与报告满足交付边界。
- **实际验证（2026-09-23）：** 定向 60 passed；全套 289 passed、169 subtests passed、1 failed（既有 dev-v1 归档哈希）。BM25 evaluate 与 demo 成功，当时未注册的方法退出 2 且不落盘。
- **回归结论：** 新结果的 benchmark / retrieval / metrics / queries / summary 与 M2 一致；新增计时不改变排名、分数或指标。比较基于交接快照与工作树，非仅按当时 HEAD 归因。
- **Verdict：accepted。** 不代表方法比较或最终选型完成。
