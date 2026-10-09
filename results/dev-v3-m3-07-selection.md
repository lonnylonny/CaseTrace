# M3 四方法同版汇总（M3-07 SD3）

本文件汇总 M3 已验收的**同 benchmark**检索结果：BM25、Embedding、Hybrid、Rerank 四类交付方法，另列 M3-06 的 BM25 Query 过滤变体（R0–R3）作为补充证据。它是只读汇总：不修改代码、`qrels`、标签或任何检索参数，也不产生新的检索观测。

表中每个数字都由 `uv run python scripts/m3_07_selection_tables.py` 从结果 JSON 复算打印（该脚本调用 SD2 的 `check_comparable` / `load_per_query_scores` / `per_query_deltas`，不手工抄哈希）。本文件只登记观测与规则适用结果；**第 7 节记录 2026-09-30 用户拍板的最终方案、最终正式结果与复跑核对。**

## 1 运行条件与同 benchmark 核对

| 项目 | 值 |
|---|---|
| benchmark | `data/evaluation/dev-v3/qrels.json`（`dev-qrels-v3` / `development` / 确认日 2026-09-26，9 × 5 = 45 对 `human_confirmed`，revision 2） |
| qrels SHA-256 | `7c4e85511ba72b58b19eb3134f1935c711e0f3142e58ba118918d96afac7b4dd` |
| 语料 | `data/dev/demo-v3.json`，9 条，SHA-256 `0a29041a4e6ed11a5b31ff85a74fa8bed9b79afeb1d35158ea9430f6e5af8f0b` |
| 主数据 SHA-256 | `f5001bddd3dff43342a2569ceda836ddb4f5c0caca942c1c4d043d99a9131c85` |
| 指标口径 | `ks = [1, 3, 4]`、`rr_k = 4`、`summary_metric_keys` 十项、`no_relevant_policy` 与 `definitions` 在 9 份产物间一致 |
| 语料规模 / top_k | 9 条 / 请求 `top_k = 9`（= 全量，所有方法都不存在候选截断） |

**可比性检查（代码，不是人工比对）：** 以 `results/dev-v3-bm25-m3-04-fixed.json` 为基准，对另外 8 份产物逐一调用 `check_comparable`，**9 份全部返回 `None`**（`schema_version`、`benchmark.*`、`metrics.*` 共 12 条身份字段逐项一致）。

| 产物 | 方法 | 可比性 |
|---|---|---|
| `dev-v3-bm25-m3-04-fixed.json` | `bm25_okapi` | 基准 |
| `dev-v3-embedding-m3-04-fixed.json` | `embedding` | 可比 |
| `dev-v3-hybrid-m3-04-fixed.json` | `hybrid` | 可比 |
| `dev-v3-rerank-m3-05.json` | `rerank` | 可比 |
| `dev-v3-m3-06-r0.json` | `bm25_okapi`（控制组） | 可比 |
| `dev-v3-m3-06-r1.json` | `bm25_filtered_query_terms`（H1） | 可比 |
| `dev-v3-m3-06-r2.json` | `bm25_filtered_query_terms`（H2） | 可比 |
| `dev-v3-m3-06-r3.json` | `bm25_filtered_query_terms`（H1+H2） | 可比 |
| `dev-v3-m3-06-r0-pre-variant.json` | `bm25_okapi`（变体引入前复跑） | 可比 |

这同时回答了 SD1 遗留的"9 份产物"问题：**9 = 四类方法 4 + M3-06 的 R0–R3 4 + R0 变体前复跑 1**，不含其它文件。方法、模型与源码哈希允许不同（`check_comparable` 不收这些字段），只有 benchmark 身份与指标口径必须一致。

SD4 另存的最终正式结果 `results/dev-v3-m3-07-final.json` 是同一 benchmark 上的第 10 份产物（配置等于 R3），对基准的 `check_comparable` 同样返回 `None`，见第 7 节。

## 2 四方法汇总指标对照（dev-v3 r2）

