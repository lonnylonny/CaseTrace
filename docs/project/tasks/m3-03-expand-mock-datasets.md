# M3-03 — Expand Mock Datasets

创建：2026-09-22。状态：**当前活动包，实施中**；[M3-02](m3-02-embedding.md) 已于 2026-09-25 accepted。Cline 已完成首轮规划（SD 拆分、覆盖清单、数量与路径，用户 2026-09-25 确认 3 Case + 2 Query 与拟用路径）、SD1（事实与来源）、SD2（新语料 `data/dev/demo-v3.json`）、SD3 的 loader 版本支持，并已起草 SD4 的 45 对标签草稿（`review_status=draft_pending_human_review`，正式 evaluator 拒绝）。**当前停在用户确认 27 对新标签**；确认后执行用户亲手编写的 loader 回归测试（SD3b）与 SD5 的正式运行。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 按已观察到的检索缺口扩充一小批模拟 Case / Query，形成完整、人工确认的新 Development benchmark，并在新版本重跑 BM25 / Embedding。扩充与确认属于本包，不另设项目阶段。

**任务来源与阅读：** [Current Plan](../current-plan.md) 的 M3-03 边界、[M2 错误分析](../../../results/dev-v2-bm25-error-analysis.md)、[M3-02](m3-02-embedding.md) 实际结果；生成前读[结构定义](../../data/CaseTrace_Data_Structure_V2_No_Scenario.md)、[CR](../../data/CaseTrace_Case_Constraint_Rules_Frozen.md)、[GR](../../data/CaseTrace_Case_Generation_Rules_V1.md)。读取与校验从 [benchmark.py](../../../src/casetrace/evaluation/benchmark.py) 及现有 data / demo 路径复用。

**输入 → 输出：** dev-v2 原件、reference data、错误清单 → 独立新语料文件、Query、全配对 qrels 草稿及确认版本、来源/近重复家族记录、版本说明、新版两方法结果。

**必须实现的行为：**

- Cline 先提出一个有数量上限的小批覆盖清单，列明新增 Case / Query 数和总配对数，将人工判断量计入工作量；按具体缺口选择样例，不按某个模型必须胜出设计数据。数量与文件路径在生成前记入本包。
- 沿用冻结结构及 CR / GR，按 GR-10 先用 Python 确定事实与候选来源，再生成文本；保留必要生成依据。复用校验，另审阅未自动覆盖且影响本批可信度的语义，不扩建生成平台或 Validator。
- 新文件保留原 Case / Query 的来源；记录同义改写的父项或近重复家族。保留 dev-v2 原字节、标签与结果；新 qrels 绑定新文件哈希，新增内容不回填进旧版。
- 审阅新增历史记录在 Query 时点前结案且完整可用的快照设定；Query 只含当时已知事实。遵循既有相关性规则，不能把同产品等充分条件成立的 Case 标成 Hard Negative。
- 全部 Query × Case 配对完整，包括旧 Query × 新 Case。未改变的旧判断保留确认来源，新增/改变判断由用户最终确认；未确认或 Ambiguous 保持 draft，正式 evaluator 继续拒绝它们。
- 最小调整 loader 的版本支持，同时保留 dev-v2、来源哈希、ID 唯一、配对完整、确认状态和 Development 检查；语料版本与文件格式若需区分，明确记录，不简单移除版本守卫。
- 用户确认后发布新 benchmark，重跑 BM25 / Embedding，记录新旧差别但不跨数据版本宣称算法提升。本包数据用于 Development；来源家族信息供后续 Locked Test 隔离使用。

**用户亲手部分（预留）：** 建议用户为 loader 写一个缺失配对的回归测试：在独立临时测试数据中让“旧 Query × 新 Case”缺失，验证正式加载明确失败。Cline 提供现有 fixture / loader 接口、预期错误及必要提示，不提前写测试体；其后核对测试确实触发配对检查，而非先因错误哈希等无关原因失败。Ground Truth 审阅是另一项用户职责，不能代替亲手编码。

