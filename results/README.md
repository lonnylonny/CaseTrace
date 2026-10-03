# 评估结果与复现入口

正式结果记录的是对应 Development benchmark 上的观测，不证明生产泛化。当前状态与后续实验见 [Current Plan](../docs/project/current-plan.md)。原始 JSON 保留完整排名、指标、配置、来源及源码/依赖指纹，本页不重复抄录。

## 已完成产物

| 交付 | 正式结果 | 解读与验收 |
|---|---|---|
| M2 | [dev-v2-bm25.json](dev-v2-bm25.json)，evaluation-result-v1 | [错误分析](dev-v2-bm25-error-analysis.md)、[M2 验收](../docs/project/tasks/m2-completion.md#codex-acceptance) |
| M3-01 | [dev-v2-bm25-m3-01.json](dev-v2-bm25-m3-01.json)，evaluation-result-v2 | 增加 timing，BM25 事实面板与 M2 一致；[验收](../docs/project/tasks/m3-01-evaluation-entry.md#codex-acceptance) |
| M3-02 | [BM25](dev-v2-bm25-m3-02.json)、[Embedding](dev-v2-embedding-m3-02.json)，evaluation-result-v2 | [同基准对照](dev-v2-bm25-vs-embedding-m3-02.md)、[验收](../docs/project/tasks/m3-02-embedding.md#codex-acceptance) |
| M3-03 | [BM25](dev-v3-bm25-m3-03-r2.json)、[Embedding](dev-v3-embedding-m3-03-r2.json)（dev-v3 qrels revision 2，各带 `.cli.txt` 终端附件），evaluation-result-v2 | [dev-v3 版本说明与确认记录](../data/evaluation/dev-v3/README.md) |
| M3-04 | [BM25](dev-v3-bm25-m3-04-fixed.json)、[Embedding](dev-v3-embedding-m3-04-fixed.json)、[Hybrid](dev-v3-hybrid-m3-04-fixed.json)（dev-v3 r2，各带 `.cli.txt`），evaluation-result-v2 | [三方法对照与无收益说明](dev-v3-hybrid-m3-04.md) |
| M3-05 | [Rerank](dev-v3-rerank-m3-05.json)（dev-v3 r2，候选段 = Embedding 全量 9 条，重排 = bge-reranker-base，带 `.cli.txt`），evaluation-result-v2 | [重排评估与对照（同样无收益）](dev-v3-rerank-m3-05.md) |
| M3-06 | [R0](dev-v3-m3-06-r0.json)、[R1](dev-v3-m3-06-r1.json)、[R2](dev-v3-m3-06-r2.json)、[R3](dev-v3-m3-06-r3.json)（dev-v3 r2，BM25 加三个 Query 词项过滤变体，各带 `.cli.txt`；`dev-v3-m3-06-r0-pre-variant.json` 是变体引入前的同配置重跑），evaluation-result-v2 | [针对性实验与产品族探针](dev-v3-m3-06-targeted-experiments.md) |
| M3-07 | [最终结果](dev-v3-m3-07-final.json)（= R3 同配置的最终复跑，带 `.cli.txt`），evaluation-result-v2 | [四方法同版汇总与选型](dev-v3-m3-07-selection.md)、[M4 检索交接](../docs/project/handoffs/m3-07-m4-retrieval-handoff.md) |
| M4-04 | [回答质量评估](dev-v3-m4-answer-evaluation.md)（accepted，学习展示范围），[v10](m4/dev-v3-answer-v10/)、[原语义审阅](m4/dev-v3-answer-v10/semantic-review.json)保留；两处措辞仅记限制，不继续修复/重跑；旧 qrels/指标不冒充新口径 | [最终验收](../docs/project/tasks/m4-04-answer-evaluation.md#2026-10-03-最终闭环验收)；[M5 接口交接](../docs/project/handoffs/m4-04-m5-handoff.md)，不自动启动 M5 |

M2 的终端输出与测试日志是对应交付的附件，不代表当前全套检查状态。dev-v3 于 2026-09-25 初次确认，2026-09-26 用户更正 Q001×C007（45 对 `human_confirmed`，revision 2）；M3-04 复验后的三方法同版结果为 `dev-v3-*-m3-04-fixed.json`，M3-05 重排结果为 `dev-v3-rerank-m3-05.json`（其候选段即 Embedding 全量 9 条，前后对比共享同一候选集合）；无 `-fixed` 后缀的 M3-04 文件保留为验收前历史结果，`dev-v3-*-m3-03-r2.json` 为单方法参考结果，旧 `dev-v3-*-m3-03.json` 保留为 r1 历史结果，**与 dev-v2 结果不可互相比较**。

M3-06 的 R1–R3 由**实验变体**方法产生（`bm25_drop_negation_labels` 等，登记在 `runner.EXPERIMENTAL_RETRIEVER_FACTORIES`），与生产方法分表；它们只在 Query 侧过滤词项，语料、索引与指标口径与 R0 相同。**M3-07 已按证据选定 R3 的配置为默认检索方案**（`recall@4 0.9600`、逐 Query 无退步、无模型依赖），最终结果另存为 `dev-v3-m3-07-final.json`；Rerank（与候选段指标相同）与 Hybrid（唯一聚合退步）不采用，但结果与实验报告全部保留；`bm25` 与 `embedding` 保留为可切换对照。选型依据与局限见 [选型报告](dev-v3-m3-07-selection.md) 第 7 节。

## 复现与比较

在项目根目录运行，输出使用新路径以保留正式产物。当前版本为 dev-v3 qrels revision 2（2026-09-26 用户更正）；`--qrels` 不指定时仍是 dev-v2：

```bash
uv sync --locked --inexact
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25 --output /tmp/casetrace-dev-v3-bm25-recheck.json
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method embedding --output /tmp/casetrace-dev-v3-embedding-recheck.json
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method rerank --output /tmp/casetrace-dev-v3-rerank-recheck.json
uv run casetrace evaluate --qrels data/evaluation/dev-v2/qrels.json --method bm25 --output /tmp/casetrace-dev-v2-bm25-recheck.json
# M3-07 选定的默认检索方案（BM25 + Query 过滤）：
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25_drop_negation_labels --output /tmp/casetrace-dev-v3-m3-07-final-recheck.json
uv run python tmp/m3_07_final_recheck.py   # 与 dev-v3-m3-07-final.json / R3 逐字段比对
```

调用路径与字段说明见 [M4 检索交接说明](../docs/project/handoffs/m3-07-m4-retrieval-handoff.md)。


Embedding 需要预先准备[固定版本模型](../docs/project/research/m3-02-embedding-model-selection.md)，默认离线加载。向量缓存可重建，不能代替模型权重缓存。**Rerank** 还额外需要一个 cross-encoder（`BAAI/bge-reranker-base`，revision 见 `src/casetrace/retrieval/rerank.py` 的 `RERANK_REVISION`）；未绑定 revision 时直接报错，不静默加载 latest，模型缺失或版本不符也不会回退。

- **输入与代码：** 先核对报告的 benchmark、retrieval、metrics、reproducibility。历史运行可能来自未提交工作区；HEAD 和哈希只标识版本，复现还需取得对应源码与依赖。当前源码重跑不等于按字节重建 M2 的旧格式报告。
- **同方法复跑：** 固定数据、源码、模型与配置后比较 benchmark / retrieval / metrics / queries / summary；generated_at、timing 和运行时 Git 状态可能变化。绝对缓存路径随机器变化，不冒充质量差异。
- **跨方法比较：** 必须同 Corpus / Query / qrels 与指标版本；方法配置和源码可以不同，原始分数不能跨方法当作同一量纲或相关概率。
- **数值边界：** M3-02 当前 CPU 环境实测，冷暖缓存排名与指标一致，分数最大末位差 3.331e-16；不承诺跨硬件逐位一致。
- **耗时：** 报告保存计时边界及 method_details。比较时固定硬件与缓存条件；单次读数不支持效率结论，模型加载时间不由向量缓存省掉。

## 已知限制

dev-v2 只有 6 Case / 3 Query，并已反复用于开发。泛词、背景句、否定表达与产品信号问题见两份分析，供 M3 后续实验使用。dev-v1 的现存归档哈希与迁移记录仍不一致；[2026-09-29 维护](../data/evaluation/dev-v2/README.md#2026-09-29-归档校验维护)使测试明确校验该缺口及可观察的标签关系，不能据此宣称旧迁移的逐字节溯源已经通过。
