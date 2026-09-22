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

2026-09-19 用户明确确认并已实施异常站点修订：Case 增加必填多选 abnormal_processes，按涉及产品路线工序并集校验；新增 same_abnormal_process 分组类型并检查全组公共交集。现行规则见结构文档及 CR-48～51，SQL 仅更新 M5 设计。本次有限修订不重开其他基础工作，调查确认事实仍需语义审阅。

## 4. Retrieval / Ground Truth / Evaluation 约定

检索问题是：**仅根据 Current Incident 当时已知的信息，哪些已结案历史 Case 值得工程师查看？**

2026-09-19 用户确认：**同产品、同批次、类似产品、同异常，任一关系本身成立就足以算 Relevant**，不要求这些关系同时成立，也不要求当前与历史原因相同。这是调查参考范围，不代表各相关 Case 具有相同的阅读优先级。

- 本轮“类似产品”以同 Product Family 为依据；仅同 Package Route 不足以成立。例如 Q001 的 PROD_001 与 C004 的 PROD_002 同属 PF_001，C005 的 PROD_005 仅与其同为 LF_WB，不能据此算类似产品。
- 本版不增加“同一异常类别”的相关性判定层，不因共享 failure_mode_id 就自动将不同异常表现判为 Relevant。C004 对 Q001 的相关性可由类似产品支持，无需新增异常类别规则。
- 同异常站点是重要判断依据，但须结合已知异常或背景，不单独构成 Relevant 充分条件。只能使用 Query 时点已知的站点，不能从历史 Case 反填当前 Incident 的未知工序。same_abnormal_process 分组不自动生成 qrels；本次加入历史站点检索文本，不增加排序权重，权重实验仍属于 M3。
- 用户表达的排序期望为：有完全相同的异常时优先返回这类记录，没有时返回 BM25 相关度高的记录。用户确认此类优先级与权重属于 **M3 排序实验**；M2 保持现有 BM25 排名，先完成基线评估，将未符合阅读期望的排序记录到错误分析。“完全相同”的识别方式及是否需要额外排序规则留到 M3 根据结果讨论，不作为 M2 前置条件，也不转换为分级 qrels 或未经确认的权重。
- 当前三条 Query 均未提供批号，本轮 18 对标注不使用同批次作为依据，也不通过历史 Case 之间同批推断它们与当前异常同批。“同批次”的具体判定粒度暂不展开。

| 相关性类型 | 判断依据 |
|---|---|
| Repeat / Recurrence | 同产品且异常相同或高度相似，具有重复发生的调查参考价值；不要求事先知道当前最终原因 |
| Incident / Context Linkage | 同产品或同批次本身足以构成调查参考，Failure Mode 可以不同；其他设备、时间窗口或生产背景联系仍需具体依据 |
| Technical Analog | 类似产品或同异常本身足以构成调查参考，不要求产品相同；类似产品的口径及不增加异常类别判定层的边界见上文 |

一个 Case 可有多类相关性。仅能提供通用调查方法、且不满足上述相关关系的案例不自动算 Relevant；Hard Negative 具有表面相似性但不满足已确认的相关性标准，不能将已经满足任一充分条件的案例当作 Hard Negative。

