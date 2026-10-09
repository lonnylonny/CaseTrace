# Locked Test 比较协议（locked-test-v1）

状态：**已冻结（2026-10-08，SD1～SD5 完成）。**
本文件同时是预登记（方法、指标、计时规则）与最终冻结清单，不另建第二份协议。
规则来源为 [Current Plan §4](../../../docs/project/current-plan.md) 与 [M6-03 任务包](../../../docs/project/tasks/m6-03-locked-test-freeze.md)；
此处只登记本次要执行的固定内容，不重新定义相关性口径。

## 1. 预登记方法（按此顺序比较）

方法配置继承已验收的 M3 源码与既有结果文件，**不根据 Locked Test 内容搜模型或改参数**。

| 顺序 | CLI method | 登记配置 | 权威参照 |
|---|---|---|---|
| 1 | `bm25` | k1=1.5、b=0.75、epsilon=0.25，现有 tokenizer 与 document builder | `results/dev-v3-bm25-m3-04-fixed.json` |
| 2 | `embedding` | `BAAI/bge-small-zh-v1.5`，revision `7999e1d3359715c523056ef9478215996d62a620`，CPU、512 维、现有 Query instruction、归一化 `normalize_embeddings=True`、`float32`、既有截断 | `results/dev-v3-embedding-m3-04-fixed.json` |
| 3 | `hybrid` | BM25 + 同配置 Embedding，RRF 常数 60、每路候选 10、同分按 Case ID 升序 | `results/dev-v3-hybrid-m3-04-fixed.json` |
| 4 | `rerank` | 候选段 = Embedding 全量 9 条 → `BAAI/bge-reranker-base`，revision `2cfc18c9415c912f9d8155881c133215df768a70`，CPU、batch=8、既有截断/激活/同分规则 | `results/dev-v3-rerank-m3-05.json` |
| 5 | `bm25_drop_negation_labels`（R3） | 同 BM25；H1 整句过滤否定小句 + H2 过滤标识标签词与主数据 ID，规则原样登记 | `results/dev-v3-m3-07-final.json` |

**本轮执行范围（2026-10-08 用户决定）：** 只运行已选固定方案 **R3（`bm25_drop_negation_labels`）一次**，
用于确认评估链路可运行；结果好坏均接受，不追加调参、数据扩充或反复评审。
其余四方法仍在此登记以备查，**本轮不执行**。

配置常量位置（SD5 逐个核对未变）：`bm25.py`、`embedding.py`（`DEFAULT_MODEL`、`DEFAULT_REVISION`、`QUERY_INSTRUCTION`、`MODEL_OUTPUT_DTYPE`）、`hybrid.py`（`RRF_RANK_CONSTANT`、`CANDIDATES_PER_ROUTE`）、`rerank.py`（`CANDIDATE_METHOD`、`CANDIDATE_COUNT`、`RERANK_MODEL`、`RERANK_REVISION`、`RERANK_BATCH_SIZE`）、`query_filter.py`（`NEGATION_MARKERS`、`LABEL_TOKENS`、`ID_PATTERN`），均在 `src/casetrace/retrieval/` 下。

## 2. 指标与比较口径

沿用 Current Plan §4：主 K=4，另报 K=1、3 的 Recall / Precision / 二值 nDCG 与 MRR@4；
所有方法使用同一份 Corpus / Query / qrels 与同一指标版本，保存全部实际返回排名，不补分、不补名次。
无正例 Query 的排除口径与 `runner.NO_RELEVANT_POLICY` 一致。结果好坏均有效，无最低分或超越 Development 的要求；
不与旧口径 Development 数值直接计算提升，也不重新选择回答模型/提示词。

## 3. 运行规则（2026-10-08 精简）

本轮**只执行已选固定方案 R3 一次**，目的是确认评估链路（加载 → 校验 → 检索 → 计分 → 报告）可运行。
结果好坏均接受：不追加调参、不扩充数据、不反复评审，也不做计时重复或跨方法耗时比较。
每次保存独立结果文件与终端日志；**单次读数不支持效率结论**。后续若要做完整多方法对比，须另行建包。

## 4. 数据设计（先登记再生成）

**规模：9 Case / 9 Detail / 至少 18 Evidence / 5 Query / 45 个完整配对。**
每 Case 一个 Detail、至少两个真实调查项；LC003 含 die tilt + package warpage 双异常，其余单异常（约 89% / 11%，符合 GR-02）。
CaseGroup / Membership 为空；标注家族写入语料元数据，不建业务 Group。