**测试边界与命令：** 验证新旧版本可读取、未知版本/草稿被拒绝、缺失/重复配对与来源哈希不符被拒绝；运行 `uv run pytest -q tests/evaluation/test_benchmark.py tests/evaluation/test_runner.py tests/test_cli_evaluate.py` 及本批新增数据检查。记录 CR / GR 审阅与自动校验的真实覆盖边界；运行两个方法的 `casetrace evaluate --qrels <新 qrels> ...` 并保存实际命令。本包不修复旧 dev-v1 归档失败。

**验收与教学停止点：** 新基准完整可追溯，用户确认可查，新旧输入均可校验，两个方法在同一新版本完成运行，用户测试已检查。讲清语料扩充为何增加交叉配对、为什么旧结果不能直接比较；Ground Truth 未确认时报告待确认，不能标成已完成。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

**Cline 接手首轮（只规划，不生成）：**

1. 先核对 Handoff Baseline 的 61 个快照文件、HEAD 与 tracked / untracked 状态；如有接手间变化，先在 Cline Report 逐项归因，不覆盖也不回退。
2. 在同一 Cline Report 中拆分 **1–5 个 SD**，逐项写明目标、产物、检查、教学停点及 Cline / 用户所有权；保留本包约定的用户亲手测试，不能由 Cline 预先写出测试体。
3. 提出小批覆盖清单，至少逐项映射到同义表达、技术类比、背景关联、易混淆案例、否定表达中的实际缺口，并记录来源候选、父项 / 近重复家族及为何不偏向某个检索方法。**规划上限为新增 4 个 Case、2 个 Query**；以现有 6 Case × 3 Query 计算，总规模最多 10 × 5 = 50 对，其中沿用已确认旧 18 对、最多新增 32 对人工判断。优先提出更小且能覆盖缺口的方案，不为凑满上限生成数据。
4. 同时提出拟用的独立 dataset、qrels draft、版本说明和后续结果文件路径；dev-v2 原文件与既有结果不得改写。列出总 Case / Query / 配对数以及新增人工判断数，公式须覆盖旧 Query × 新 Case、新 Query × 旧 Case、新 Query × 新 Case。
5. **首轮停在用户确认：** 只把上述计划写入 Cline Report 并向用户讲清工作量与覆盖取舍；在用户确认数量、覆盖清单和路径之前，不创建数据、不修改 loader / 测试、不运行正式 BM25 / Embedding 结果。确认后才进入 SD1 的数据事实与来源准备。

## Handoff Baseline

- 起始 HEAD：`b8aaea4151b74d4b2bf80255a5cc22b5105a7205`。M3-01、M3-02 均已 accepted 但尚未提交，不能只按 HEAD 归因本包改动。
- 实施基线目录：`/tmp/casetrace-m3-03-codex-WRKTMs`。`head.txt`、`git-status.txt`、`staged.patch`、`unstaged.patch` 记录激活时完整状态；`files/` 保存相关计划、数据、检索/评估实现、测试与结果原字节，`manifest.sha256` 可核对；`absent-targets.txt` 说明新 benchmark 的具体路径尚未选择。
- 基线中的既有改动包括：用户维护的 `AGENTS.md` / `.clinerules`；已 accepted 的 M3-01 公共评估入口；已 accepted 的 M3-02 Embedding 实现、依赖、测试、缓存规则、正式结果与分析；M3 七个任务包和 Current Plan 状态。它们均是本包起点，不归因于 M3-03，也不得为扩充数据回退。
- 已验收输入：活动 benchmark 仍为 dev-v2（6 Cases × 3 Queries、18 对用户已确认二值标签）；BM25 正式结果为 `df2c2f5d…0e06`，Embedding 正式结果为 `98aaf6e9…4ab0`；Embedding 固定 `BAAI/bge-small-zh-v1.5@7999e1d3…`、CPU、Query instruction、L2 normalize + dot/cosine 与缓存键 `d2374a3b…4497`。M3-03 必须保留 dev-v2 原字节与这些结果，不跨数据版本宣称算法提升。
- 新 benchmark 的数量与路径须先按 Codex Plan 第 17 行在本包记录后再生成，因此激活时没有预设具体目标文件名。Cline 接手先核对本基线；对随后确定的新路径及任何未被 `files/` 覆盖的新涉及文件，在编辑前追加快照并记录。

