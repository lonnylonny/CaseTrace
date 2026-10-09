# dev-v3 M3-06 有限针对性实验（R0–R5）

本文件记录 M3-06 在 dev-v3 qrels revision 2 上的针对性对照：**R0–R3** 是 BM25 的四次 pipeline 运行
（控制组 + 三个单变量变体），**R4/R5** 是 Embedding / Rerank 的组件级产品族探针。
它不修改 `qrels`、标签、语料或指标口径，也**不构成选型结论**（选型属 M3-07）。

结论先说：三个变体在主指标 `recall@4` 上符合预期，R1 还改善了 Q005 的前 3 排序；**没有任何一条 Query 的指标退步**。其中 H2（标识段不参与词面计分）
还额外改善了 Q003 的 `recall@3`（包内未预先声明）。产品族探针显示：只给候选文本追加族行
**没有改变本次排名**；Query 侧也不含族名，单侧追加的效应很小。

## 1. 运行条件

| 项目 | 值 |
|---|---|
| benchmark | `data/evaluation/dev-v3/qrels.json`（`dev-qrels-v3` / `development` / 确认日 2026-09-26，45 对 `human_confirmed`，revision 2） |
| 语料与请求 | 9 条 Case；`top_k = 9`（全语料）；BM25 `k1=1.5` / `b=0.75` / `epsilon=0.25`，分词 `casetrace.retrieval.bm25.tokenize` |
| R0 命令 | `uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25 --output results/dev-v3-m3-06-r0.json` |
| R1 / R2 / R3 | 同命令，`--method` 依次为 `bm25_drop_negation` / `bm25_drop_labels` / `bm25_drop_negation_labels` |
| 变体定义 | `src/casetrace/retrieval/query_filter.py`（SHA-256 `f21f22ac…d1c47a`）；H1 = 含否定线索（`排除/不/未/无/非`）的小句整句不参与计分；H2 = 主数据 ID（`prod_*` / `cus_*` / `dev_*`）与引出 ID 的模板标签词不参与计分 |
| 变体登记 | `runner.EXPERIMENTAL_RETRIEVER_FACTORIES`，与生产 `RETRIEVER_FACTORIES` 分表；默认方法仍是 `bm25` |
| 产物 SHA-256 | R0 `e5b6d18a…f0aca9`、R1 `6dbffaca…9ea44d`、R2 `53efe536…899579`、R3 `c02610d9…b9572b`；变体引入前的重跑 `7b90a6da…d422cf` |
| 探针命令 | `uv run python scripts/m3_06_family_probe.py`（组件级，不跑 pipeline） |

三次变体运行的 `retrieval.query_filter` 如实记录在各自报告里（开关、否定标记、标签词、ID 正则）。

## 2. 复现验证（R0）

`results/dev-v3-m3-06-r0.json` 与已验收的 `results/dev-v3-bm25-m3-04-fixed.json` 逐项对比：

- **完全相同**：`benchmark`、`retrieval`、`metrics`、`queries`（排名、分数、命中词项）、`summary`；
- **差异 5 处，全部在 `reproducibility`**：git 状态列表长度、`runner.py` 哈希、`bm25.py` 哈希（本包为变体抽出 `query_tokens()` 钩子）、新增 `query_filter.py`、`rerank.py`（M3-05 之后已加入 `source_files`）。

另外，变体引入**之前**的同配置重跑 `dev-v3-m3-06-r0-pre-variant.json` 与 R0 的
`queries` / `summary` / `benchmark` **完全相同** → 新增变体代码没有改变 bm25 的任何结果。

## 3. 汇总指标（Recall-first，主 K=4）

| 运行 | 方法（过滤规则） | recall@1 | recall@3 | recall@4 | precision@4 | ndcg@4 | mrr@4 |
|---|---|---|---|---|---|---|---|
| R0 | `bm25_okapi`（控制组） | 0.3900 | 0.6700 | 0.8600 | 0.6000 | 0.8871 | 1.0000 |
| R1 | `bm25_filtered_query_terms`（H1） | 0.3900 | 0.7200 | 0.8600 | 0.6000 | 0.8926 | 1.0000 |
| R2 | 同上（H2） | 0.3900 | 0.8200 | 0.9100 | 0.6500 | 0.9347 | 1.0000 |
| R3 | 同上（H1+H2） | 0.3900 | 0.8700 | 0.9600 | 0.7000 | 0.9839 | 1.0000 |