- Ground Truth 单位为 Query × Historical Case。Agent 可起草 Case、Query、Relevant / Not Relevant / Ambiguous 标签、理由和依据；**正式 Ground Truth 必须由用户最终确认**。
- 未确认标签保持 draft；可以调试评估流程，但不得作为已验证 Ground Truth 或正式质量结果。第一批 **6 个 Case × 3 条 Query，共 18 个配对判断** 曾经用户最终确认；[v1 原件与快照](../../data/evaluation/dev-v1/README.md) 保留历史来源和发现的存储冲突。异常站点修订后的活动标注为 [dev-qrels-v2](../../data/evaluation/dev-v2/qrels.json)，绑定新语料 SHA-256；**用户已于 2026-09-19 最终确认 dev-v2 数据版本及全部 18 对二值标签**，直接用于 Development 评估，无需重复确认。Q001–C002 已恢复为 1，其余 17 对沿用原判断；本次只同步确认元数据，不修改标签、理由或源 Case 审阅状态。旧 qrels 归档哈希存在不一致，详见 [v2 核对记录](../../data/evaluation/dev-v2/README.md)，不能将当前 v2 确认描述成旧版溯源校验已通过。
- CaseGroup、相同 Root Cause、Evidence 的 `related` 都不能自动转换为检索相关性标签。
- Query 只包含当时已知事实，不能加入当前 Incident 后来确认的原因；仅检索、返回在 Query 时点前已结案且可用的历史内容。用户已确认首轮模拟快照：现有 6 个历史 Case 的完整结案内容均在三条 Query 的 2026-09-15 时点之前可用。该设定不由检测日期推导，也不等于逐对 qrels 已确认；无需为首轮快照改动冻结 Case 模型。
- 索引只使用允许的历史记录及主数据背景；qrels、标注理由、生成审查信息和参考候选库全文不得混入检索文本。
- 采用 Recall-first，报告 Recall@K、MRR@4、nDCG@K，Precision@K 作为辅助约束；保存逐 Query 排名、汇总指标、配置和数据 / 模型版本。首轮以 **K=4 为主，同时报告 K=1、3**，保留完整排名供检查。MRR@4 仅看前四条中第一个相关结果的排名 r，逐 Query 记为 1/r，前四条无相关结果记 0，再对参与该指标的 Query 等权平均；特殊数据的处理见下一条，并在评估实现时固定。
- 已实现的 Recall / Precision 口径：K 必须是正整数（不接受 bool 或小数），只数前 K 条中的相关 Case。Recall 除以该 Query 的全部正例数，无正例返回 `None` 并排除 Recall 均值；Precision 固定除以 K，返回不足 K 条也不缩小分母，无正例返回 `0.0` 并单列分析。有正例但空返回时两者均为 `0.0`。runner 须先检查完整标注和有效、唯一的排名 ID；指标函数不将未标注当作不相关。
- RR@K 已实现为 `reciprocal_rank_at_k`：K 校验与上述函数一致，按原排名找到前 K 条中的首个相关结果后返回 `1 / rank`，返回不足 K 条时按实际排名计算。有正例但前 K 条未命中（含空返回）记 `0.0`；无正例返回 `None`，后续单列并排除 MRR 均值。M2 固定用 RR@4；跨 Query 求 MRR@4 的汇总已实现，并通过现有汇总测试。
- nDCG 已由 Cline 实现，具体接口及手算依据见 [M2-02](tasks/m2-02-ndcg.md)，已纳入 2026-09-22 总审，未发现该函数缺陷。现有汇总按 [M2 连续完成包](tasks/m2-completion.md) 固定：None 单列并排除该指标均值，Precision 的无正例 0 纳入其均值；保存各指标参与数与排除原因，没有参与项时汇总为 null。当前三条 Query 均有正例。
- 未标注不能当作 Not Relevant；Ambiguous、无正例 Query 单列分析并明确指标处理方式。首轮采用 Relevant / Not Relevant 二值计分，nDCG 使用二值相关性；暂不扩展分级相关性或将工程排序意见量化为权重。相关 Case 之间可能难以比较，既有阅读优先级意见仅保留用于错误分析；二值指标不衡量相关 Case 之间的内部排列优劣。
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
| M2 — Ground Truth / Evaluation | 首批 18 个配对经用户确认；CLI 输出逐 Query 结果及 Recall / MRR / nDCG；指标有可手算样例验证；产出首轮错误分析并确定数据版本、指标与 split 约定 | 已验收 accepted（2026-09-22）；三项审核 findings 已关闭，含 nDCG；旧归档哈希失败作为非阻塞历史限制保留 |
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

2026-09-19 M2 访谈进度：

- 已确认的相关性充分条件、类似产品口径、历史快照、二值评估范围及 K 值见第 4 节。术语释义见 [CONTEXT.md](../../CONTEXT.md)。
- 代码核对：现有 BM25 按分数排序，没有独立的“完全相同异常优先”规则；demo 对输入全部 Case 建索引，尚无通用的结案状态与历史可用时间过滤。首轮使用上述限定快照，不能把快照约定描述成已经实现通用过滤。
- 已确认优先级与权重实验归入 M3，M2 先评估现有 BM25。用户已最终确认全部 18 对二值标签及 MRR@4；正式标注已保存为 dev-qrels-v1，Q001 / Q002 / Q003 的正例数分别为 4 / 1 / 1，无未标注、Ambiguous 或无正例 Query。该批全部用于 Development，不拆出已经参与讨论的 Locked Test。
- 已记录现有语料 / Query 文件与主数据文件的 SHA-256，用于将 qrels 绑定到本次审阅的数据版本；后续 evaluator 应校验这些版本，不能在源数据改变后静默复用旧标注。尚无 CLI evaluator、正式指标结果或错误分析，M2 尚未完成。

