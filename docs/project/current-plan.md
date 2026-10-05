# CaseTrace — Current Plan

本文件是范围、里程碑、当前状态与下一交付的唯一计划入口。协作与教学规则见 [AGENTS.md](../../AGENTS.md)，交付细节见活动任务包；已验收任务包保留结论摘要，历史执行记录查 Git 或任务包注明的清理前快照。

**当前位置：M1～M4 已验收；M5-01 于 2026-10-05 简化后 accepted。** PostgreSQL 完整建表、dev-v3 原子导入和读回已通过真实数据库验收。下一交付为 M5-02 数据库接入回答核心，待准备任务包；API 尚未实现。验收证据见 [M5-01](tasks/m5-01-postgresql-roundtrip.md#codex-acceptance)。

## 1. 目标与执行顺序

CaseTrace 是半导体封装历史质量案例的 **Retrieval + Evaluation + Grounded Answer 系统**，用于 AI Engineering 学习与求职展示。系统提供历史调查参考，不判断当前 Incident 的最终 Root Cause。

```text
Data Foundation v1（已完成并冻结）
    → Case Documents / BM25
    → 用户确认 Ground Truth / CLI Evaluation / Error Analysis
    → Embedding / Hybrid / Rerank 对比
    → Grounded Answer
    → PostgreSQL / FastAPI
    → Docker / 简单 Web Demo / 可复现实验结果 / README
```

每次推进一个可运行、可审阅的交付。错误分析贯穿实验；数据扩充由实际缺口驱动，数据基础与数据库不重新成为检索评估的前置工程。

## 2. 已确认的范围

**学习展示优先（2026-10-03 用户确认）：** 本项目不是实际生产质量判定系统。以基本逻辑正确、链路可运行、主要输出完整可追溯、方便学习和展示为完成标准；不追求逐句行业语义零争议。行业隐含判断由用户负责，agent 不代替工程师裁决；不影响基本输出的措辞歧义记为已知限制，不追加机制、评审循环或反复模型重跑。优先保留用户已理解、已固定的实现；只对已复现的重要逻辑/系统错误作直接必要的最小修复，不做顺带清理、接口重写或风格重构。

**实现复杂度（2026-10-05 用户确认）：** 在基本安全和正确性足够的前提下，优先简单明了、逻辑清晰的实现。校验放在明确的职责入口并复用结果；逐字段/文档等价检查用于验收测试，不在运行链路重复叠加。只为当前需求增加模块、抽象和状态，不提前建设通用迁移、多版本管理或多层防御；已实现的偏重功能可作必要简化。

| 类别 | V1 决定 |
|---|---|
| 必做检索实验 | BM25、Embedding、Hybrid、Rerank，在同版本 Corpus、Query、用户确认 qrels 与指标口径上比较 |
| 最终方案 | 按实验结果选择；完成实验不表示必须部署该组件，Rerank 无收益也保留实验结论 |
| Grounded Answer | 相关历史 Case、相关依据、历史原因、历史检查 / Evidence 结果、来源与当前信息不足 |
| 必做工程交付 | PostgreSQL、FastAPI、Docker、简单 Web Demo、CLI Evaluation、可复现实验结果、README |
| 框架 | LangChain 可用于 LLM Application 层；仅在明确需要改写、分支、重试等工作流时考虑 LangGraph，不为框架重写 Retrieval Core |
| Optional | React / TypeScript、Kubernetes、复杂 CI/CD、公开部署、完整 Ingestion Platform |
| Defer | 复杂 Cause / Checkpoint 抽取、全面主数据导入与语义 Validator、通用生成平台、独立搜索服务 / 向量数据库 |
| 排除 | 当前 Root Cause 预测、autonomous investigation、GraphRAG / Knowledge Graph、fine-tuning、正式因果推断、Computer Vision、完整工厂模拟 |

## 3. Data Foundation v1 冻结

Schema、dataclass、CR / GR、Validator 和 reference data 已完成并冻结。冻结不代表全部语义检查已实现或通过，也不表示 PostgreSQL 已建库。

| 权威内容 | 位置 |
|---|---|
| 字段、关系与 M5 数据库映射 | [数据结构](../data/CaseTrace_Data_Structure_V2_No_Scenario.md) |
| 业务约束与生成边界 | [CR](../data/CaseTrace_Case_Constraint_Rules_Frozen.md)、[GR](../data/CaseTrace_Case_Generation_Rules_V1.md) |
| 校验覆盖与人工审阅缺口 | [Validator 说明](../data/CaseTrace_Validator_Implementation_Plan.md) |
| 主数据与生成来源 | [reference data](../../data/reference/)、[主数据决定](../data/CaseTrace_Structure_Logic_Audit_Confirmation.md) |

只修复影响运行、评估可信度、数据泄漏或来源追溯的问题。业务规则变更须由用户确认并更新其权威来源；已知覆盖缺口不自动形成待办。现行冻结模型已包含必填异常站点及同站点分组规则（CR-48～51），调查事实仍需语义审阅。

Query、qrels、split 与实验记录独立于历史 Case；不恢复 Scenario 实体，不从 CaseGroup 推导标签或数据划分。M5 按冻结模型实现持久化，不重开数据设计。

## 4. Retrieval / Ground Truth / Evaluation 约定

检索问题：**仅根据当前 Incident 当时已知的信息，哪些已结案历史 Case 值得查看？** 术语见 [CONTEXT.md](../../CONTEXT.md)。

### 相关性与阅读优先级

- **统一规则（2026-10-03 用户确认，覆盖旧背景充分条件）：** 是否 Relevant / 采用，依据当前已知异常与历史案例的调查参考价值。理由须由双侧已知现象及历史记录支持，不要求措辞逐字相同或根因相同。
- 同批次、同产品、同产品族、同客户等仅为背景补充/辅助信息，均不单独决定相关性、不强制采用或另列背景案例；背景不同也不能单独否定异常参考价值。“类似产品”仍指同 Product Family，仅同 Package Route 不等于类似产品。不新增硬编码权重或必选条件。
- **采用后再说明背景关系。** 明确标注同批次，分别写生产批和客户批的匹配字段/值，不凭一项相同推定另一项也相同；当前未给批号不从历史反填。产品、产品族、客户等已知背景关系在已采用 Case 中简明说明，不能替代异常参考理由。未采用 Case 不因这些关系相同被判漏选，也不单独摘出。
- 不新增“同异常类别”判定层，共享 failure_mode_id 不自动等于同异常。仅同异常站点也不足以单独 Relevant，须结合已知异常或背景；不得从历史记录反填当前未知工序。
- Repeat / Recurrence 指同产品且异常相同或高度相似；Incident / Context Linkage 描述产品、批次等背景联系；Technical Analog 描述异常的技术参考关系。这些名称不自动生成相关性标签。
- 仅有通用调查方法不自动 Relevant；CaseGroup、相同 Root Cause、Evidence 的 `related` 也不能自动生成 qrels。异常参考价值须按当前已知信息说明，不新增“共享代码即同异常”的捷径。
- 阅读期望为优先完全相同异常；其它排序变化须有实验依据，不转换为未经确认的分级 qrels 或权重。旧 Q001×C002 的同产品/同批次正例、Q001×C004 与 Q003×C005 的同族依据不能继续作为新规则裁决，须复核；不自动改标签。C004 不因与 C001 同站点而成为完全相同异常。
- dev-v2 三条 Query 未提供批号，不以历史 Case 间同批推断 Query 同批；同批次只作采用后的背景标注，不作为独立纳入条件。
- Query 必须写明当时已知的客户、产品、生产批号与客户批号（2026-09-25 用户决定，自 dev-v3 起执行）：取值与主数据及语料一致——客户由产品经 `customer_product_map` 推导，复用的批号须与语料中该批的产品、投批时间、客户批一致，新批号不得与既有 Case 重复；批号为模拟值，主数据无批号表。dev-v3 的五条 Query 已按此补足，见 [dev-v3 版本说明](../../data/evaluation/dev-v3/README.md)。

### Ground Truth、时点与隔离

- Ground Truth 单位是 Query × Historical Case；Agent 起草标签、理由和证据，**用户最终确认**。未确认或 Ambiguous 保持 draft；未标注不能当 Not Relevant，正式 evaluator 拒绝不完整或未确认输入。
- 2026-10-03 规则改变后，既有 qrels 与实验按旧口径保留；其 `human_confirmed` 不等于新口径确认，不自动重标。新 GT 仍由用户确认；若未来发布新口径指标，再版本化并同基准重评。该复核不作为学习展示或工程推进的前置任务，不用旧指标冒充新结论。
- [dev-v2](../../data/evaluation/dev-v2/README.md) 的 6 Case × 3 Query、18 对二值标签已于 2026-09-19 最终确认，无需再次确认。qrels 确认不改变源 Case 的 draft 审阅状态；新版本的新增或语义改变配对另行确认。
- Query 只含当时已知事实；只检索在 Query 时点前已结案且完整可用的历史内容。dev-v2 的六案完整内容被用户设定为在 2026-09-15 前可用；这是模拟快照约定，不能由 detection_time 推导，也不表示已实现通用结案/可用时间过滤。扩充数据必须记录自己的快照依据。
- 索引限于允许的历史内容与主数据背景，排除 qrels、标注理由、生成审阅信息和候选知识库全文。
- Development 用于调试、模型选择与错误分析。Locked Test 按来源 / 近重复家族隔离；已参与讨论和调参的样例不能再充当 Locked Test。固定模型与参数后执行预先约定的最终对比，不能持续用 Locked Test 调参。

### 指标与可比较性

采用 Recall-first，主 K=4，同时报告 K=1、3 的 Recall / Precision / 二值 nDCG 与 MRR@4。保留全部实际返回排名，不补分或补名次。runner 在计分前校验完整标注、排名 ID 有效且唯一。

| 口径 | 固定规则 |
|---|---|
| K | 正整数，拒绝 bool 与小数 |
| Recall@K | 前 K 命中数 / 全部正例数 |
| Precision@K | 前 K 命中数 / K；返回不足 K 不缩分母 |
| RR@4 / MRR@4 | 前四条首个相关结果名次 r 的 1/r，再跨 Query 等权平均 |
| nDCG@K | 二值 gain，以 log2(rank + 1) 折扣；IDCG 使用全部正例与 K |
| 无正例 Query | Recall / RR / nDCG 为 None 并排除对应均值；Precision 为 0 并参与均值；单列原因 |
| 有正例但未命中（含空返回） | 各指标为 0 |
| 汇总 | Query 等权，保存各指标参与数与排除原因；无参与项为 null |

二值指标不衡量 Relevant 内部的阅读顺序。四类方法必须共享 Corpus / Query / qrels 与指标版本；任一变化后在同一新版重跑，不能跨版本声称提升。保存逐 Query 排名、配置、模型/数据/源码/依赖版本及耗时；计时注明边界、硬件、冷启动与缓存条件。复现约定与产物见 [results](../../results/README.md)。

### Grounded Answer 边界

只用检索到的历史内容支持事实陈述；相关理由对应 Query 已知事实与历史原文，关键原因和检查结果保留 Case / Evidence 来源。缺证据时明确不足，区分历史结论与当前未知。先复用结构化字段；检索质量与回答忠实度分开验证。

## 5. 交付里程碑与完成标准

| 里程碑 | 完成标准 | 状态 |
|---|---|---|
| M1 — Retrieval Baseline | 真实开发样例可运行，Case 文档可检查，BM25 稳定返回排名与来源 | 已完成（2026-09-17） |
| M2 — Ground Truth / Evaluation | 用户确认标签、CLI 逐 Query 及汇总指标、手算验证、版本约定与错误分析 | [accepted（2026-09-22）](tasks/m2-completion.md) |
| M3 — Retrieval Experiments | 同基准四方法比较，记录收益、退步、耗时与错误，按证据选型 | 已完成；[M3-07 accepted（2026-09-30）](tasks/m3-07-selection.md#codex-acceptance) |
| M4 — Grounded Answer | 生成约定的历史参考回答，检查主要字段、来源及历史/当前区分 | 已完成；M4-01～M4-04 accepted（学习展示范围） |
| M5 — PostgreSQL / FastAPI | 冻结模型完整存取；必要导入与 API；API/CLI 共用核心；迁移前后固定输入结果与来源一致 | M5-01 accepted；M5-02 待规划 |
| M6 — Docker / Demo / 收束 | Docker 与简单 Web Demo，CLI 可复现，固定方案完成 Locked Test 对比，README 含启动、数据、实验、失败案例和局限 | 未开始 |

### M3 交付索引（已完成）

下表仅保留交付索引；不再执行旧排期或激活流程。实验数据和复现入口见 [results](../../results/README.md)。

| 包 | 交付与依赖 | 状态 |
|---|---|---|
| [M3-01 多方法评估入口](tasks/m3-01-evaluation-entry.md) | 公共检索契约、方法选择、配置/版本/耗时报告；BM25 与 M2 回归一致 | accepted 2026-09-23 |
| [M3-02 Embedding](tasks/m3-02-embedding.md) | 本地 BGE small CPU/离线路径、缓存、同 dev-v2 对照；[选模决定](research/m3-02-embedding-model-selection.md) | accepted 2026-09-25 |
| [M3-03 Expand Mock Datasets](tasks/m3-03-expand-mock-datasets.md) | 扩充 Development，完整配对与用户确认、来源家族和版本说明；新版重跑 BM25 / Embedding | accepted 2026-09-26 |
| [M3-04 Hybrid](tasks/m3-04-hybrid.md) | 已确认新版上用 RRF 融合，记录两路候选/名次/参数，与单方法比较 | accepted 2026-09-27 |
| [M3-05 Rerank](tasks/m3-05-rerank.md) | 固定候选方法与数量，真实重排模型，分开分析候选遗漏和排序错误 | accepted 2026-09-28 |
| [M3-06 有限针对性实验](tasks/m3-06-targeted-experiments.md) | 依据错误做少量单变量对照；无必要时记录不调整理由，保留用户证据检查练习 | accepted 2026-09-29 |
| [M3-07 汇总选型](tasks/m3-07-selection.md) | 四方法同版本结果、逐 Query 退步、耗时/复杂度与复现；固定 M4 所需检索方案及来源接口 | accepted 2026-09-30 |


### M5 交付顺序

按下列顺序逐包实施、教学与验收；仅为活动包建立实施基线，后续包在前一包验收后准备。

| 包 | 交付与完成标准 | 状态 |
|---|---|---|
| [M5-01 PostgreSQL 完整存取](tasks/m5-01-postgresql-roundtrip.md) | 冻结 Schema、主数据与 dev-v3 原子导入、完整读回、来源/顺序/快照身份保留；真实 PostgreSQL 往返与回滚验证 | accepted 2026-10-05（简化后） |
| M5-02 数据库接入回答核心 | 复用已验收 DB 加载与身份检查；CLI 可选择数据源；固定输入的文件/DB 排名、上下文、来源与响应回放一致 | 下一包，待准备 |
| M5-03 FastAPI | 输入、输出和 HTTP 错误适配；复用同一回答核心；成功、空命中和失败状态可测，给出可运行请求示例 | 待 M5-02 验收 |

## 6. 当前事实与下一交付

- **工程状态：** M1～M4 accepted；2026-10-03 Pre-M5 审计全套 **571 passed、169 subtests passed**，ruff/lock 检查通过。demo、默认评估及 R3 回归通过；五条 v10 回答离线回放通过，未新增模型调用。详细范围与证据见 [审计记录](tasks/pre-m5-audit.md)。
- **检索选型：** R3（`bm25_drop_negation_labels`，H1+H2），回答默认 top_k=4；`demo` 仍为原 BM25 / 六案，`evaluate` 默认 BM25 / dev-v2。四类方法及实验产物保留。R3 同版旧口径 Recall@4=0.96、Precision@4=0.70、nDCG@4=0.9839；这些是 Development 历史结果，不是新规则质量结论。
- **数据状态：** dev-v3 r2 为 9 Case × 5 Query、45 对旧口径 `human_confirmed`，正例 5 / 2 / 2 / 2 / 4；Case 仍为 draft。新口径待复核配对见 [M4-04](tasks/m4-04-answer-evaluation.md#新口径-ground-truth-待复核draft不改正式文件)，不是 M5 前置任务。
- **已接受限制：** v10 两处措辞限制及原审阅计数保留在 [M4 报告](../../results/dev-v3-m4-answer-evaluation.md)；不继续调模型。dev-v1 历史哈希原件缺失仍不能证明逐字节迁移，但反复测试失败已于 2026-09-29 修复，详见 [dev-v2 归档说明](../../data/evaluation/dev-v2/README.md#2026-09-29-归档校验维护)。M3-03 早期基线丢失仅限制历史差异归属，不影响当前运行。
- **存储状态：** M5-01 简化后 accepted。一份固定建表 SQL、一次主数据读取、单事务导入和统一读回内容检查；开发/测试库保留快照 `dev-v3-2026-09-15`，各 244 行业务数据。2026-10-05 全套 **640 passed、169 subtests passed**，storage **69 passed、0 skipped**，ruff/lock/diff 检查通过；未新增模型调用。[运行说明](../development/postgresql.md)。
- **下一入口：** 准备 M5-02 任务包，复用 `casetrace.storage.load_snapshot` 接入回答核心；数据库读回已完成内容摘要检查，消费方只处理已记录快照的适用性，不再逐字段重验。本轮停在 M5-01 验收，未实施 M5-02。核心接缝见 [M5 交接](handoffs/m4-04-m5-handoff.md)。

## 7. Grounded Answer 最终决定与 M5 invariants

M4-01～M4-04 已 accepted：[上下文](tasks/m4-01-evidence-context.md)、[生成](tasks/m4-02-grounded-generation.md)、[CLI](tasks/m4-03-answer-cli.md)、[回答评估](tasks/m4-04-answer-evaluation.md)。用户的代码与学习贡献保留在各包摘要；完成的两天排期不再作为当前任务。

1. **共用核心：** CLI/API 只适配输入、输出及错误；复用现有检索、上下文、生成和引用校验，不复制业务逻辑。数据库按 §3 冻结模型完整存取，保留 ID、关系、原文、来源和 review 状态；固定输入迁移前后排名、上下文及来源一致。
2. **保持原始 Query：** R3 过滤只影响检索词，生成器仍收到完整 Query（含否定、客户、产品与批号）与证据；`known_at` 用于快照检查。Query 提及产品的主数据查表只补名称/产品族/标准路线，不做 Incident 字段抽取或反填当前未知。
3. **快照与隔离：** 当前仅支持 `dev-v3-2026-09-15` 的已记录可用性快照，文件身份同时绑定语料与主数据。M5 更换存储后仍须能核对同一内容及可用性依据，不能用 detection_time 冒充结案时间。qrels/理由、生成审阅元数据和候选库全文不进入检索或模型证据；draft 状态不得自动升级，Development / Locked Test 隔离继续有效。
4. **输出与来源：** 输出相关历史案例、双侧相关依据、历史原因/检查/改善措施、来源和具体缺口。保留 Case、Detail、checkpoint 与字段原文、否定和不确定性；采用依据遵守 §4，不由背景关系强制纳入。历史结论不成为当前 Root Cause 或当前已验证措施。
5. **状态与记录：** 成功、空命中、模型失败、格式失败、引用失败分开；空命中不调用模型，失败不包装成成功。记录原始输入、排名、上下文、实际发送消息、模型/提示词/源码/数据身份及可用的响应、耗时和用量；凭据不入产物，批量复跑不覆盖旧证据。
6. **生成与质量边界：** 当前直接用 OpenAI 兼容 SDK 接 DeepSeek `deepseek-flash` 非思考 JSON Output，提示词 `grounded_answer_v10`；单次生成，无重试、路由或 Agent 工作流。引用守卫只证明可定位，语义支持另行审阅；软件回归不替代 AI 评估。模型别名不等于不可变版本，不承诺逐字复现。接受既有学习展示限制，不在存储/API 迁移中调模型或重新选型。