**逐 Query 差值**（用 `casetrace.evaluation.compare.per_query_deltas`，`after − before`）：

| 对照 | Q001 | Q002 | Q003 | Q004 | Q005 |
|---|---|---|---|---|---|
| R1−R0 | 无变化 | 无变化 | 无变化 | 无变化 | `recall@3` +0.25、`precision@3` +0.3333、`ndcg@3` +0.2346、`ndcg@4` +0.0271 |
| R2−R0 | 无变化 | 无变化 | `recall@3` +0.5、`precision@3` +0.3333、`ndcg@3` +0.3066、`ndcg@4` +0.0425 | 无变化 | `recall@3` +0.25、`precision@3` +0.3333、`ndcg@3` +0.2346、`recall@4` +0.25、`precision@4` +0.25、`ndcg@4` +0.1952 |
| R3−R0 | 无变化 | 无变化 | 同 R2−R0 | 无变化 | `recall@3` +0.5、`precision@3` +0.6667、`ndcg@3` +0.5307、`recall@4` +0.5、`precision@4` +0.5、`ndcg@4` +0.4415 |
| R3−R2 | 无变化 | 无变化 | 无变化 | 无变化 | `recall@3` +0.25、`precision@3` +0.3333、`ndcg@3` +0.2961、`recall@4` +0.25、`precision@4` +0.25、`ndcg@4` +0.2463 |

**所有差值均 ≥ 0**，未出现“均值涨而单条降”的情况。

## 4. 逐 Query 前 4 与命中数

| Query | 正例 | R0 前 4 | R1 前 4 | R2 前 4 | R3 前 4 |
|---|---|---|---|---|---|
| Q001 | C001 C002 C003 C004 C007（5） | C001 C002 C003 C004（4/5） | 同 R0 | C001 C003 C004 C007（4/5） | 同 R2 |
| Q002 | C005 C008（2） | C005 C008 C002 C006（2/2） | 同 R0 | 同 R0 | 同 R0 |
| Q003 | C005 C006（2） | C006 C009 C002 C005（2/2） | 同 R0 | C006 C009 C005 C008（2/2） | 同 R2 |
| Q004 | C005 C008（2） | C008 C005 C002 C006（2/2） | 同 R0 | C008 C005 C002 C003（2/2） | 同 R2 |
| Q005 | C001 C003 C004 C007（4） | C007 C006 **C002** C001（2/4） | C007 C002 C001 C006（2/4） | C007 C006 C001 C004（3/4） | C007 C001 **C004 C003**（4/4） |

（加粗为进入前 4 的正例。Q003 的 `recall@3` 改善体现在第 3 名由不相关的 C002 换成正例 C005 —— 单条 `recall@4` 仍是 1.0，C005 原本就在第 4 名。）

## 5. 观察与假设

**5.1 H1 单独（R1）：改善前 3 的排序，前 4 命中数不变。** 去掉 Q005 的“已排除外观碰伤与运输损伤的可能”小句后，不相关的 C006 由第 2 降到第 4，正例 C001 由第 4 升到第 3，前 4 变为 `C007 C002 C001 C006`。Q005 的 `recall@3` 增加 0.25、`ndcg@4` 增加约 0.0271；`recall@4` 仍是 0.5（2/4）。包内预期的“0 收益”只对 `recall@4` 成立。

**5.2 H2 单独（R2）：Q005 提升，并额外改善 Q003。** 过滤标识段后 Q005 由 2/4 升到 3/4（正例 C004 进入第 4），符合包内预期“0.5→0.75”。**实测还多出一条包内未预先声明的改善**：Q003 的 `recall@3` 由 0.5 升到 1.0（第 3 名由不相关的 C002 换成正例 C005）。可检验的机制线索是：Q003 与候选文本都会出现同一批主数据 ID（`PROD_*` / `DEV_*`）以及“客户 / 产品 / 涉及”这类模板词，词面计分因此被抬高；过滤后计分更多依赖异常描述本身的用词。这条线索只来自 5 条 Query 的一次观测，**不外推**，也不修改标签。

**5.3 H1+H2（R3）：Q005 补齐。** Q005 前 4 变为 `C007 C001 C004 C003`（4/4），与包内预期“1.0”一致；相对 R2 只多改善 Q005 一格，说明两个因素各自解释一部分损失。