| 指标 | BM25 | Embedding | Hybrid | Rerank | R0 | R1 | R2 | R3 |
|---|---|---|---|---|---|---|---|---|
| recall@1 | 0.3900 | 0.3900 | 0.3900 | 0.3900 | 0.3900 | 0.3900 | 0.3900 | 0.3900 |
| recall@3 | 0.6700 | 0.7700 | 0.7200 | 0.7700 | 0.6700 | 0.7200 | 0.8200 | 0.8700 |
| **recall@4** | **0.8600** | **0.8600** | **0.7600** | **0.8600** | **0.8600** | **0.8600** | **0.9100** | **0.9600** |
| precision@1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| precision@3 | 0.6000 | 0.7333 | 0.6667 | 0.7333 | 0.6000 | 0.6667 | 0.7333 | 0.8000 |
| precision@4 | 0.6000 | 0.6500 | 0.5500 | 0.6500 | 0.6000 | 0.6000 | 0.6500 | 0.7000 |
| ndcg@1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| ndcg@3 | 0.8165 | 0.9226 | 0.8757 | 0.9226 | 0.8165 | 0.8634 | 0.9247 | 0.9839 |
| ndcg@4 | 0.8871 | 0.9226 | 0.8500 | 0.9226 | 0.8871 | 0.8926 | 0.9347 | 0.9839 |
| mrr@4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

- **主指标 Recall@4：BM25 = Embedding = Rerank = 0.86，Hybrid = 0.76（−0.10）。** Rerank 与其候选段（Embedding）逐项相同，是 M3-05 已登记的观测。
- 四类交付方法中，只有 Hybrid 在主指标上低于 BM25；其余三者在 Recall@4 上并列，Embedding / Rerank 在 `precision@4`、`ndcg@4` 上更高（0.65 / 0.9226 对 0.60 / 0.8871）。
- R0（控制组）与 BM25 的十项指标完全相同，与 M3-06 验收记录的"五个可比面板完全相同"一致。


## 3 逐 Query 差值与前 4（退步逐条列出）

**逐 Query `recall@4`（绝对读数）：**

| Query | 正例数 | BM25 | Embedding | Hybrid | Rerank | R0 | R1 | R2 | R3 |
|---|---|---|---|---|---|---|---|---|---|
| Q001 | 5 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 |
| Q002 | 2 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Q003 | 2 | 1.00 | 0.50 | 0.50 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 |
| Q004 | 2 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Q005 | 4 | 0.50 | 1.00 | 0.50 | 1.00 | 0.50 | 0.50 | 0.75 | 1.00 |

**相对 BM25 的差值（`per_query_deltas`，正数=提升，负数=退步）：**

| 方法 | Q001 | Q002 | Q003 | Q004 | Q005 | 退步 Query |
|---|---|---|---|---|---|---|
| Embedding − BM25 | 0.0000 | 0.0000 | -0.5000 | 0.0000 | +0.5000 | Q003 |
| Hybrid − BM25 | 0.0000 | 0.0000 | -0.5000 | 0.0000 | 0.0000 | Q003 |
| Rerank − BM25 | 0.0000 | 0.0000 | -0.5000 | 0.0000 | +0.5000 | Q003 |
| R0 − BM25 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 无 |
| R1 − BM25 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 无 |
| R2 − BM25 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.2500 | 无 |
| R3 − BM25 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.5000 | 无 |

**退步只有一条，且三个方法落在同一位置：Q003 的 `recall@4` 从 1.00 掉到 0.50。**

- 原因不是候选截断（`top_k = 9` = 语料全量，所有正例都在候选内），而是排序：BM25 前 4 命中 C005+C006（1.00），Embedding / Rerank / Hybrid 的前 4 都用不相关项换掉了 C005。
- Embedding 与 Rerank 同时在 Q005 拿到 +0.50，因此**聚合层面互相抵消**（净差 0.0000）；逐 Query 层面并不持平，这正是"不能用均值掩盖单条退步"要防的情况。
- Hybrid 没有任何 +0.50 的补偿，聚合净差 −0.10 完全来自 Q003 这一条。

**逐 Query 前 4（加粗表示该条是已确认正例）：**

