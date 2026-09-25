# 评估结果与复现入口

正式结果记录的是对应 Development benchmark 上的观测，不证明生产泛化。当前状态与后续实验见 [Current Plan](../docs/project/current-plan.md)。原始 JSON 保留完整排名、指标、配置、来源及源码/依赖指纹，本页不重复抄录。

## 已完成产物

| 交付 | 正式结果 | 解读与验收 |
|---|---|---|
| M2 | [dev-v2-bm25.json](dev-v2-bm25.json)，evaluation-result-v1 | [错误分析](dev-v2-bm25-error-analysis.md)、[M2 验收](../docs/project/tasks/m2-completion.md#codex-acceptance) |
| M3-01 | [dev-v2-bm25-m3-01.json](dev-v2-bm25-m3-01.json)，evaluation-result-v2 | 增加 timing，BM25 事实面板与 M2 一致；[验收](../docs/project/tasks/m3-01-evaluation-entry.md#codex-acceptance) |
| M3-02 | [BM25](dev-v2-bm25-m3-02.json)、[Embedding](dev-v2-embedding-m3-02.json)，evaluation-result-v2 | [同基准对照](dev-v2-bm25-vs-embedding-m3-02.md)、[验收](../docs/project/tasks/m3-02-embedding.md#codex-acceptance) |

M2 的终端输出与测试日志是对应交付的附件，不代表当前全套检查状态。dev-v3 尚未用户确认，也没有正式结果；确认后的新结果使用 M3-03 约定的独立路径。

## 复现与比较

在项目根目录运行，输出使用新路径以保留正式产物：

```bash
uv sync --locked --inexact
uv run casetrace evaluate --qrels data/evaluation/dev-v2/qrels.json --method bm25 --output /tmp/casetrace-dev-v2-bm25-recheck.json
uv run casetrace evaluate --qrels data/evaluation/dev-v2/qrels.json --method embedding --output /tmp/casetrace-dev-v2-embedding-recheck.json
```

Embedding 需要预先准备[固定版本模型](../docs/project/research/m3-02-embedding-model-selection.md)，默认离线加载。向量缓存可重建，不能代替模型权重缓存。

- **输入与代码：** 先核对报告的 benchmark、retrieval、metrics、reproducibility。历史运行可能来自未提交工作区；HEAD 和哈希只标识版本，复现还需取得对应源码与依赖。当前源码重跑不等于按字节重建 M2 的旧格式报告。
- **同方法复跑：** 固定数据、源码、模型与配置后比较 benchmark / retrieval / metrics / queries / summary；generated_at、timing 和运行时 Git 状态可能变化。绝对缓存路径随机器变化，不冒充质量差异。
- **跨方法比较：** 必须同 Corpus / Query / qrels 与指标版本；方法配置和源码可以不同，原始分数不能跨方法当作同一量纲或相关概率。
- **数值边界：** M3-02 当前 CPU 环境实测，冷暖缓存排名与指标一致，分数最大末位差 3.331e-16；不承诺跨硬件逐位一致。
- **耗时：** 报告保存计时边界及 method_details。比较时固定硬件与缓存条件；单次读数不支持效率结论，模型加载时间不由向量缓存省掉。

## 已知限制

dev-v2 只有 6 Case / 3 Query，并已反复用于开发。泛词、背景句、否定表达与产品信号问题见两份分析，供 M3 后续实验使用。dev-v1 归档哈希失败按[用户决定](../data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)保留，不阻塞后续开发，也不视为迁移校验通过。
