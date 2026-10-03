# BM25 / Embedding / Hybrid dev-v3 r2 对照分析（M3-04）

本文件对三份**同基准正式结果**做只读对照：`results/dev-v3-bm25-m3-04-fixed.json`、`results/dev-v3-embedding-m3-04-fixed.json`、`results/dev-v3-hybrid-m3-04-fixed.json`。它不修改代码、`qrels`、标签或任何检索参数，也不把排名差距当作标签错误。结论诚实记录：**本轮等权 RRF 未带来收益**，只登记本次观测与可验证的机制线索，不构成选型结论。

## 1. 运行条件

| 项目 | 值 |
|---|---|
| benchmark | `data/evaluation/dev-v3/qrels.json`（`dev-qrels-v3` / `development` / 确认日 2026-09-26，45 对 `human_confirmed`） |
| qrels SHA-256 | `7c4e85511ba72b58b19eb3134f1935c711e0f3142e58ba118918d96afac7b4dd` |
| 语料 | `data/dev/demo-v3.json`，9 条，SHA-256 `0a29041a4e6ed11a5b31ff85a74fa8bed9b79afeb1d35158ea9430f6e5af8f0b` |
| 命令 | `uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method {bm25,embedding,hybrid} --output results/dev-v3-{method}-m3-04-fixed.json` |
| Hybrid 参数 | `rrf_rank_constant=60`、`candidates_per_route=10`（语料 9 条，等价全量）、`route_methods=["bm25","embedding"]` |
| 同版一致性 | 三份报告的 `benchmark`、顶层 `metrics` 定义、`reproducibility.source_files` 完全一致；Hybrid 的 `retrieval.routes` 与 `timing.method_details.routes` 保存两路实际配置和运行观测 |
| 产物 | bm25 `fa152352…`、embedding `81372b97…`、hybrid `bee9eeb3…`（完整哈希见结果文件及验收记录） |

2026-09-27 修订：修复重复 ID 时追溯名次与计分不符的问题，并让 Hybrid 报告保存两路实际配置/缓存观测；三方法在同一份输入和修订后源码上全部重跑。现以 `*-m3-04-fixed.json` 为正式结果；原无 `-fixed` 后缀的三份 JSON/CLI 保留为验收前历史结果，原字节未覆盖。修订前后三方法的完整排名、分数与指标均相同；新增的是可核对的运行元数据和正确的边界说明。模型/缓存与计时只反映本次运行，不据单次耗时比较效率。

## 2. 汇总指标对照（Recall-first，主 K=4）

| 指标 | BM25 | Embedding | Hybrid |
|---|---|---|---|
| recall@1 | 0.39 | 0.39 | 0.39 |
| recall@3 | 0.67 | 0.77 | 0.72 |
| recall@4 | **0.86** | **0.86** | **0.76** |
| precision@4 | 0.60 | 0.65 | 0.55 |
| ndcg@4 | 0.8871 | 0.9226 | 0.8500 |
| mrr@4 | 1.0 | 1.0 | 1.0 |

**结论：等权 RRF 未带来 Recall@4 收益（0.76 < 单方法 0.86），反而略退步。**

## 3. 逐 Query 归因

前 4 命中正例（`[x]` 表示该条是相关正例）：

| Query | 正例 | BM25 前 4 | Embedding 前 4 | Hybrid 前 4 |
|---|---|---|---|---|
| Q001 | C001、C002、C003、C004、C007 | C001 C002 C003 C004 | C001 C003 C004 C007 | C001 C003 C002 C004 |
| Q002 | C005、C008 | C005 C008 | C005 C008 | C005 C008 |
| Q003 | C005、C006 | C006 C009 C002 C005 | C006 C009 C002 C004 | C006 C009 C002 C001 |
| Q004 | C005、C008 | C008 C005 | C008 C005 | C008 C005 |
| Q005 | C001、C003、C004、C007 | C007 C006 C002 C001 | C001 C003 C007 C004 | C007 C001 C006 C002 |

- **Q001 / Q002 / Q004**：三方法前 4 命中正例数相同，无差异（Q001 三法均命中 4/5）。
- **Q003**：BM25 前 4 命中 C005+C006；Embedding 与 Hybrid 都漏掉 C005 → 单条 0.5 vs 1.0。Hybrid 继承了 Embedding 的漏检。
- **Q005**：Embedding 前 4 四中四；BM25 与 Hybrid 都只命中 C001+C007 → 单条 0.5 vs 1.0。Hybrid 继承了 BM25 的漏检。

## 4. 观察与假设（有证据支撑，但不作结论）

**4.1 Q005：前四名由两路名次共同决定。** 正例 C003 在 Embedding 排第 2、BM25 排第 8；不相关的 C006、C002 在 BM25 排第 2、第 3。RRF 累加名次贡献后，C006（0.03151）与 C002（0.03102）排在 C004（0.03101）与 C003（0.03083）之前，后两条因此落在前四名外。BM25 的命中词中，C006 包含已被 Query 排除的「碰伤」「运输」，还包含「产品」「检查」「确认」；目前没有逐词贡献或删除词项的对照实验，不能断定哪些词导致了这个次序。

**4.2 用户证据检查（2026-09-26）：** 用户指出「剥离/脱开」「焊点界面/焊盘」等不同措辞可能削弱 BM25 的词面匹配。这与 C003 在 BM25 第 8、Embedding 第 2 的观察相符，是待单变量对照的假设；当前结果只证明名次及其 RRF 贡献，不能单凭排名确认词项因果。

**4.3 融合边界。** RRF 对两路候选取并集：只在一路出现的 Case 仍可能靠前，只有两路都未纳入的 Case 才无法进入融合。本次每路请求 10 条、语料只有 9 条，因此不存在候选截断造成的遗漏；Q003、Q005 的前四名漏检来自融合后的排序。一路靠前的不相关 Case 会得到该路贡献，但也可能被两路均靠前的相关 Case 超过。后续实验如要检验词面或参数假设，应保持其余条件固定；本包不据此调参。

**4.4 分数不同量纲，不可跨方法比较。** BM25 分数是无上界词频统计，Embedding 是余弦相似度，Hybrid 是 1/(k+rank) 的名次贡献——三者分数都只是排序依据，不是相关概率。

## 5. 边界与未跑项

- 数据规模：9 条语料、5 条 Query、二值 qrels、单一 k=60，只够支撑开发期对照，不构成生产泛化结论。
- 本文件不修改代码、`qrels`、标签与任何检索参数；调整方向（权重、候选截断、k）登记为 M3-06 输入。
- 未跑：Rerank（M3-05）、针对性参数实验（M3-06）、Locked Test 对比（M6）。
- 既有历史限制不变：dev-v1 归档哈希失败按用户决定保留；dev-v3 源 Case 仍为 draft。
- 复现命令与比较边界见 [results README](README.md#复现与比较)。