## Cline Report

状态：**实施中（SD1 已完成，待用户确认详细设计后进入 SD2）**。

- **基线核对（2026-09-25）**：HEAD `b8aaea4151b74d4b2bf80255a5cc22b5105a7205` 与 `head.txt` 一致；`git status --porcelain` 与基线 `git-status.txt` 逐行相同；`sha256sum -c manifest.sha256` 为 **61 个全部 OK、0 个不符**。接手间无变化，无需要归因的改动。
- **Cline 编辑前快照**：`/tmp/casetrace-m3-03-cline-20260925-0100/before/`（`m3-03` 包、`benchmark.py`、`src/casetrace/__init__.py`、`results/README.md`、`tests/evaluation/test_benchmark.py`、`practical-todo.md`、`current-plan.md` 共 7 个文件 + `manifest.sha256` + `head.txt`）；新目标路径（当前均不存在）记入同目录 `absent-targets.txt`；SD1 事实表为同目录 `facts/sd1-candidates.md`。
- **用户已确认（2026-09-25）**：新增 **3 Case + 2 Query**（9 Case × 5 Query = 45 对，沿用旧 18 对，新增人工判断 **27** 对）；路径 `data/dev/demo-v3.json`、`data/evaluation/dev-v3/qrels.json`、`results/dev-v3-bm25-m3-03.json`、`results/dev-v3-embedding-m3-03.json`；SD3 的 loader 缺失配对回归测试**由用户亲手编写**（Cline 只给接口、期望错误与陷阱提示，不提供测试体）。
- **本轮决定（可复核）**：CLI `evaluate --qrels` 的默认值保持 `dev-v2` 不变，新基准一律显式传 `--qrels data/evaluation/dev-v3/qrels.json`，避免改动既有入口行为；不修改既有 `G001 / memberships`；dev-v2 数据与已验收结果一律不覆盖。