2026-09-19 异常站点修订交付：

- 已接入 Case 异常站点、工序主数据读取、路线并集校验、同站点分组交集检查及检索/CLI 展示。6 个 Case 完成字段回填，C002 的仓储调查补充明确记录为新增模拟事实；G001 显式关联 C001、C003、C004。三条 Query 的文本和时点不变。
- 复核发现 v1 原件将 Q001–C002 存为 0，与已确认规则及上述访谈记录不一致，原件实际正例数为 3 / 1 / 1。用户确认恢复为 1；旧语料按原字节保存，qrels 原件保留不改。v2 草稿正例数为 4 / 1 / 1，变更及待审阅范围见 [迁移说明](../../data/evaluation/dev-v2/README.md)。
- `uv run pytest -q` 实测 **168 passed、169 subtests passed**，覆盖字段、路线并集、全组交集、主数据错误、检索文本边界及版本溯源；三条真实 Query 的 CLI 回归通过，`uv run casetrace demo` 实际显示工序 ID 和名称。Excel 未修改，BM25 算法与权重未修改；文档内容已改变，排名与指标须使用新版本重跑。软件检查不证明调查语义或检索质量。

2026-09-19 M2 输入核对与确认同步：

- 用户已最终确认 dev-v2 数据版本和全部 18 对标签，qrels 已同步为 `human_confirmed`；源数据及各 Case 审阅状态不变。
- 实际核对了唯一 ID、完整配对、二值标签、Development 范围及源文件 SHA-256：活动 v2 输入均符合预期，Q001 / Q002 / Q003 正例为 4 / 1 / 1。
- 旧 `dev-v1/qrels.json` 的实际哈希与 v2 的 `previous_qrels.sha256` 不符，且 Q003–C006 理由存在额外差异；迁移测试在旧哈希断言失败。保留现有文件及记录哈希，具体值见 [核对记录](../../data/evaluation/dev-v2/README.md)。此问题尚未解决，不影响先学习指标计算。
- 用户更新协作方式：**Agent 逐步实现并解释，用户理解代码、建立心智结构，再在此基础上维护和微调**。每次只推进一个可运行的小步骤，采用简洁易维护的代码，不要求用户从空白实现，也不一次展开整个评估模块。
- `recall_at_k` 已实现且用户已理解；本步新增 `precision_at_k`，沿用相同输入和集合交集计算，分母改为固定 K，口径见第 4 节。`uv run pytest -q tests/evaluation/test_metrics.py` 实测 **24 passed**，覆盖两个指标的手算及边界情况。目前没有正式评估结果，M2 尚未完成。
- 输入核对时，排除指标文件的其余测试实测为 **168 passed、169 subtests passed、1 failed**，唯一失败为上述旧 qrels 哈希断言；新增的活动 v2 确认与完整性检查通过。本步仅运行 24 个指标测试，未重跑全套测试。

2026-09-20 M2 交接：

- 用户已表示理解 Recall 和 Precision，并认可“一次实现、验证、讲解一个小步骤”的协作节奏，希望另一 Agent 延续。
- 已新增 `reciprocal_rank_at_k`，`uv run pytest -q tests/evaluation/test_metrics.py` 实测 **39 passed**。RR 代码已完成，用户尚未听取该函数的具体讲解；MRR 汇总仍未实现。本次没有重跑全套测试，旧版归档问题仍未解决。
- 交接入口现已指向 [M2-01 — 接续 RR 讲解](tasks/m2-01-rr-teaching.md)，包含当前任务的计划、基线、Cline 回报和 Codex 验收位置；本文件仍是唯一活动计划。

2026-09-20 协作工作流更新：

- 用户确认改为 **Codex 统筹、规划并输出 plan 包 → Cline 实现、自测与教学 → Codex 验收**；复杂问题和困难 debug 交回 Codex。此前日期下的协作记录保留为历史，现行规则以 [AGENTS.md](../../AGENTS.md) 为准。
- 每个小交付使用 `docs/project/tasks/<task-id>.md` 保存规格、交接基线、Cline 回报和 Codex 验收；它不替代本文件的总计划职责。本次仅更新协作文档，M2 的代码、数据、学习进度和既有验证记录不变。
- 已按新规则生成 M2-01 任务包并保存交接基线，待用户转交 Cline；本包只讲已有 RR，尚未执行或验收。旧交接文件改为入口指针，后续 nDCG 由 Codex 另建小任务包。