| Query | 正例 | BM25 | Embedding | Hybrid | Rerank |
|---|---|---|---|---|---|
| Q001 | C001 C002 C003 C004 C007 | **C001 C002 C003 C004** | **C001 C003 C004 C007** | **C001 C003 C002 C004** | **C001 C003 C002 C004** |
| Q002 | C005 C008 | **C005 C008** C002 C006 | **C005 C008** C004 C001 | **C005 C008** C002 C001 | **C005 C008** C002 C006 |
| Q003 | C005 C006 | **C006** C009 C002 **C005** | **C006** C009 C002 C004 | **C006** C009 C002 C001 | **C006** C009 C002 C008 |
| Q004 | C005 C008 | **C008 C005** C002 C006 | **C008 C005** C002 C004 | **C008 C005** C002 C006 | **C008 C005** C002 C003 |
| Q005 | C001 C003 C004 C007 | **C007** C006 C002 **C001** | **C001 C003 C007 C004** | **C007 C001** C006 C002 | **C001 C003 C004 C007** |

- Q003：只有 BM25 保留了正例 **C005**；Embedding / Rerank / Hybrid 用不相关项换掉了它，且换进的条目各不相同（C004 / C008 / C001）。M3-05 已记录重排给 C005 **0.5901（第 7）**，却给不同产品族且不相关的 C002 **0.9453（第 3）**。
- Q005：BM25 与 Hybrid 的前 4 只有 2/4 正例（C001、C007），Embedding 与 Rerank 为 4/4；R2 为 3/4，R3 为 4/4。
- R0 的前 4 与 BM25 完全相同；R1 仅在 Q005 的第 2–4 名之间换位，命中数不变，两者与 BM25 的差值全为 0.0000。

## 4 代表性退步（逐条）

**退步 1 — Q003：BM25 与其余三方法的主指标差异全部来自这里。**
Q003 是"BGA 锡球缺失 + 托盘碰伤痕迹"；C005 是塑封空洞，与 Q003 的 PROD_006 同属产品族 PF_003，用户据此确认相关。BM25 把 C005 排进前 4，Embedding / Rerank / Hybrid 都没有。按已确认的阅读优先级，这是"M3 方法在已确认的类似产品相关性上仍未排在前面"的位置，而不是标签差异。

**退步 2 — Hybrid 无补偿项，聚合退步 −0.10。**
Embedding 与 Rerank 在 Q005 的 +0.50 抵消了 Q003 的 −0.50；Hybrid 的 Q003 前 4 缺少正例 C005，Q005 前 4 仍只有 2 个正例，没有对应补偿，因此平均 Recall@4 从 0.86 降到 0.76。**这描述的是本次 RRF 融合后的前 4 排名；现有结果不足以把退步归因于某一种一般性的融合机制。**

**阅读顺序与 K=4 命中数要分开看。**
Q001 有 5 个正例，前 4 全中时单条 Recall@4 上限也只有 0.80；BM25 第 2 名的 C002 与 Embedding 第 4 名的 C007 都是正例，虽然顺序不同，前 4 命中数相同。Q005 则不同：Embedding 与 Rerank 把 C003/C004 等正例排进前 4，相对 BM25 的命中数从 2/4 提升到 4/4（Recall@4 +0.50）。二值指标只记录是否相关及名次，不解释这些排序变化的原因。

## 5 耗时与复杂度

**本次运行耗时（单次读数，含冷启动与本次缓存状态，不支持效率结论）：**

| 方法 | index_build | 逐 Query 合计 | total | 额外模型/产物 |
|---|---|---|---|---|
| BM25 | 0.0013 s | 0.0013 s | 0.0132 s | 无模型；内存倒排/词频索引 |
| Embedding | 4.0974 s | 0.1574 s | 4.2650 s | `bge-small-zh-v1.5@7999e1d…`，权重约 96 MB，CPU；索引构建含**模型加载 4.09 s**，文档编码命中向量缓存（0.0 s），Query 编码 0.105 / 0.012 / 0.012 / 0.014 / 0.014 s |
| Hybrid | 2.8447 s | 0.0621 s | 2.9184 s | 两路（BM25 + Embedding）各建索引；Embedding 路模型加载 2.84 s、缓存命中，Query 编码合计约 0.06 s |
| Rerank | 4.5034 s | 4.0155 s | 8.5297 s | 候选段 = Embedding 全量 9 条；`bge-reranker-base@2cfc18c…`，权重约 1.11 GB，**重排模型加载 4.45 s**；候选检索合计 0.1453 s，重排合计 3.8699 s |