| 子交付 | 目标与产物 | Cline / 用户负责的代码 | 检查与教学停止点 | 实际状态 |
|---|---|---|---|---|
| SD1 事实与来源准备 | 用 Python 从主数据确定三个新 Case 的 product / failure mode / 工序 / lot / 时间 / 数量 / 原因与措施候选 / Evidence 事实，并记录近重复家族 | 全部由 Cline 完成；只读主数据，不改仓库文件；产物 `facts/sd1-candidates.md` | 逐项对照 CR-16 / CR-49 / CR-08~10 / GR-04 / GR-06 与主数据逐字候选；讲清「同义表达」「技术类比」缺口 | **已完成**，待用户确认设计 |
| SD2 生成与校验 | 生成 `data/dev/demo-v3.json`：原 6 Case 内容逐字保留 + C007 / C008 / C009 + Q004 / Q005；复用 Validator 并记录来源哈希 | Cline 生成（GR-10 允许改写的 abnormal_description / Evidence.result / root_cause / corrective_action / disposition）；用户审阅语义与措辞 | `uv run casetrace demo --data data/dev/demo-v3.json` 可运行；`validate_relations` / `validate_generation` 无错误；语料 SHA-256 可记录 | **已完成**：17,748 B / `97685706…cc7a`；两次生成字节一致；dev-v2 原件哈希未变 |
| SD3 loader 版本支持 + 用户测试 | loader 接受新版本，同时保留 dev-v2、来源哈希、配对完整、确认状态与 Development 校验 | **Cline 已完成** `benchmark.py` 的最小改动；**用户亲手写「旧 Query × 新 Case 缺配对」回归测试**（测试体不由 Cline 提供） | 新旧版本都可读；未知版本、draft、缺配对、哈希不符、重复配对均被拒绝，且失败原因是配对检查而非无关哈希 | **Cline 部分已完成**；用户测试因需要 `human_confirmed` 的 dev-qrels-v3，安排在 SD4 确认之后执行 |
| SD4 全配对 qrels 与确认 | 起草 45 对标签与理由 → 用户逐条确认后发布 `dev-qrels-v3` | Cline 起草标签与理由；**用户最终确认（Ground Truth 不能由 Agent 确认）** | 45 对完整、无重复、二值；确认前保持 draft 且正式 evaluator 拒绝 | **草稿已完成**：13,621 B / `71d0480c…96d1`，45 对唯一、origin 18/26/1、正例 5/2/1/2/3；草稿被 loader 与 CLI 双重拒绝，临时副本改为 `human_confirmed` 后可完整加载。**待用户确认 27 对** |
| SD5 新版本重跑两方法 | 在同一新基准上运行 BM25 / Embedding，记录新旧差别但不宣称算法提升 | Cline 运行与记录；用户核对读数与结论边界 | 两条 `evaluate` 退出码 0；dev-v2 原件与 M3-01 / M3-02 结果不被覆盖 | 未开始 |

**覆盖清单与配对计算（用户已确认数量与覆盖项）**：

| 缺口（来源：M2 错误分析 4.1–4.3） | 承担样例 | 相关性依据 | 为什么不偏向某个方法 |
|---|---|---|---|
| 同义表达（词面不重合） | C007（同 00010，措辞避开 C001 的用词） | 同异常 | 词面重合低对 BM25 不利、语义相近对 Embedding 有利，两边都未保证胜出 |
| 技术类比（跨产品族 / 跨路线） | C007（PF_002 + SUBSTRATE_WB）、C008（00018 换 PF_005 + SUBSTRATE_WB） | 同异常 | 只改产品与路线，不改任何方法的算法与参数 |
| 背景关联（同批次） | Q004（含生产批 DEV_PL_009） | 同批次 + 同异常 | 批号是精确 token，BM25 本就擅长；同时检验没有产品 ID 时的泛词噪声 |
| 易混淆案例 | C009（探针压形 vs 运输碰伤）、Q005 | 表面相似但不满足任何充分条件 | 制造高词面相似的负例，考验 precision 而非只考验召回 |
| 否定表达 | C009 的 Evidence 否定句、Q005 的「已排除碰伤」 | 词袋局限，不是相关性变化 | 记录为已观察机制，不预设哪个方法一定获益 |

- 配对公式：旧 18 + 新增 27 = 45。新增 = 旧 Query × 新 Case（3 × 3 = 9）+ 新 Query × 旧 Case（2 × 6 = 12）+ 新 Query × 新 Case（2 × 3 = 6）。
- 拟新增正例（草稿，待 SD4 与用户确认）：Q001×C007、Q002×C008、Q004×C005、Q004×C008、Q005×C001、Q005×C003、Q005×C007；Q005×C004 记为需用户裁定的疑难配对。
- 未确认前不发布正式指标；新基准在用户确认标签前保持 draft。

