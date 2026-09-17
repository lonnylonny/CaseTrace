# CaseTrace — Current Plan

状态：2026-09-16 用户确认的轻量重启计划。本文件是项目目标、范围、里程碑和当前进度的唯一计划入口，取代旧 Stage 1–7。
协作规则见 [AGENTS.md](../../AGENTS.md)；旧规划仅保存在 [Legacy Profile](../legacy/pre-restart-2026-09-16/README.md)，不再作为执行或验收要求。

## 1. 目标与执行顺序

CaseTrace 是一个以半导体封装历史质量 Case 为应用场景的 **Retrieval + Evaluation + Grounded Answer 系统**，兼顾 AI Engineering 学习和求职展示。
系统帮助工程师查找、比较和理解历史调查记录，不自动判断当前 Incident 的最终 Root Cause。

```text
Data Foundation v1（已完成并冻结）
    → Case Dataset / Searchable Documents / BM25
    → 人工确认 Ground Truth / CLI Evaluation / Error Analysis
    → Embedding / Hybrid / Rerank 对比实验
    → Grounded Answer
    → PostgreSQL / FastAPI
    → Docker / 简单 Web Demo / 可复现实验结果 / README
```

每次推进一个可运行、可审阅的交付。Schema、Validator、Database、Ingestion 是支持层，不能再次成为检索评估的前置工程。
Error Analysis 从第一轮评估开始，贯穿后续实验；数据扩充由实际检索缺口驱动。

## 2. 已确认的范围

| 类别 | V1 决定 |
|---|---|
| 必做检索实验 | BM25、Embedding、Hybrid、Rerank，全部在相同版本的 Corpus、Query、人工确认 qrels 和评估口径上比较 |
| 最终检索方案 | 根据实验结果选择；Rerank 必须实践和评估，但不要求最终采用；其他组件也不因完成实验而自动进入最终组合 |
| Grounded Answer | 输出相关历史 Case、相关依据、历史 Root Cause、历史检查 / Evidence 结果、来源和当前信息不足之处 |
| 必做工程交付 | PostgreSQL、FastAPI、Docker、简单 Web Demo、CLI Evaluation、可复现实验结果、README；数据库和服务集成排在检索评估与 Grounded Answer 之后 |
| LangChain | 可在 Grounded Answer / LLM Application 层按实际需要加入，不是验收项 |
| LangGraph | 仅在确有 Query Rewrite、条件判断、重试等多步骤工作流时考虑；不为使用框架重写 Retrieval Core |
| Optional | React / TypeScript、Kubernetes、复杂 CI/CD、公开部署、完整 Ingestion Platform；不计入 V1 完成门槛 |
| Defer | 复杂 Cause / Checkpoint 抽取、全面主数据导入和语义 Validator、通用批量生成平台、独立搜索服务 / 向量数据库 |
| V1 排除 | 当前 Root Cause 自动判断、autonomous investigation、GraphRAG / Knowledge Graph、fine-tuning、正式因果推断、Computer Vision、完整工厂模拟 |

PostgreSQL 是后续必做交付，延期的是实施时间，不是取消该能力。当前先用本地文件与已有检索实现推进。

## 3. Data Foundation v1 冻结

用户确认现有 Schema、dataclass、CR / GR、Validator、reference data 作为 Data Foundation v1 **完成并冻结**，没有其他数据基础工作需要作为 Retrieval Evaluation 的前置条件。

| 保留内容 | 权威位置 |
|---|---|
| 字段、实体关系、数据库映射 | [数据结构](../data/CaseTrace_Data_Structure_V2_No_Scenario.md) |
| Case 约束与生成限制 | [CR](../data/CaseTrace_Case_Constraint_Rules_Frozen.md)、[GR](../data/CaseTrace_Case_Generation_Rules_V1.md) |
| 校验实现及已知覆盖边界 | [Validator 说明](../data/CaseTrace_Validator_Implementation_Plan.md)、[代码](../../src/casetrace/data/validators.py) |
| dataclass、枚举、主数据读取 | [data 模块](../../src/casetrace/data/) |
| 固定主数据 | [reference data](../../data/reference/) |

冻结表示支持层交付已收束，不表示全部 CR / GR 已自动验证或全部语义审查已通过。已知缺口只记录，不形成自动补齐任务。
后续只修复影响运行、评估可信度、数据泄漏或来源追溯的问题；不得为领域完整性扩展基础模型或重开全面审计。
现有字段和规则继续有效；确需改变已确认业务规则时，说明具体冲突，取得用户确认并更新原权威来源。