| Case | Product | Route | 客户 | failure_mode_id | 用途 |
|---|---|---|---|---|---|
| LC001 | PROD_014 | LF_WB | CUS_002 | `00004` die tilt | 局部 die 倾斜 |
| LC002 | PROD_007 | SUBSTRATE_WB | CUS_003 | `00004` die tilt | die tilt 不同表达 |
| LC003 | PROD_008 | SUBSTRATE_WB | CUS_003 | `00004` + `00022` | 双异常（tilt + warpage） |
| LC004 | PROD_008 | SUBSTRATE_WB | CUS_003 | `00022` package warpage | 整体翘曲（塑封） |
| LC005 | PROD_007 | SUBSTRATE_WB | CUS_003 | `00022` package warpage | 整体翘曲（来料载体） |
| LC006 | PROD_012 | SUBSTRATE_FC | CUS_005 | `00030` bump open | FC 互连开路 |
| LC007 | PROD_016 | SUBSTRATE_FC | CUS_003 | `00030` bump open | FC 开路（wafer bump 高度） |
| LC008 | PROD_017 | SUBSTRATE_FC | CUS_004 | `00031` bump short | FC 互连短路 |
| LC009 | PROD_010 | SUBSTRATE_FC | CUS_004 | `00031` bump short | FC 短路（placement 偏移） |

以上是生成覆盖，**不预先规定任何标签或正例数量**；标签在 SD2 起草、SD3 由用户裁决。

**家族（`case_families`，仅作隔离记录）：** `geometry-tilt-warpage` = LC001～LC005；`fc-bump-open-short` = LC006～LC009。
两个来源族（四条来源 `00004` / `00022` / `00030` / `00031`）整族仅用于 Locked Test。家族关系不构成检索相关性。

**隔离依据：** 两份开发语料已用来源为 `00010 / 00016 / 00018 / 00026 / 00028`，与新四条来源（`00004 / 00022 / 00030 / 00031`）不重合；
新 Case 产品取 `PROD_007/008/010/012/014/016/017`，均未出现在开发 Case 或开发 Query 中；开发 Case / Query 不是新文本的改写父项。
共享冻结主数据与通用术语是允许的。这是同一合成知识底座下的家族隔离，小样本不证明真实现场泛化。

**批号与时间：** 新模拟批号沿用 `DEV_PL_` / `DEV_CL_` 格式，从 101 起编号；前缀不决定 split。
整份语料只复用 1 个生产批 `DEV_PL_102`（恰两个 Detail：LC002 / LC005，同产品 PROD_007、同投批时间 2026-06-10、同客户批 DEV_CL_102，符合 GR-04）。
其余新批不与 Development 重合。历史投批 2026-06-01～2026-07-31，发现/反馈为投批后至 2026-08-20。
模拟快照 `locked-test-v1-2026-08-31`：全部九案及完整调查在 **2026-08-31 当日结束前已结案且可用**；
五条 Query 的 `known_at=2026-09-30`。发现日期检查只是必要条件，不代替结案/完整可用性依据。

**Query：** LQ001 局部 die 倾斜、LQ002 相同异常的不同表达/跨产品背景、LQ003 封装整体翘曲、LQ004 FC 互连开路、LQ005 FC 互连短路。
每条写明当时已知客户、产品、生产批与客户批；至少两条自然包含有观测依据的否定事实；不含未来根因、改善措施或未知异常工序。
LQ003 复用历史批 `DEV_PL_102` 作已知背景，其余当前批独立（新批从 109 起）；同批背景不自动产生正例。

## 5. SD1 检索实现指纹（生成前记录）

记录时点 HEAD = `099615ef8ada0ebc736300e35ca914e296c047b0`（`M5 finished.`），工作区 dirty（含 M6-01/02 未提交产物）。

| 文件 | SHA-256（SD1） |
|---|---|
| `src/casetrace/__init__.py` | `412a3eb13b885013942b2c89ece5a3c0dd56783ddf7dce8944750ae68dd07330` |
| `src/casetrace/data/constants.py` | `6ceca4b9cd2716b6f960a2022b4bb30de82a6ab9e1de45209d4e6010d1e358fd` |
| `src/casetrace/data/dataset_model.py` | `bace7dba979338725d6bd9e1e58068e5bcc7d37eddc34e8b3fa77e80711f138e` |
| `src/casetrace/data/reference.py` | `54c0fdcba6fc231d8f86d0857f1d1374b7c1199946b1abd3be5e07322336b812` |
| `src/casetrace/data/validators.py` | `073297b5957f87b50f490b1abad007bfdc5e6acd823b524980334d01150210cb` |
| `src/casetrace/evaluation/runner.py` | `45ed57c3b54363fbbbc29d80166ebd0affff4338855de2fb416d7fc4feb343d1` |
| `src/casetrace/evaluation/benchmark.py` | `9e4e24f7e4cbdeed5dd2017c7f0d3cb74b62f65388e99c85c4afa04de590af15` |
| `src/casetrace/evaluation/metrics.py` | `47e55310fc9ebf9b4afd406295f6833b2c5cfe7db9ca3e5dbb414464e080d191` |
| `src/casetrace/demo.py` | `e4752c1bdf4d20929c1e20e496aa64fd5655094a4c6abdd90e9c3b005f6b8f1b` |
| `src/casetrace/retrieval/base.py` | `131dacc428ed7fd0c553a75b9125c1e08c08880a8cc3571fda0625cc957ba4dc` |
| `src/casetrace/retrieval/bm25.py` | `d6f1a9d556463a55ec1d8b9989efc1b417ded7aa94714603f57db50931afb3eb` |
| `src/casetrace/retrieval/embedding.py` | `18ff108f79bac07f52ead3870cb24bf3f17c1e4c3582d26e5292a86078057e48` |
| `src/casetrace/retrieval/hybrid.py` | `34bf2ccdc97e69178ac35ee906c479d0fa86ff4b1eb1774ae68e0cf0deed59a6` |
| `src/casetrace/retrieval/query_filter.py` | `f21f22ac83f012d1f564000f154a3421894bd42525f85428f03997b51cd1c47a` |
| `src/casetrace/retrieval/rerank.py` | `d686fe0f87576456ea8d2dc6287683b9095cf21ea2b3ceee8b6f29a24b74f4ac` |
| `pyproject.toml` | `f4419de973d491eacdb1a7af273a49cc014948c0fa7dd8807bf803dca18ecb49` |
| `uv.lock` | `9c0e9c19bef778f748490e43d57eb51268ea68c407d4196181a7e02007952b52` |

