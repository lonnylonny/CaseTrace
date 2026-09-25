# CaseTrace — Current Plan

本文件是范围、里程碑、当前状态与下一交付的唯一计划入口。协作与教学规则见 [AGENTS.md](../../AGENTS.md)，交付细节见活动任务包；历史执行记录通过 Git 查阅。

**当前位置：M1、M2、M3-01、M3-02 已验收；M3-03 实施中，尚未验收。** dev-v2 是正式 Development benchmark；dev-v3 仍为待用户确认的草稿。下一步见第 6 节。

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

- 同产品、同批次、类似产品、同异常，**任一关系成立即足以 Relevant**；不要求同时成立或原因相同。“类似产品”按同 Product Family 判断，仅同 Package Route 不足以成立。
- 不新增“同异常类别”判定层，共享 failure_mode_id 不自动等于同异常。仅同异常站点也不足以单独 Relevant，须结合已知异常或背景；不得从历史记录反填当前未知工序。
- Repeat / Recurrence 指同产品且异常相同或高度相似；Incident / Context Linkage 包括同产品、同批次及有依据的生产背景联系；Technical Analog 包括类似产品或同异常。一个 Case 可有多类相关性。
- 仅有通用调查方法不自动 Relevant；已经满足任一充分条件的 Case 不能当 Hard Negative。CaseGroup、相同 Root Cause、Evidence 的 `related` 都不能自动生成 qrels。
- 阅读期望为优先完全相同异常；识别方式及额外排序规则由 M3 证据决定，不转换为未经确认的分级 qrels 或权重。Q001 的已确认阅读判断：C001 完全相同；C003、C004 相关，C003 更接近；C002 因同产品相关。C004 不因与 C001 同站点而成为完全相同异常。
- dev-v2 三条 Query 未提供批号，不以历史 Case 间同批推断 Query 同批；含批号的新 Query 的判断依据须在新标注中明确，同批次粒度的未决问题见活动任务包。

### Ground Truth、时点与隔离

- Ground Truth 单位是 Query × Historical Case；Agent 起草标签、理由和证据，**用户最终确认**。未确认或 Ambiguous 保持 draft；未标注不能当 Not Relevant，正式 evaluator 拒绝不完整或未确认输入。
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
| M3 — Retrieval Experiments | 同基准四方法比较，记录收益、退步、耗时与错误，按证据选型 | 进行中，当前 M3-03 |
| M4 — Grounded Answer | 生成约定的历史参考回答，检查关键事实、引用和信息不足；分开报告检索/回答问题 | 未开始；demo 目前仅展示字段 |
| M5 — PostgreSQL / FastAPI | 冻结模型完整存取；必要导入与 API；API/CLI 共用核心；迁移前后固定输入结果与来源一致 | 未开始，在 M4 后 |
| M6 — Docker / Demo / 收束 | Docker 与简单 Web Demo，CLI 可复现，固定方案完成 Locked Test 对比，README 含启动、数据、实验、失败案例和局限 | 未开始 |

### M3 小交付安排

七个包按以下顺序推进；执行、用户亲手代码、教学停点及验收规则统一见 [M3 工作流](../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)。未来包仅已准备，前包 accepted 后才建立实施基线并激活。

| 包 | 交付与依赖 | 状态 |
|---|---|---|
| [M3-01 多方法评估入口](tasks/m3-01-evaluation-entry.md) | 公共检索契约、方法选择、配置/版本/耗时报告；BM25 与 M2 回归一致 | accepted 2026-09-23 |
| [M3-02 Embedding](tasks/m3-02-embedding.md) | 本地 BGE small CPU/离线路径、缓存、同 dev-v2 对照；[选模决定](research/m3-02-embedding-model-selection.md) | accepted 2026-09-25 |
| [M3-03 Expand Mock Datasets](tasks/m3-03-expand-mock-datasets.md) | 扩充 Development，完整配对与用户确认、来源家族和版本说明；新版重跑 BM25 / Embedding | 实施中，停在标签确认 |
| [M3-04 Hybrid](tasks/m3-04-hybrid.md) | 已确认新版上用 RRF 融合，记录两路候选/名次/参数，与单方法比较 | 待前包验收 |
| [M3-05 Rerank](tasks/m3-05-rerank.md) | 固定候选方法与数量，真实重排模型，分开分析候选遗漏和排序错误 | 待前包验收 |
| [M3-06 有限针对性实验](tasks/m3-06-targeted-experiments.md) | 依据错误做少量单变量对照；无必要时记录不调整理由，保留用户证据检查练习 | 待前包验收 |
| [M3-07 汇总选型](tasks/m3-07-selection.md) | 四方法同版本结果、逐 Query 退步、耗时/复杂度与复现；固定 M4 所需检索方案及来源接口 | 待前包验收 |

M3-03 保留 dev-v2 原件，优先补同义表达、技术类比、背景关联、易混淆与否定表达，按 GR-10 准备事实和来源。规模、路径、全配对范围及确认进度由活动包维护。不按模型输赢挑选数据或标签，不保证扩充后能区分方法或证明泛化。M3-06 不无限调参、不要求指标必须上涨；M5/M6 只实现展示主流程所需能力。

## 6. 当前事实与下一交付

- **当前活动包：** [M3-03](tasks/m3-03-expand-mock-datasets.md)。Cline 已交付新语料、loader 版本支持与 qrels 草稿并自测，尚未经过 Codex 验收。
- **正式 / 草稿：** dev-v2 为已确认的 6 × 3；dev-v3 为 9 × 5、45 对草稿，沿用旧 18 对，新增 27 对待确认，其中 Q005–C004 待用户裁定。CLI 默认仍用 dev-v2。
- **下一步：** 用户确认新增标签及疑难配对 → 用户亲手完成 loader 缺配对回归测试 → Cline 完成版本说明、来源/家族与语义审阅记录，在同一新版正式运行 BM25 / Embedding → 回交 Codex。未确认前不发布正式 dev-v3 指标，不激活 M3-04。
- **验证证据：** 已验收部分见 [M3-02 最终验收](tasks/m3-02-embedding.md#codex-acceptance)，当前实现自测见 [M3-03 回报](tasks/m3-03-expand-mock-datasets.md#cline-report)；已有记录不代表本次文档整理重跑。
- **未解决的历史限制：** dev-v1 qrels 归档哈希与迁移记录不一致，失败测试保留；按用户决定不阻塞开发，也不刷新哈希或宣称迁移通过。完整依据见 [dev-v2 记录](../../data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)。
- **未完成的学习确认与比较限制：** 见各已完成包的简要记录及 M3-03 的 Handoff Baseline；代码验收、学习确认、用户代码与 Ground Truth 确认分别记录。