- **完成内容：** SD1（事实与来源表）、SD2（新语料生成与校验）、SD3 的 Cline 部分（loader 版本支持）与 SD4 草稿（45 对标签与理由，`review_status` 为草稿）已完成。新增文件：`data/dev/demo-v3.json`（17,748 B，`97685706d876b36403658421a70c153591126ab75cd0f38fc4661b35a007cc7a`）。修改文件：`src/casetrace/evaluation/benchmark.py`（版本守卫）。dev-v2 语料、dev-v2 qrels、M3-01 / M3-02 正式结果均未改动。dev-v3 qrels 已起草为草稿：`data/evaluation/dev-v3/qrels.json`（13,621 B，`71d0480cc608dc31aeca421c0c6ea9de736cd9ddf8a2591520bd3c5100fe96d1`），正式评估会拒绝它；尚未运行新版本的正式 BM25 / Embedding 结果，无范围偏差。
- **关键实现：** ① 语料生成脚本 `facts/generate_demo_v3.py`（临时目录，未入库）：`json` 载入 dev-v2 语料 → 追加 C007/C008/C009、D007/D008/D009、E007/E008/E009、Q004/Q005 与 `sources` → 写入新文件；同时写入 `corpus_version` / `generation_basis` / `supersedes`（含 dev-v2 语料哈希）/ `case_families` 元数据，以及每个新 Case 的 `sources.generation_note`（来源、家族、覆盖缺口）。这些键位于五个实体列表之外，`load_demo` 与 `load_benchmark` 不读取它们，也不进入检索文本。② `benchmark.py`：`EXPECTED_QRELS_VERSION = "dev-qrels-v2"` 改为 `SUPPORTED_QRELS_VERSIONS = ("dev-qrels-v2", "dev-qrels-v3")`，版本判断改为列表成员检查（无前缀/模糊匹配），`split` 检查与其余校验完全不变；删除已无引用的旧常量，避免同一规则两处维护。③ 修正过程中的一处自测失败：新版本错误文本初稿为「期望受支持版本之一：…」，与既有断言 `qrels \| qrels_version \| 期望 ` 的尾随空格不符（定向测试 1 failed）；改为「期望 dev-qrels-v2、dev-qrels-v3 之一，实际 …」后通过，未放宽任何校验。
- **用户亲手代码与检查：** 尚未开始（SD3b）。顺序调整为 SD4 确认后再写：测试需要一个 `human_confirmed` 的 dev-qrels-v3 作为起点，否则会先因 `review_status` 失败而测不到配对检查。Cline 已提供接口 `load_benchmark(qrels_path, *, base_dir=None) -> Benchmark`、缺配对错误文本形如 `qrels | judgments | 缺少 N 个配对：(Q001, C007)`、以及 `tests/evaluation/test_benchmark.py` 的 `benchmark_inputs` fixture 与 `_dataset / _qrels / _save_qrels / _load` 帮手；测试体由用户编写。
- **测试结果（均为实际执行）：**
  - `uv run python facts/generate_demo_v3.py` → `GEN_EXIT=0`：`source unchanged=True`（dev-v2 `6923d382…89f7` 前后一致）、`target sha256=97685706…cc7a`、`cases=9 details=9 evidences=9 queries=5 sources=9`、`reused lots=['DEV_PL_001']`、`pairs=45`；连续两次生成 `deterministic=yes`。
  - `uv run python facts/check_demo_v3.py` → `relations errors=[]`、`generation errors=[]`、`source records=OK`、`latest_detection 2026-07-18 <= 2026-09-15 → True`、`pairs=45`；异常工序为 C007 P004 / C008 P007 / C009 P011。
  - `uv run casetrace demo --data data/dev/demo-v3.json` → `DEMO_EXIT=0`，输出 9 条语料与排名。
  - `uv run python facts/check_v3_gate.py` → `GATE_EXIT=0`：仅旧 18 对 → `缺少 27 个配对`（并列出 27 对）；未确认 → `review_status` 拒绝；哈希不符 → 拒绝；`split=locked_test` → 拒绝；未知版本 `v4` / `v1` → `期望 dev-qrels-v2、dev-qrels-v3 之一` 拒绝。
  - 定向测试 `uv run pytest -q tests/evaluation/test_benchmark.py tests/evaluation/test_runner.py tests/test_cli_evaluate.py` → **67 passed**，exit 0。
  - 全套 `uv run pytest -q` → **1 failed、320 passed、169 subtests passed**；唯一失败仍是既有 `data/evaluation/dev-v1/qrels.json` 归档哈希（非阻塞历史限制），与本包改动无关。
  - **观测（非质量结论，勿当正式指标）**：用草稿语料实际排名时，Q001 中 C007 居第 4（3.096，仅命中 `oqc/力检/发现/拉力/显示/检查/确认`，无任何症状词）；Q002 首位 C005、次位 C008；Q004 首位 C008（含批号 token `dev_pl_009`）、次位 C005；Q005 首位 C007、次位是负例 C006、第五位是负例 C009，而已确认正例 C003 掉到第 7。这些读数只说明缺口已被真实触发，标签尚未确认，不可作为方法优劣结论。
  - `uv run python facts/generate_qrels_v3.py` → `GEN_QRELS_EXIT=0`：`target sha256=71d0480cc608dc31aeca421c0c6ea9de736cd9ddf8a2591520bd3c5100fe96d1`、`size=13,621 B`、`judgments=45 unique=45`、`origins={'confirmed_from_v2': 18, 'new': 26, 'needs_user_ruling': 1}`、`positives={'Q001': 5, 'Q002': 2, 'Q003': 1, 'Q004': 2, 'Q005': 3}`。
  - `uv run python facts/check_qrels_v3_draft.py` → `CHECK_QRELS_EXIT=0`：草稿状态 `REJECTED -> qrels | review_status | 正式评估要求 human_confirmed`；仅在临时副本改为 `human_confirmed` 后 `ACCEPTED version=dev-qrels-v3 cases=9 queries=5 judgments=45`，正例读数与草稿一致。
  - `uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --output /tmp/m3-03-should-not-exist.json` → `EVALUATE_DRAFT_EXIT=2`，输出目录未留下文件（草稿不能进入正式评估，且不留半份结果）。