2026-09-20 M2-01 验收与下一包：

- Cline 已回报 RR 讲解及三指标区别的澄清；用户在 Codex 会话中明确表示“已理解推进到下一步”。Codex 对照基线确认只有任务包的 Cline Report 改变，Spec / Standards 均无影响验收的问题，M2-01 accepted。讲解依据为回报与用户反馈，未重放 Cline 会话或重跑测试。
- 已生成 [M2-02 — nDCG 实现与讲解](tasks/m2-02-ndcg.md) 并保存新基线，待 Cline 实施；本次未编写 nDCG，代码、数据和正式评估结果状态不变。

2026-09-20 M2 阶段连续交付工作流：

- 用户表示 nDCG 步骤已完成，并明确要求 M2 剩余工作全程由 Cline 承接：保持小步代码与教学，每个功能结束取得用户确认后直接继续，不再逐函数/功能回交 Codex；M2 全部交付后统一审核。规则权威位置为 AGENTS 的 M2 Stage Workflow 专节。
- 当前已有 `ndcg_at_k`，Cline 在 M2-02 报告 54 个指标测试通过和教学完成；Codex 本次仅读取实现/回报存在性，未复跑或单独验收。原基线和回报保留并纳入最终审核。
- 活动执行包改为 [M2 连续完成包](tasks/m2-completion.md)。Cline 可更新本文件中的实际实现、自测、教学和下一功能状态，明确待 Codex 总审；最终验收状态仍由 Codex 填写。当前从功能 1 开始。

2026-09-20 M2 功能 1 交付（Cline 自测，待总审）：

- 新增 `evaluation/benchmark.py` 的 `load_benchmark`（数据类 `Benchmark` / `BenchmarkQuery` / `VerifiedSource`）和 `tests/evaluation/test_benchmark.py`；`demo.py` 抽出 `load_validated_dataset` 与 `check_source_records`，使 demo 与评估共用同一条读取与校验路径，`run_demo` 行为不变。
- 校验内容：qrels 版本、`human_confirmed`、Development 范围、`sources` 两个文件按原字节的 SHA-256（失败报文件与预期／实际值，不刷新哈希、不改源文件）、Query 与 Case ID 唯一、18 对完整配对、标签为整数 0/1、理由非空，以及语料时点不晚于 Query 时点。未标注、Ambiguous、未知 ID、缺失或重复配对一律报错，不降级为不相关；标签确认与源 Case 的 draft 审阅状态分开记录。
- 实测：`uv run pytest -q tests/evaluation/test_benchmark.py` 为 **27 passed**；`uv run pytest -q` 为 **249 passed、169 subtests passed、1 failed**，唯一失败仍是旧 `dev-v1/qrels.json` 归档哈希断言；`uv run casetrace demo` 正常。正式排名、指标结果与错误分析尚未产出，M2 未完成。
- 旧归档问题本轮未解决：全盘无匹配记录哈希的原件，两种短语替换也无法复现该哈希，保留差异与失败证据，不计入功能 1 的通过项。

2026-09-21 M2 功能 2 步骤 A 交付（Cline 自测，待总审）：

- 按用户“节奏放慢”的要求，功能 2 拆为 2A（一条 Query 的数据流）、2B（跨 Query 汇总与无正例排除政策）、2C（结果保存与 CLI，即功能 3）。2A 新增 `evaluation/runner.py` 的 `build_retriever` / `rank_query` / `evaluate_query`（数据类 `RankedCase` / `QueryEvaluation`）和 `tests/evaluation/test_runner.py`，两者在阶段基线 manifest 中记为 absent，属新增；本步骤未改动任何既有文件。
- 检索口径：建一次索引，请求范围 `top_k = len(case_ids)` 覆盖整个语料，保留 BM25 实际返回的全部条目，不补分、不补名次；先校验返回 ID 属于已校验语料且无重复，再调用指标；标签与理由不进入历史文本或 Query。逐 Query 报告 `recall@k` / `precision@k` / `ndcg@k`（K=1/3/4）与 `rr@4`，无正例时沿用指标函数的 `None`。
- 实测：`uv run pytest -q tests/evaluation/test_runner.py` 为 **10 passed**；`uv run pytest -q` 为 **259 passed、169 subtests passed、1 failed**，唯一失败仍是既有 `dev-v1/qrels.json` 归档哈希断言，非本步骤引入；`uv run casetrace demo --json` 正常，默认 top_k=4 的前 4 名与运行器前 4 名一致。真实 dev-v2 观测：Q001 返回 6 条、正例 C001–C004 位于第 1、3、4、2 名，三条 Query 的 Recall@4 / nDCG@4 / RR@4 均为 1.0；这是当前语料与 BM25 参数下的观测读数，不构成检索质量结论。
- 该步骤已讲解；用户于 2026-09-21 表示基本理解，下一会话由 Cline 从 2B 继续。跨 Query 汇总、结果落盘、CLI 子命令、正式运行与错误分析尚未产出，M2 未完成。