**复杂度对照（结构，不看单次耗时）：**

| 维度 | BM25 | Embedding | Hybrid | Rerank |
|---|---|---|---|---|
| pipeline 阶段数 | 1（建索引 → 打分） | 2（编码/索引 → 打分） | 3（两路 → RRF 融合） | 2（候选检索 → cross-encoder 重排） |
| 额外模型 | 无 | 1 个 bi-encoder（约 96 MB） | 继承 1 个 bi-encoder | 1 个 bi-encoder + 1 个 cross-encoder（约 1.11 GB） |
| 是否需外部缓存 | 否 | 需向量缓存（可重建，省下文档编码） | 需向量缓存 | 需向量缓存 + 重排模型权重 |
| 离线依赖 | 仅 `rank_bm25` | `sentence-transformers` / `torch` / `transformers` | 同上 + 融合实现 | 同上 + 重排实现 |
| 需维护的配置面 | `k1` / `b` / `epsilon` | 模型、revision、device、指令前缀、归一化 | 另加 `rrf_rank_constant`、`candidates_per_route`、路由顺序 | 另加候选方法与数量、batch、`max_seq_length`、激活函数 |
| 本次观察到的排序问题 | Q005 的 C003/C004 未进入前 4 | Q003 的同产品族正例 C005 未进入前 4 | Q003 的 C005 未进入前 4，Q005 仍只有 2 个正例进入前 4 | 增加一次全量打分，但十项指标与 Embedding 候选段相同 |

- 冷启动差异主要来自模型加载：Embedding 索引构建 4.10 s 里 4.09 s 是模型加载，缓存命中使文档编码为 0.0 s；Rerank 的 8.53 s 里 4.45 s 是重排模型加载、3.87 s 是实际重排。**模型加载时间不会被向量缓存省掉。**
- 上述均为单次读数，比较效率需固定硬件、冷启动与缓存条件并重复测量；本表只用来说明成本量级与结构复杂度，不用于排名。


## 6 M3-06 变体证据与产物范围

M3-06 的四个运行与四类方法同 benchmark（第 1 节已用 `check_comparable` 确认），但它们是 **BM25 的实验变体**（`runner.EXPERIMENTAL_RETRIEVER_FACTORIES`），与生产方法分表：

| 运行 | 方法 | Query 侧改动 | recall@4 | 与 BM25 的退步 |
|---|---|---|---|---|
| R0 | `bm25_okapi` | 无（控制组） | 0.8600 | 无 |
| R1 | `bm25_filtered_query_terms` | H1 否定小句 | 0.8600 | 无 |
| R2 | `bm25_filtered_query_terms` | H2 标识/标签词 | 0.9100 | 无 |
| R3 | `bm25_filtered_query_terms` | H1 + H2 | 0.9600 | 无 |

- R1 的逐 Query Recall@4 与 R0、BM25 相同，但 Q005 的正例从第 4 名移到第 3 名，使汇总 Recall@3 从 0.67 升到 0.72、Precision@3 从 0.6000 升到 0.6667、nDCG@3 从 0.8165 升到 0.8634、nDCG@4 从 0.8871 升到 0.8926；不能称为十项指标相同。**R2、R3 相对 BM25 的 Recall@4 提升都来自 Q005**：前 4 正例从 2 个增至 3 个（R2）或 4 个（R3）。Q003 的 C005 从第 4 名升至第 3 名，改善前 3 的排序指标，但 BM25 原本已在前 4 命中它，Q003 的 Recall@4 保持 1.00。
- 这些变体只在 Query 侧过滤词项，语料、索引与指标口径与 R0 相同，因此是本 benchmark 内的单变量对照；**采纳决定见第 7 节（R3 已定为默认方案）。**