Schema 冻结不等于 PostgreSQL 已建库。后续按既有模型实现持久化属于 M5，不重启数据设计阶段。
Query、qrels、split 与实验记录独立于历史 Case 实体维护，不为评估重新引入 Scenario 实体。

## 4. Retrieval / Ground Truth / Evaluation 约定

检索问题是：**仅根据 Current Incident 当时已知的信息，哪些已结案历史 Case 值得工程师查看？**

| 相关性类型 | 判断依据 |
|---|---|
| Repeat / Recurrence | 同产品且异常相同或高度相似，具有重复发生的调查参考价值；不要求事先知道当前最终原因 |
| Incident / Context Linkage | 已知产品、关联批号、设备、时间窗口或生产背景存在具体联系，Failure Mode 可以不同 |
| Technical Analog | 产品可以不同，但 Failure Mode 和工艺背景具有足够技术共性，可参考历史原因和调查路径 |

一个 Case 可有多类相关性。仅能提供通用调查方法、缺乏具体联系的案例不自动算 Relevant；Hard Negative 具有表面相似性但缺少足够调查关联。

- Ground Truth 单位为 Query × Historical Case。Agent 可起草 Case、Query、Relevant / Not Relevant / Ambiguous 标签、理由和依据；**正式 Ground Truth 必须由用户最终确认**。
- 未确认标签保持 draft；可以调试评估流程，但不得作为已验证 Ground Truth 或正式质量结果。第一批为现有 **6 个 Case × 3 条 Query，共 18 个配对判断**。
- CaseGroup、相同 Root Cause、Evidence 的 `related` 都不能自动转换为检索相关性标签。
- Query 只包含当时已知事实，不能加入当前 Incident 后来确认的原因；历史语料须在 Query 时点前可用。首轮可使用明确限定的历史语料快照。
- 索引只使用允许的历史记录及主数据背景；qrels、标注理由、生成审查信息和参考候选库全文不得混入检索文本。
- 采用 Recall-first，报告 Recall@K、MRR、nDCG@K，Precision@K 作为辅助约束；保存逐 Query 排名、汇总指标、配置和数据 / 模型版本。K、MRR 截断范围及边界处理在首轮评估实现时固定。
- 未标注不能当作 Not Relevant；Ambiguous、无正例 Query 单列分析并明确指标处理方式。首轮可用二值相关性计算 nDCG，无需先建立多级标签。
- 四类实验共享相同 Corpus、Query、qrels 版本与指标口径；数据或标注修改后，对比方法都应在新版本上重跑，不能跨版本宣称提升。
- Development 用于调试、选模型和错误分析；Locked Test 按案例来源 / 近重复家族隔离，不用于持续调参。划分信息不等同于业务 CaseGroup。模型与参数确定后再执行预先约定的最终对比。
- 数据扩充优先补同义表达、技术类比、背景关联和易混淆案例，不为数量或领域覆盖批量生成。第一批只能验证流程，不代表真实生产泛化效果。

Grounded Answer 只使用检索到的历史内容支持事实陈述。相关依据须能对应 Query 已知信息与历史原文；关键原因和检查结果保留 Case / Evidence 来源。
缺证据时明确不足，区分历史结论与当前未知；不生成当前最终 Root Cause。先复用已有结构化字段，复杂抽取另行延期。
Retrieval 质量与答案忠实度分开检查，不能用流畅回答代替检索指标或来源验证。

## 5. 交付里程碑与完成标准

以下 M1–M6 是交付顺序，不对应旧 Stage 编号。必做实验和工程交付均完成后，才算 V1 完成。

| 里程碑 | 交付与完成标准 | 当前状态 |
|---|---|---|
| M1 — Retrieval Baseline | 实际开发样例可运行；每个 Case 生成可检查的文档；BM25 返回稳定排名与来源；真实 demo smoke check 通过 | 已完成（2026-09-17）；真实 CLI 回归检查通过 |
| M2 — Ground Truth / Evaluation | 首批 18 个配对经用户确认；CLI 输出逐 Query 结果及 Recall / MRR / nDCG；指标有可手算样例验证；产出首轮错误分析并确定数据版本、指标与 split 约定 | 人工审阅进行中；无正式 qrels / evaluator |
| M3 — Retrieval Experiments | 完成 BM25、Embedding、Hybrid、Rerank 同基准比较；记录收益、退步、耗时和代表性错误；按结果选最终组合 | 未开始 |
| M4 — Grounded Answer | 从检索结果生成约定的历史参考回答；检查关键事实、引用和信息不足处理；分别报告检索与回答问题 | 未开始；现有 demo 仅展示字段 |
| M5 — PostgreSQL / FastAPI | 按冻结模型保存并取回完整 Case；提供必要的导入方式和 FastAPI 入口；API / CLI 共用检索与回答核心；固定输入迁移前后的结果及来源一致 | 未开始；在 M4 后实施 |
| M6 — Docker / Demo / V1 收束 | Docker 启动必要服务与简单 Web Demo；CLI Evaluation 可复现；固定方案完成 Locked Test 对比；README 说明启动、数据、实验、失败案例与局限 | 未开始 |