**5.4 二值指标的可见度有限。** `mrr@4` 四次全为 1.0（每条 Query 的第一名都是正例），`recall@1` 四次完全相同；R1 与 R3−R2 的收益主要落在 `ndcg@3/@4`、`recall@3` 上。二值 K=4 计数读不出“同为相关条目之间的顺序”，必须配合逐 Query 前 4 一起看。

**5.5 未出现退步。** 逐 Query 差值全部 ≥ 0；Q001 的前 4 成员变化发生在两个正例之间（C002 ↔ C007），Q004 的变化发生在两个不相关条目之间（C006 ↔ C003），命中数都没有下降。

## 6. 产品族探针（R4 / R5，组件级）

对象：`Q003 × C005`（C005 = PROD_005，与 Q003 的 PROD_006 同属 `PF_003 Microcontroller`）。改动只有一处：给 **C005 的候选文本**追加一行 `产品族：Microcontroller`；Query 文本保持原样，其余候选文本不变。

| 组件 | C005 原文本 | 追加族行后 | 差值 | C005 名次 | 前 4 |
|---|---|---|---|---|---|
| Embedding（`bge-small-zh-v1.5`，余弦） | 0.531740 | 0.535396 | **+0.003655** | 8/9 → 8/9 | 不变（C006 C009 C002 C004） |
| Rerank（`bge-reranker-base`，Sigmoid 后） | 0.590143 | 0.591785 | **+0.001642** | 7/9 → 7/9 | 不变（C006 C009 C002 C008） |

- 探针**复算出了 M3-05 记录的 C005 重排分数 0.5901 / 第 7**，说明探针与已验收结果同源。
- 分数只有约 **0.37% / 0.16%** 的微小上升，**名次与前 4 完全不变**。
- Query 文本里没有族名；本次只给一条候选追加族名的探针，不能证明排名不变的唯一原因，也不能评估双侧呈现产品族或结构化过滤的效果。这些做法超出本包边界，**留给 M3-07 及之后决定**。

## 7. 成本

| 运行 | index_build | 逐 Query 合计 | total |
|---|---|---|---|
| R0 | 0.0014 s | 0.0014 s | 0.0189 s |
| R1 | 0.0019 s | 0.0016 s | 0.0166 s |
| R2 | 0.0014 s | 0.0011 s | 0.0137 s |
| R3 | 0.0014 s | 0.0010 s | 0.0150 s |

变体不引入额外模型或索引：与 R0 共用同一份 BM25 索引，只在 Query 侧多做一次词项过滤。以上均为**单次读数**（含进程与缓存状态差异），差异在噪声范围内，**不支持效率结论**；探针的模型加载时间也不参与 pipeline 比较。

## 8. 边界与未跑项

- 规模：9 条语料、5 条 Query、二值 `qrels`、单一分词与单一 BM25 参数，只够支撑开发期对照，**不构成生产泛化结论**。
- R1–R3 与 R0 的**源码指纹不同**（本包新增变体代码）；四个运行的语料、`qrels`、指标口径与请求范围完全一致，对照的是排名与指标。
- H1 的否定标记集合与 H2 的标签词集合是针对 Query 模板的**针对性定义**（依据 M2 / M3 错误分析），不声称覆盖其他表述；`NEGATION_MARKERS` 含“未”，因此四条 Query 结尾的“原因尚未确认”小句同样被过滤，这是规则的一致结果，不是对单条 Query 的特判。
- 探针只改打分输入文本，**未跑任何 pipeline 变体**，也没有把产品族写入语料或 `qrels`。
- 未跑：Hybrid / Rerank 的 pipeline 变体、Locked Test 对比（M6）、参数网格搜索；本包不锁定最终方案。
- 选型与是否采纳任一变体属 **M3-07**；`dev-v3` 源 Case 仍为 draft，dev-v1 归档哈希失败按用户决定保留。

## 9. 复算入口

```bash
uv run pytest -q tests/retrieval/test_query_filter.py tests/evaluation/test_compare.py
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25 --output /tmp/m3-06-r0.json
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25_drop_negation_labels --output /tmp/m3-06-r3.json
uv run python scripts/m3_06_family_probe.py
```

比较边界见 [results README](README.md#复现与比较)。