2026-09-22 M2 功能 2 步骤 B、功能 3（2C）与功能 4（4A、4B）交付（Cline 自测，待 Codex 总审）：

- 2B 跨 Query 汇总：`evaluation/runner.py` 追加 `aggregate` 与汇总常量 / 数据类（`ExcludedQuery` / `MetricSummary` / `EvaluationSummary`）。逐 Query 分数按 Query 等权平均，RR@4 的均值命名为 `mrr@4`；无正例 Query 的 Recall / nDCG / RR 记 `None` 并从各自均值排除、原因记入 `excluded`，Precision 的 `0.0` 按指标函数口径纳入均值，没有可参与 Query 时汇总为 `None`。实测 `uv run pytest -q tests/evaluation/test_runner.py` 为 **17 passed**，全套 **266 passed、169 subtests passed、1 failed**（既有 dev-v1 归档哈希断言）。用户 2026-09-21 确认讲解。
- 2C 结果保存与 CLI：`runner.py` 增加 `run_evaluation`（校验 → 建索引 → 逐 Query 计分 → 汇总 → 可复现报告）与 `write_report`（同目录临时文件 + 原子替换，失败不留半份结果）；CLI 新增 `evaluate` 子命令（`--qrels` 默认活动 dev-v2、`--output` 必填）；README 补运行入口；新增 `tests/test_cli_evaluate.py`，`tests/evaluation/test_runner.py` 追加报告层测试。实测相关测试 **28 passed**，全套 **277 passed、169 subtests passed、1 failed**；缺失 qrels 时 exit 2 且输出目录无任何文件；两次运行除 `generated_at` 外报告完全相等。用户 2026-09-22 确认讲解。
- 4A 正式运行与结果落盘：新增 `results/dev-v2-bm25.json`（13,460 B）、`results/dev-v2-bm25.cli.txt`、`results/pytest-full.log`、`results/README.md`；README 加运行记录入口。实测 `uv run casetrace evaluate --output results/dev-v2-bm25.json` exit 0，重复运行除 `generated_at` 外完全相等，只读结构性自测 37/37 通过，`uv run casetrace demo` exit 0。未改任何产品代码。
- 4B 错误分析：新增 `results/dev-v2-bm25-error-analysis.md`。三条 Query 在 K=4 **均无漏检**；Q001 同异常分组 G001（`same_abnormal_process`，共同工序 P004）位于第 1/2/3 名、仅同产品的 C002 第 4 名，Q002 / Q003 唯一正例第 1 名，**符合已记录的阅读期望**。机制：本语料 `N=6`、`epsilon=0.25`、`average_idf=0.8373615299`，`idf = ln(N - df + 0.5) - ln(df + 0.5)` 为负时被统一压到地板 `0.20934038248156323`，因此 df≥4 的词项（`确认` / `检查` / `发现` / `剥离` / `焊线`）几乎无判别力、df=3 恰为 0，只有 df≤2 真正参与排序。据此记录三类问题：泛词误召、Query 背景句参与排序、否定语境被计为命中（C002 文本"未发现剥离"仍命中 `焊线` / `剥离`），并给出「问题 → 可能原因 → 下一步实验」表，五条全部登记为 **M3 输入**，M2 未调整权重、分词或标签。只读重算自测 174/174 通过。
- 交付读数（当前语料与参数下的观测值，非质量结论）：Q001 `C001 > C003 > C004 > C002 > C005 > C006`；Q002 `C005 > C002 > C006 > C001 > C004`；Q003 `C006 > C005 > C002 > C001 > C004`。汇总：`recall@1 0.75`、`recall@3 0.9167`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5556`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`；三条 Query 全部参与、无排除。
- 交付时复跑（2026-09-22，4C）：`uv run pytest -q` 为 **277 passed、169 subtests passed、1 failed in 2.21s**，唯一失败仍是既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言；`uv run casetrace demo` exit 0。
- 未解决 / 边界：旧 `dev-v1/qrels.json` 归档哈希差异保留为未解决项（未刷新哈希、未改旧文件）；`results/dev-v2-bm25.json` 权限为 600，记为可选后续项；工作区未提交，复现需核对 `results/README.md` 记录的源码与依赖哈希；6 条语料 / 3 条 Query / 单一参数不足以宣称泛化。M2 交付完毕，**待 Codex 总审（含尚未单独验收的 nDCG）**，不进入 M3。