M3 每次增加一个方法并对比，Rerank 无收益也应保留实验结论。最终组件取舍以证据为依据，不设置未经实验支持的提升承诺。
M5 / M6 只实现展示主流程所需工程能力，不扩展成完整 Ingestion Platform 或企业基础设施。

## 6. 当前事实与下一交付

2026-09-16 重启前审计记录：

- 已有 6 个历史 Case、6 个 Detail、6 个 Evidence、3 条 Query；全部是 Development 草稿。尚无正式 Ground Truth、Locked Test、评估结果或答案生成。
- 已有 dataclass、确定性 Validator、主数据子集读取、Searchable Documents、BM25 和 CLI。Reference Excel 的 498 条记录是主数据，不是 Case Corpus。
- 软件测试为 **116 passed、169 subtests passed**；软件测试通过不证明检索质量。
- 当时默认 demo 失败：D001 的 `production_lot=DEV_CL_001`，D002 为 `DEV_PL_001`，导致 Dataset 无复用生产批号，触发 GR-04。测试使用独立人工样例，未捕获实际 demo 数据问题。此批号错误已于下述进度更新中修复。
- PostgreSQL、FastAPI、Docker、Web Demo 及四类方法的正式比较均未交付。

2026-09-17 进度更新：

- 用户已将 D001 的生产批号修正为 `DEV_PL_001`，已阅读数据转换流程并手动尝试查询；Agent 复跑三条现有 Query，真实样例均可运行。
- 用户给出的工程审阅意见：Q001 为 C001 最相关，C002 / C003 次之且同级，C004 略低；Q002 / Q003 各有一个相关异常。C002 的相关性依据是直接产品匹配：Q001 明确包含 `PROD_001`，C001 的 D001 和 C002 的 D002 都是该产品，用户认为同产品的其他异常具有调查参考价值。此判断无需经 C001 推导 C002，也不依赖当前异常与历史案例同批。当前 BM25 已将产品号纳入检索文本并返回 C002，但其排名为第四；后续实验需检验产品匹配与异常表现匹配的权衡，不能预先认定 Hybrid 必然改善。保留用户确认的工程意见，尚未形成版本化的 18 对正式 qrels，不转换为未经确认的多级分值。
- 按用户要求清理 C002 / C003 异常描述中的跨样例相对措辞；生成提示词维护在 GR-10 后，不扩展 Validator。检索文本发生变化，后续正式评估须基于清理后的版本重新运行。
- M1 验收完成：检查了 6 个 Case 的非空检索文档；`uv run casetrace demo` 正常输出排名及来源；`tests/test_demo.py` 新增真实开发样例的三条 Query CLI 回归检查，验证默认路径、重复运行一致性及 Case / Evidence 来源与原始数据一致，不将当前排名写成相关性标准。`uv run pytest -q` 实测为 **119 passed、169 subtests passed**。用户自行修改的 CLI 默认 `top_k=4` 保留；M2 的正式评估 K 值仍需固定并记录。

当前位置：**Data Foundation v1 已冻结，M1 已完成，进入 M2 Ground Truth / Evaluation**。

下一项交付限定为：**整理并确认 18 个标注 → 完成第一轮 BM25 CLI Evaluation 与 Error Analysis。**

1. 根据已确认的工程意见整理首批 Query–Case 标注、理由和依据，补齐仍待确认的判断；固定语料、Query、qrels 版本和历史可用范围，明确 Development / Locked Test 划分约定，不擅自补写正式标签。
2. 实现最小评估入口及指标验证，固定指标口径并保存排名、指标和版本；等待确认期间可用独立人工小样例验证软件计算。
3. 复核检索错误和数据 / 标注问题，再决定小幅扩充哪些开发样例，进入 M3。

后续任务完成时更新本文件的状态与下一交付。README 只保留入口和必要运行摘要；AGENTS.md 只维护协作与范围规则。不要另建竞争的路线图，也不要把旧文档中的“方案完成”当作软件已经交付。