**9 份产物的范围说明：** 第 1 节列出的 9 份 = 四类方法 4 份 + R0–R3 4 份 + `dev-v3-m3-06-r0-pre-variant.json` 1 份。最后一份是变体引入前对 R0 的同配置复跑，用于回答 SD1 遗留的清点问题：

- 与 R0 相比，`schema_version`、`benchmark`、`retrieval`、`metrics`、`queries`、`summary` **完全相同**；差异只在 `generated_at`、`timing` 与 `reproducibility`。
- 但 `reproducibility.source_files` 与 `git_status_paths` 不同（两次运行之间 `runner.py` 等源码已改动），所以它**只证明"同配置、同输入的结果可复现"，不能声称是同一源码快照的逐字节复跑**；SD4 的最终配置复跑会按"可比面板一致、差异只在 `generated_at` / `timing` / 运行时 Git 状态"核对。
- 它不作为独立方法行进入第 2、3 节的排名。

## 7 最终方案与复跑核对（SD4）

### 7.1 决策依据（按 SD1 预先声明的选型规则）

规则见本包 Report 的 SD1"预先声明的选型规则"（在看汇总表之前写下）。按这些规则，读数适用如下：

1. **主指标 `recall@4`：** BM25 = Embedding = Rerank = 0.86；Hybrid = 0.76。
2. **逐 Query 不得退步：** 严格按此条，四类交付方法中 **Embedding、Rerank、Hybrid 都有 Q003 的单条退步（−0.50）**，Hybrid 同时还存在聚合退步（−0.10）；R0/R1/R2/R3 无任何单条退步。第 4 节已把这三条退步逐条解释为"排序换位"，但按规则，解释不等于没有退步。
3. **主指标差 ≤ 0.01 视为持平，再比 `precision@4` / `ndcg@4`：** BM25（0.6000 / 0.8871）与 Embedding、Rerank（0.6500 / 0.9226）满足"持平"条件，Embedding / Rerank 在次级指标上更好；Hybrid（0.5500 / 0.8500）不满足规则 2，已先出局。
4. **成本与复杂度：** BM25 阶段最少、无模型、无缓存；Embedding 增加一个约 96 MB 模型与可重建的向量缓存；Hybrid 阶段最多（两路 + 融合）且主指标最低；Rerank 增加约 1.11 GB 的 cross-encoder，**且与候选段 Embedding 的十项指标完全相同（无收益）**。
5. **泛化风险（单独记录）：** R2 / R3 的收益来自 Query 侧的标签词与否定小句过滤，规则依赖本版 Query 模板与 5 条 Query 的观测；dev-v3 源 Case 仍为 draft；Embedding / Rerank 的语义排序在 Q003 上未能把同产品族相关案例带进前 4。这些都不能由本次读数消除。
6. **表述边界：** 以上都是 Development benchmark 上的观测，不冒充 Locked Test 或生产表现；Rerank 与 Hybrid 未被采用也保留已完成的实验记录。

### 7.2 用户决定（2026-09-30）

- **默认检索方案 = BM25 + Query 过滤（H1 否定小句 + H2 标识/标签词），即 M3-06 的 R3 配置**：`recall@4 = 0.9600`，十项指标中 6 项最高、其余 4 项与最优并列，逐 Query 无退步，且不引入任何模型或缓存依赖。
- **Rerank 不采用**：与候选段 Embedding 十项指标完全相同（零收益），另需约 1.11 GB cross-encoder 与额外耗时。
- **Hybrid 不采用**：四类交付方法中唯一存在聚合退步（0.86 → 0.76）的方法。
- **BM25（原版）与 Embedding 保留为可切换对照**；四类方法与 R0–R3 的代码、结果 JSON、CLI 附件与实验报告**全部保留，不删除、不覆盖**。
- 已知边界随结论一并保留：规则依赖本版 Query 模板、样本只有 5 条 Query / 9 条语料、dev-v3 源 Case 仍为 draft；**Development 选型不冒充 Locked Test 或生产泛化**。

### 7.3 固定配置与最终正式结果