2026-09-22 M2 Codex 总审：

- Verdict：**needs changes**。Spec 发现 2 项：错误分析把同异常站点当作完全相同异常，以及 BM25 归因忽略词频/长度归一化、错误排除地板词的排序贡献。Standards 发现 1 项：报告未记录已有未提交改动的数据模块与 CLI 的源码哈希。位置、复现、修订要求见 [M2 完成包的 Codex Acceptance](tasks/m2-completion.md#codex-acceptance)；上方 Cline 4B 记录中的相关结论不作为审核认可的事实。
- 独立全套实测 277 passed、169 subtests passed、1 failed；唯一失败仍为旧 dev-v1 归档哈希断言。evaluate / demo exit 0；三份辅助脚本分别 50/50、174/174、37/37，但不覆盖上述缺陷。nDCG 已对照原基线纳入总审及全套复跑，未发现该函数的验收缺陷。
- 旧归档差异保留，不刷新哈希；结果权限 600 不构成本地使用的验收阻塞。用户原有学习确认独立保留，分析纠正尚待讲解。

2026-09-22 复现记录修复与现有实现复核：

- 已确认源码清单缺口影响原计划的复现要求；补齐 5 个执行依赖的哈希路径并加 1 个回归测试，没有新增功能、依赖或仓库文件。相关测试 29 passed；全套 278 passed、169 subtests passed、1 failed（仍为旧归档哈希）。
- 正式 evaluate、demo、临时目录按 HEAD + 记录源码重建后的 CLI 均成功；排名、BM25 分数和指标未变，报告与 README 的哈希引用已同步，源码清单 finding 关闭。当前调用链复核未发现新的重大运行缺陷或本次引入的模块衔接问题。
- 用户此前更新的是 qrels 中 Q001–C004 的 rationale，标签不变，本次保留并如实记录新哈希；分析正文仍有“完全相同异常”及“只有低频词参与排序”的表述，两项 Spec findings 尚未关闭。详情与证据见 [M2 完成包](tasks/m2-completion.md#codex-acceptance)。

2026-09-22 M2 最终收尾：

- 两处分析文字已按用户澄清修正，源码清单缺口已修复验证；Spec / Standards findings 均关闭，**M2 accepted**，详见 [最终验收记录](tasks/m2-completion.md#2026-09-22-最终验收与交接)。上方阶段回报中的错误解释已被当前分析更正，不作为后续实验依据。
- 最近一次代码验证为 278 passed、169 subtests passed、1 failed；evaluate、demo、隔离重建与结果一致性验证均成功。本次只刷新文档，没有重跑或改写测试结果。
- 用户明确以当前 dev-v2 继续；旧归档哈希差异作为历史限制保留，不再作为 M2 收尾或 M3 前置。具体决定见 [dev-v2 记录](../../data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)，不能称旧版迁移校验通过。

当前位置：**M1、M2 已完成并验收。当前基线为 dev-v2、6 Cases × 3 Queries、18 对已确认二值标签、K=1/3/4 与 MRR@4；正式结果及已修正分析在 results/。M3 尚未开始。**

下一项交付限定为：**在用户新开的窗口中规划 M3 的第一个小交付，再实施检索对比实验。** 先读本计划，再按需查看 [M2 最终交接](tasks/m2-completion.md#2026-09-22-最终验收与交接)、[运行记录](../../results/README.md) 与 [错误分析](../../results/dev-v2-bm25-error-analysis.md)。BM25 / Embedding / Hybrid / Rerank 必须同基准比较；方法逐个推进，具体模型、依赖、测试和教学边界在新包确定。本轮不预先展开 M3 实现或新增基础设施。

用户学习反馈与代码验收分别记录。本文是唯一当前计划；旧的带日期回报保留历史状态，不作为当前待办。