**预期允许的变化（SD4）：** 只扩展 `src/casetrace/evaluation/benchmark.py` 与 `runner.py`（版本→split 校验、Locked Test 快照说明）；
`data/`、`retrieval/`、`demo.py` 与检索参数必须逐字节不变。

**SD5 实际核对（2026-10-08）：** 逐文件复核后只有下表两个文件变更，`src/casetrace/__init__.py` 未改，
其余 15 个文件与上表逐字节一致（CLI 文案无需改动，版本/split 本来就打印在头部）。

| 变更文件 | SD1 | SD5 实际 |
|---|---|---|
| `src/casetrace/evaluation/benchmark.py` | `9e4e24f7…af15` | `7cf68cf61048f68d65b97bb207f8649a0919cc1420121854f3c49ee3a215142f` |
| `src/casetrace/evaluation/runner.py` | `45ed57c3…43d1` | `8f508836fd86c9a635a1ba9b9bddbef1bbdaa82bd6202e0d47431f4cc0e6de50` |

## 6. 冻结身份（2026-10-08，frozen）

冻结内容为**数据与规则**；正式成绩在其上单独运行（见 §3，本轮只跑 R3 一次）。
以下为核对通过的实际原字节身份，HEAD = `099615ef8ada0ebc736300e35ca914e296c047b0`（dirty 工作区，逐文件身份见本表与 §5）。

| 冻结项 | 路径 | SHA-256 |
|---|---|---|
| 语料（内含 Query） | `data/locked-test/corpus-v1.json` | `2fdc390ac65eb023acf7d9e77388321dd5479187dbd27ab11c1d5d58284def18` |
| qrels（正式） | `data/evaluation/locked-test-v1/qrels.json` | `d6ad943390f9b7136fac60f5dc73c0d9d7c62e8623836a32d7bc2f82c9b93540` |
| qrels 草稿（裁决前历史） | `data/evaluation/locked-test-v1/qrels.draft.json` | `f5a009ca8cb10a22e02084e2afcb6f9ff5856f6c397547fe0d096e1e6a88f01e` |
| 主数据 | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx` | `f5001bddd3dff43342a2569ceda836ddb4f5c0caca942c1c4d043d99a9131c85` |
| 生成入口 | `scripts/prepare_locked_test_v1.py` | `c870f92cf17924dc70ba74021d6fe05333d2806ef2c5e57cc1318ca799fd7c44` |
| 依赖锁定 | `uv.lock` | `9c0e9c19bef778f748490e43d57eb51268ea68c407d4196181a7e02007952b52` |
| 构建配置 | `pyproject.toml` | `f4419de973d491eacdb1a7af273a49cc014948c0fa7dd8807bf803dca18ecb49` |

- **评估源码：** `benchmark.py = 7cf68cf61048f68d65b97bb207f8649a0919cc1420121854f3c49ee3a215142f`、
  `runner.py = 8f508836fd86c9a635a1ba9b9bddbef1bbdaa82bd6202e0d47431f4cc0e6de50`；其余见 §5（未变）。
- **模型 revision：** `BAAI/bge-small-zh-v1.5` = `7999e1d3359715c523056ef9478215996d62a620`；
  `BAAI/bge-reranker-base` = `2cfc18c9415c912f9d8155881c133215df768a70`（本轮未加载，仅登记）。
- **指标版本/定义：** `evaluation-result-v2`；K=1/3/4，主 K=4，MRR@4（定义见 runner 的 `METRIC_DEFINITIONS`）。
- **方法参数：** 见 §1；预定输出目录 `results/locked-test-v1/`。
- **协议自身哈希：** 记在 [M6-03 任务包](../../../docs/project/tasks/m6-03-locked-test-freeze.md#cline-report) 的 Cline Report（避免自引用）。
- **凭据：** 未进入任何产物。

**冻结前状态：** 未冻结 → **本表核对通过后标 frozen。**

## 7. 故障与更正规则

正式运行中若故障，保存失败输入、命令、日志、修复 diff 和排名/协议影响说明后纠错重跑。
语料或标签需要更正时保留原版、重新确认并显式版本化；不能用结果反复挑选样例或静默替换文件。