| 项目 | 值 |
|---|---|
| 调用名 | `--method bm25_drop_negation_labels` |
| 报告内方法名 | `bm25_filtered_query_terms`；`retrieval.query_filter` 记录 `drop_negation_clauses: true`、`drop_label_terms: true`、否定标记词、标签词与 ID 模式 |
| 命令（exit 0） | `uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25_drop_negation_labels --output results/dev-v3-m3-07-final.json` |
| 最终结果 | `results/dev-v3-m3-07-final.json`，SHA-256 `d5660afbb2598c62abe08aaafa1e72c46a5a56f852d22b9c50c2e2e1fd2fd5d7` |
| 终端附件 | `results/dev-v3-m3-07-final.cli.txt`，SHA-256 `4054ff80712d80811256b5e4ff9405f40dc9d1c905369b8a0306a94777995892` |
| 指标 | 与第 2 节 R3 列一致：`recall@4 0.9600`、`precision@4 0.7000`、`ndcg@4 0.9839`、`mrr@4 1.0000` |
| 耗时（单次） | index_build 0.0027 s、逐 Query 合计 0.0012 s、total 0.0156 s |

该结果与已验收的 `dev-v3-m3-06-r3.json` 在 `schema_version` / `benchmark` / `retrieval` / `metrics` / `queries` / `summary` 六个面板上完全相同（`check_comparable` 返回 `None`，逐 Query `recall@4` 差值全为 `0.0`）。另存的目的，是给 M4 与 README 一个名称明确的"最终方案"产物，而不是让实验编号充当默认配置。

### 7.4 复跑核对（2026-09-30）

同命令复跑到 `/tmp/casetrace-dev-v3-m3-07-final-recheck.json`（exit 0，SHA-256 `0f5daf2ba11b0ce6d897506335443ba71a76cf8fed9451b1969e5e7a9fd4c5d3`），与最终结果逐字段比较（复算入口：`uv run python scripts/m3_07_final_recheck.py`）：

| 比较项 | 结果 |
|---|---|
| `schema_version` / `benchmark` / `retrieval` / `metrics` / `queries` / `summary` | **全部一致** |
| `generated_at` | 不同（运行时间） |
| `timing` | 仅数值不同（`index_build_seconds`、`per_query`、`queries_total_seconds`、`total_seconds`）；`unit`、`clock`、`boundaries`、`comparison_note` 一致 |
| `reproducibility` | 仅 `git_status_paths` 不同（本包新增报告与最终产物）；`python`、`packages`、`git_head`、`source_files` 一致 |

**差异只落在运行时间、耗时与运行时 Git 文件清单上；排名、分数与指标未变。**

### 7.5 已知项

- 该默认配置目前仍登记在 `runner.EXPERIMENTAL_RETRIEVER_FACTORIES`；是否改名为生产方法属注册表整理，本包不改代码，交接时明示。
- `retrieval.method` 对 R1 / R2 / R3 都是 `bm25_filtered_query_terms`，只有 `retrieval.query_filter` 能区分三者；M4 引用时必须看 `query_filter`，不能只看方法名。
- `results/README.md` 的产物索引与复现命令已更新（SD5）；回答核心边界见 [业务与评估约定](../docs/design/behavior-contracts.md#3-grounded-answer-核心约定)。

## 8 边界与未跑项

- 规模：9 条语料、5 条 Query、二值 qrels、单一模型与单一候选数，只够支撑开发期对照，不构成生产泛化结论。
- 本文件不修改代码、`qrels`、标签与任何检索参数；不把排名差距当作标签错误。
- 耗时均为单次读数，含冷启动与本次缓存状态，不支持效率结论；模型数值容差沿用 M3-02 记录（≤3.331e-16，排名与指标一致）。
- 已完成：SD5 的 M4 交接与 `uv run casetrace demo`（默认 6 条和 dev-v3 9 条均成功；demo 仍使用原版 BM25）。未跑：Locked Test 对比（M6）。SD4 的最终配置复跑与方案固定见第 7.3–7.4 节。
- 既有历史限制不变：dev-v1 现存归档哈希与迁移记录不一致按用户决定保留；dev-v3 源 Case 仍为 draft。
- 复现命令与比较边界见 [results README](README.md#复现与比较)；本文件数字的复算入口是 `uv run python scripts/m3_07_selection_tables.py`。