- **遗留问题：** ① Q005×C004（颈部断裂 vs 界面脱开）仍待用户裁定；② 「类似产品」口径依赖人工读 `products.product_family_id`，Validator 未实现该检查；③ 旧 dev-v1 归档哈希失败保留。均为非阻塞。
- **教学状态：** 已讲 SD1「事实由 Python 确定、文本才改写」与两类缺口；SD2 讲解待用户确认（要点：为什么语料扩充使配对数按乘法定律增加、为什么旧排名不能跨版本比较、为什么「新增 27 对」必须逐对人工判断而不能由脚本补齐）。用户反馈待记录。
- **基线核对及接手间变化：** Codex 基线（HEAD / `git-status.txt` / 61 文件 manifest）核对通过、无接手间代码变化。**环境观察（非 Cline 执行）**：会话期间工作区出现 `git add .`（index 中已暂存全部改动），并有一次 `git commit -m "m3 fin…"` 被用户 Ctrl-C 取消；Cline 未执行任何 `git add/commit/push/reset`，也未回退这些暂存。Codex 验收时请把 staged 内容与 Cline 的实际改动分开归因。
- **下一步入口：** SD4 草稿已完成，**停在用户确认 27 对新标签**（其中 1 对为 `needs_user_ruling`）。用户确认后由 Cline 把 `review_status` 改为 `human_confirmed`、填入确认日期与范围、其余字节保持不变；随后用户执行 SD3b 的 loader 回归测试，最后进入 SD5 在新基准上运行 BM25 / Embedding 正式结果。本包全部完成后回报 ready for acceptance。

## Codex Acceptance

- **Spec：** 未审阅。
- **Standards：** 未审阅。
- **独立验证证据与比较限制：** 未执行；实际完成时填写。
- **用户代码/教学记录核对：** 未审阅；不替代 Ground Truth 确认。
- **Verdict：** 待验收（accepted / needs changes / blocked）。
- **Current Plan 刷新及下一包基线：** 未执行；仅 accepted 后激活下一入口。
