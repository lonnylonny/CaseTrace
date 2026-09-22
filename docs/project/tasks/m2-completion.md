# M2 — Cline 连续构建、教学与最终回交

创建：2026-09-20。当前状态：**M2 accepted（2026-09-22）**，三项审核 findings 已关闭；旧 dev-v1 归档差异按用户决定保留为非阻塞历史限制。M3 尚未开始，下个窗口另行规划。下文带日期的 needs changes / 待审核表述保留为过程记录，最终结论见 Codex Acceptance 末尾。

## Codex Plan

**目标与工作流：** 完成 [Current Plan](../current-plan.md) 中 M2 的 BM25 自动评估与错误分析。适用 [AGENTS 的 M2 专用流程](../../../AGENTS.md) 和 [Cline 入口](../../../.clinerules/rules.md)。本包覆盖 M2 后续全部功能，替代旧包中“每个函数完成后回 Codex”的交接时机；旧包的代码、测试、回报及有效指标定义保留。

**起点：** Recall / Precision / RR 已有实现，RR 讲解已验收。nDCG 已存在，[M2-02 回报](m2-02-ndcg.md)记录 Cline 自测 `54 passed`（39 既有 + 15 新增）并交付教学；用户本次表示该步骤已完成。Codex 本次只确认文件与回报存在，未复跑或验收 nDCG，将其纳入 M2 最终审核。直接从 benchmark 输入校验开始，不重新要求 nDCG 交接确认。用户如有概念问题，先就地澄清。

### 范围、接口与约束

- 继续使用已有四个指标函数，K 和特殊值以 Current Plan 第 4 节及 M2-02 已交付接口为依据；nDCG 为二值 gain，按原排名累加位置折扣，理想分数使用全部正例与 K，无正例返回 `None`。
- 复用 [demo.py](../../../src/casetrace/demo.py) 的数据读取、允许的历史文档构建和现有确定性校验，以及 [BM25Retriever](../../../src/casetrace/retrieval/bm25.py)。保持算法、分词、权重和匹配过滤不变，不为评估引入另一套检索实现。
- 建议入口为 `evaluation/benchmark.py` 的 `load_benchmark(qrels_path: Path)`：返回已校验的历史记录、主数据、Queries、标签和来源信息；`evaluation/runner.py` 的 `run_evaluation(qrels_path: Path) -> dict`：返回可 JSON 序列化的逐 Query 结果、汇总及复现信息。内部数据结构与必要拆分由 Cline 按清晰易维护原则决定并记录。
- 在现有 CLI 增加 `evaluate` 子命令，建议 `--qrels` 默认活动 dev-v2 路径、`--output` 指定结果 JSON。核心计算与 CLI 展示/保存分开，保留现有 demo 行为；README 简要给出运行入口。
- 可编辑评估模块、相关测试、必要的 CLI 接入和 README，并维护本包及 Current Plan / practical-todo 的实际状态。不得重开冻结数据设计、改已确认标签、调整 BM25 权重或启动 M3。新增依赖只有在具体必要时才考虑，本轮预计标准库和现有依赖足够。

### 按功能连续推进

每项完成后：自测 → 用一个短例子讲清用途、输入输出、关键语法和调用关系 → 记录用户确认 → Cline 直接进入下一项。功能内部仍小步写代码和讲解；用户有疑问就留在当前概念，不一次展开全部模块。

**功能 1：读取并校验评估输入。**

- 读取 [dev-v2/qrels.json](../../../data/evaluation/dev-v2/qrels.json)，检查确认状态、`dev-qrels-v2` 版本、Development 范围、Query / Case ID 唯一、标签为整数 0/1、配对无重复且覆盖所有 Query × Case。本轮应为 3 × 6 = 18；未知 ID、未标注、Ambiguous 必须明确报错，正式流程不降级为不相关或静默跳过。
- 按文件原字节核对 `sources` 的 dataset / reference SHA-256，明确记录相对路径的解析基准；失败指出文件、预期和实际值，不自动刷新哈希。复用已确认的历史快照（6 个历史 Case 的完整结案内容在三条 Query 的 2026-09-15 时点前可用），校验本轮快照涉及的 Query、时点与语料范围并记录约定；不宣称已实现通用时间过滤。qrels 确认与源 Case draft 审阅状态分开，不因源 Case draft 自动拒绝已确认 benchmark。
- 核查已记录的[旧 qrels 归档问题](../../../data/evaluation/dev-v2/README.md)，Cline 可继续调查。若有可验证的原件可做有记录的恢复，先保留现有文件；不能证明来源时保留差异，不猜测标签或刷新哈希。旧归档问题与当前 v2 的有效来源校验分别报告，可以先继续不依赖旧原件的功能，但最终保留未解决项和失败证据，不能宣称全部检查通过。
- 验证：正常 dev-v2 可读；在临时测试输入中修改哈希、版本、split、确认状态、ID、缺失/重复/非二值标签会被拒绝。测试不修改仓库中的已确认数据。

**功能 2：BM25 排名与逐 Query / 汇总评分。**

- 建立一次历史索引，逐 Query 查询并保留全部实际返回结果。请求范围覆盖语料规模，不能只取默认 demo 的前 4 条；检索本身没有返回的 Case 不强行补分数。保存 Case ID、有序名次、原始 BM25 分数，可附已有 matched terms。
- 标注与理由只用于评估，不传入历史文本构建或检索 Query。检查返回 ID 属于已校验语料、无重复，再调用指标。独立测试文档构建边界，不能用“评估结果看起来合理”替代防泄漏检查。
- 每条 Query 报告 Recall / Precision / nDCG 的 K=1、3、4 和 RR@4；均值为 Query 等权平均，RR@4 的平均命名为 MRR@4。空结果按已有函数口径计分，少于 K 的 Precision 仍除以 K。
- 无正例 Query 单列：Recall / RR / nDCG 为 `None` 并排除各自均值，Precision 按函数口径为 0 并纳入其均值；保存各指标的参与数、排除 ID 和原因，使分母差异可见。没有可参与 Query 的指标汇总为 `null`，不能除零或写成 0。当前 dev-v2 三条 Query 都有正例；上述政策用合成输入测，不改 benchmark。
- 验证：手算的跨 Query 均值、None 排除、空排名、返回不足 K、重复/未知返回 ID，以及实际文档只含允许历史内容。先讲清一条 Query 的数据流，再解释汇总，确认后进入保存与 CLI。

**功能 3：CLI、结果保存与复现。**

- `uv run casetrace evaluate --qrels data/evaluation/dev-v2/qrels.json --output <结果路径>` 完成读取、校验、建索引、查询、计分和保存。错误信息可定位到输入或阶段，返回失败状态，不留下可误认为成功的半份报告。
- 输出包含逐 Query 完整返回排名、分数、指标、汇总和特殊样本处理；记录 qrels 版本及实际文件哈希、dataset/reference 路径与哈希、Development split、历史快照说明、指标版本/公式口径、K、实际 BM25 参数、分词/文档构建版本、软件包版本和代码/依赖复现信息。
- 工作区未提交，仅 HEAD 不足以复现：记录相关源码和 `uv.lock` 哈希或等效的可核对配置；标注脏工作区状态。运行时间、耗时可以保存，但不能把它们当成排名重复性比较的字段。
- 验证：临时输出目录中的 CLI 成功/失败与 JSON 内容，原 demo 回归；同一固定输入重复运行的排名、分数、指标一致。默认路径、输出位置和运行命令写清楚，避免与历史版本结果混淆。

**功能 4：正式运行、错误分析与最终交付。**

- 实际运行完整测试和正式 dev-v2 评估，保存结果与日志；报告通过数及所有失败，区分本轮引入的问题与既有归档冲突。保留已有测试，不为变绿移除验证。质量读数与软件测试结论分别说明。
- 写简短错误分析：每条 Query 在 K=4 漏掉了哪些已确认正例；相关案例之间是否不符合已记录的阅读期望。后一项不能称为二值标签错误或用额外权重“修好”M2。零漏检也如实记录，不凭流畅说明宣称真实生产泛化能力。
- 给出结果文件、可复现命令、配置版本、测试证据和局限。完成讲解并取得用户对本功能的确认后，在本包整理最终回报，标为待 Codex 总审；若仍有阻塞，明确标出，不假报 M2 完成。工作止于 M2。

### 测试边界、技能与最终验收

测试以公开指标函数、benchmark loader、runner 返回值和 CLI 输出为边界；使用 pytest 临时目录做输入扰动和结果保存。按功能运行最相关测试，收尾运行 `uv run pytest -q` 及实际 evaluate 命令，记录输出。现有指标测试可用 `uv run pytest -q tests/evaluation/test_metrics.py`。具体新增测试文件名由 Cline 选用并记录，测试边界已获授权，无需再向 Codex 确认。

Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[tdd](../../../.agents/skills/tdd/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，难题可用 [diagnosing-bugs](../../../.agents/skills/diagnosing-bugs/SKILL.md)。适配以 AGENTS 的 M2 专用规则为准；不自动提交、发布、建分支、调用其他 agents 或转交 Codex。

最终验收要求：固定 benchmark 的正式入口可运行、指标与汇总正确、版本和来源可核对、无泄漏、完整返回排名与结果落盘、实际测试和复现证据、简短错误分析、明确失败/局限，以及按功能的用户确认记录。Codex 最后按 Spec / Standards 审核，包括尚未单独验收的 nDCG。

## Handoff Baseline

- 起始 HEAD：`1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。
- 阶段基线：`/tmp/casetrace-m2-completion-k6qwn8y1`。`preparation/` 为本次规则与文档调整前；**Cline 以 `handoff/` 成包后状态为后续实现基线**。保存至 Codex 总审结束。
- `handoff/files/` 保存已有 src/tests Python 文件（包括 untracked 指标文件）、AGENTS / Cline 规则、计划与任务包、README、依赖文件及活动数据/主数据；`manifest.json` 记录存在状态与 SHA-256，`head.txt` / `git-status.txt` 记录 HEAD 及完整 tracked / untracked 路径，`staged.patch` / `unstaged.patch` 保存相关 tracked 改动。基线内已含 nDCG，不能把它当成本阶段后续新增。
- nDCG 最终审核仍使用 [M2-02](m2-02-ndcg.md) 的原始基线 `/tmp/casetrace-m2-ndcg-px71dp48/handoff`，再叠加本阶段增量；该包回报保留，不能因新基线覆盖而免审。RR 的已验收记录也保留。
- 本包与建议的 benchmark / runner 模块及对应新测试在整理前不存在，缺失目标已列入 manifest。新涉及的已有文件在修改前由 Cline 补快照到 `handoff/additional/` 并记入 Report；不存在的目标记录 absent。不可覆盖阶段初始快照。
- 每个功能开始检查相关基线与上一步变化，记录外部介入修改和自己的增量。快照丢失时如实记录限制，保存当前内容为新的续作基线，可继续无争议工作；不得把新快照冒充旧起点，影响来源或验收的缺口向用户说明，最终交 Codex 审核。
- Cline 追加快照（功能 1）：`handoff/additional/demo.py.pre-m2-feature1`，SHA-256 `c442970b7b715bb40ad3f82d782efd635888b87a254555cf3dce3d69c10b3cfe`，与基线 `handoff/files/src/casetrace/demo.py` 逐字节相同（已核对）。`src/casetrace/evaluation/benchmark.py`、`tests/evaluation/test_benchmark.py` 在基线 manifest 中为 absent，属本次新增；未改动其他既有文件。功能 1 开始时工作区无外部介入改动。
- Cline 追加快照（功能 2 步骤 B）：`handoff/additional/runner.py.pre-m2-feature2b`，SHA-256 `9ed8d04fd3a2f39ce6ec749c63eb945a269aa27ab7c6f4eb757d37531b8bfcc8`；`handoff/additional/test_runner.py.pre-m2-feature2b`，SHA-256 `6948d7a53b031094dfe930b3fd2cec78b97bfc2fe82fcdde404be60ba1f0de58`，与 2A 回报记录的哈希及阶段基线 manifest 的 absent 记录一致，说明 2B 开始时工作区无外部介入改动。这两个文件属 2A 新增，快照只能从当前内容建立，不能当作阶段起点。2B 未改动其他既有文件。
- Cline 追加快照（功能 3 / 2C）：`handoff/additional/runner.py.pre-m2-feature2c`（SHA-256 `095627e2f0ce…`）、`handoff/additional/test_runner.py.pre-m2-feature2c`（`9674f7e2b749…`）、`handoff/additional/__init__.py.pre-m2-feature2c`（`552dead8e8f2…`）、`handoff/additional/README.md.pre-m2-feature2c`（`2a4a747fe95b…`）。前两个与 2B 结束状态逐字节一致，说明 2C 开始时工作区无外部介入改动；后两个是阶段基线中已存在的既有文件，本步骤首次改动，快照取自改动前。`tests/test_cli_evaluate.py` 在基线 manifest 中为 absent，属本次新增。
- Cline 追加快照（功能 4 步骤 A / 4A）：`handoff/additional/README.md.pre-m2-feature4a`（SHA-256 `ccb649f5097c7df284cf0a6dd5867bba59e3f61597e1aeebf77c505cad7ed885`）、`handoff/additional/m2-completion.md.pre-m2-feature4a`（`fb6dc3e5b0d9411dc3c04b3fd0f98068b7efac8bfa47f046152133ccd7169f17`）、`handoff/additional/current-plan.md.pre-m2-feature4a`（`99450cdcba7d7e647401c99f4cb735ff555f3ed6ffe5988b2566f33717829bb2`）、`handoff/additional/practical-todo.md.pre-m2-feature4a`（`b59495f1941f17264ab753cb48bd9bc50e5c52f2bdc8c14c2b8ccbb1a9140da3`）。四个哈希与本步骤开始前的工作区实测值逐一相同，说明 4A 开始时无外部介入改动；四个文件都是阶段基线中已存在的既有文件，快照取自改动前。阶段基线 manifest（46 条）中没有 `results/` 的任何条目，因为整理时该目录不存在，属本步骤新增；同类缺失目标在 manifest 里的记录形式是 `{"exists": false}`（例如 `src/casetrace/evaluation/runner.py`、`tests/evaluation/test_runner.py`）。既有阶段基线与 nDCG 原基线均仍在原路径，未被覆盖。
- Cline 追加快照（功能 4 步骤 B / 4B）：`handoff/additional/results-README.md.pre-m2-feature4b`（SHA-256 `1361133f54fadb05c1a70aa9c6a68a176ffb408e9c258cfc1bf2e124161e7ad3`）、`handoff/additional/m2-completion.md.pre-m2-feature4b`（`dcb488ed53733be964f2c8348871c04a997da035908a59e9781c2928611e9993`）。前者与 4A 记录的 `results/README.md` 哈希逐一相同、后者与 4A 结束时本包内容相符，说明 4B 开始时工作区无外部介入改动。`results/dev-v2-bm25-error-analysis.md` 属本步骤新增（阶段基线 manifest 中没有 `results` 条目）；`results/dev-v2-bm25.json` 保持 `25aca703de92…` 不变，说明分析未触碰结果文件。
- Cline 追加快照（功能 4 步骤 C / 4C）：`handoff/additional/current-plan.md.pre-m2-feature4c`（SHA-256 `99450cdcba7d7e647401c99f4cb735ff555f3ed6ffe5988b2566f33717829bb2`，与 4A 快照相同）、`handoff/additional/practical-todo.md.pre-m2-feature4c`（`b59495f1941f17264ab753cb48bd9bc50e5c52f2bdc8c14c2b8ccbb1a9140da3`，与 4A 快照相同）、`handoff/additional/README.md.pre-m2-feature4c`（`6dc41106c871d54fbc484978e20d0e2847061551ebe15d5b87d9b5a0ee3fea0f`，与 4A 结束状态相同）、`handoff/additional/m2-completion.md.pre-m2-feature4c`（`6d19ad951bf145eb4dabc253a2e032fbbad8cef0e180ea015f8d74f34b2ae8ee`，与 4B 结束时本包相符）。四个快照说明 4C 开始时工作区无外部介入改动；`results/` 五个文件本步骤未改动。
- 此前 Cline 报告 54 个指标测试通过；Codex 本次未重跑或验收。既有旧 qrels 哈希失败按核对记录处理，不归因于后续新增功能。

## Cline Report

状态：功能 2 已按慢节奏拆为 2A（一条 Query 数据流）、2B（跨 Query 汇总）、2C（结果保存与 CLI，即任务包功能 3）。2A 已实现、自测并讲解，用户已于 2026-09-21 确认理解；2B 已实现、自测并讲解，用户已于 2026-09-21 确认理解；2C 已实现、自测并讲解，用户已于 2026-09-22 确认；功能 4 同样按慢节奏拆为 4A（正式运行与结果落盘）、4B（错误分析）、4C（最终回交），三者均已实现、自测并讲解，用户已于 2026-09-22 确认。**M2 全部交付完毕，标 `ready for final Codex review`，尚未验收。** 按下表持续追加，每个功能一行或一段，不另建任务层级。

| 功能 | 改动与基线增量 | 命令、观察结果、未跑检查 | 已教/待教与用户确认 | 剩余问题与下一步 |
|---|---|---|---|---|
| nDCG（承接） | 见 M2-02 原回报 | Cline 报告 54 passed，待最终总审 | 原包已讲解；用户本次表示该步骤已完成 | 从功能 1 开始 |
| 1 输入校验 | 新增 `src/casetrace/evaluation/benchmark.py`（`load_benchmark`、`Benchmark` / `BenchmarkQuery` / `VerifiedSource`）与 `tests/evaluation/test_benchmark.py`；`src/casetrace/demo.py` 抽出 `load_validated_dataset` / `check_source_records`，让 demo 与评估共用同一条读取与校验路径；基线中的这两个模块记为 absent，`demo.py` 改动前快照见 Handoff Baseline | `uv run pytest -q tests/evaluation/test_benchmark.py` → **27 passed**；`uv run pytest -q` → **249 passed、169 subtests passed、1 failed**（唯一失败为既有 `dev-v1/qrels.json` 归档哈希断言）；`uv run casetrace demo` 复跑正常输出。真实 dev-v2 读取实测：`dev-qrels-v2` / `development` / 确认日 2026-09-19、语料 `C001–C006`、正例 4/1/1、语料最晚发现日 2026-06-15 ≤ Query 时点 2026-09-15。未跑：功能 2 及之后的检索与评分 | 已讲：这份输入为何要先校验、`Benchmark` 字段含义、相对路径基准 `base_dir`、为什么未标注或 Ambiguous 必须报错而不降级为不相关；待教：排名与汇总口径（功能 2） | 旧 qrels 归档差异仍未解决，本轮调查证据见下方“功能 1 证据”；功能 2 待用户确认后开始 |
| 2A 一条 Query 数据流 | 新增 `src/casetrace/evaluation/runner.py`（`build_retriever` / `rank_query` / `evaluate_query`，数据类 `RankedCase` / `QueryEvaluation`）与 `tests/evaluation/test_runner.py`；两者在基线 manifest 中均为 absent，属新增；功能 2 步骤 A 未改动任何既有文件 | `uv run pytest -q tests/evaluation/test_runner.py` → **10 passed in 0.08s**；`uv run pytest -q` → **259 passed、169 subtests passed、1 failed**（唯一失败仍是既有 dev-v1 归档哈希断言）；`uv run casetrace demo --json` 正常，默认 top_k=4 的前 4 名与运行器前 4 名逐项一致。真实 dev-v2 观测（含分数）：Q001 `C001 5.1445 / C003 3.4620 / C004 2.4802 / C002 1.6463 / C005 0.9556 / C006 0.7321`，Recall@4 = nDCG@4 = RR@4 = 1.0；Q002 返回 5 条、`C005` 第 1 名，Recall@4 = nDCG@4 = RR@4 = 1.0；Q003 返回 5 条、`C006` 第 1 名，同为 1.0。未跑：跨 Query 汇总（2B）、结果保存与 CLI（2C） | 已讲：一条 Query 的完整数据流、请求范围为何覆盖全语料、为何先校验返回 ID 再计分、标签不进入检索的防泄漏测法与 `None` 的单条含义。待教：跨 Query 汇总口径与无正例排除政策（2B） | 已实现、自测并讲解，用户 2026-09-21 确认理解；下一会话从 2B 继续；旧 qrels 归档差异仍未解决 |
| 2B 跨 Query 汇总 | 在 `src/casetrace/evaluation/runner.py` 追加汇总常量（`RR_KEY` / `MRR_KEY` / `SCORE_KEYS` / `SUMMARY_METRIC_KEYS` / `NO_RELEVANT_REASON`）、数据类（`ExcludedQuery` / `MetricSummary` / `EvaluationSummary`）与 `aggregate(evaluations)`；`evaluate_query` 的 RR 计分改用 `RR_KEY`（同一个键，行为不变）；`tests/evaluation/test_runner.py` 追加 7 个汇总测试。未新增文件，未改动指标函数、benchmark loader、qrels、BM25 参数或 CLI | `uv run pytest -q tests/evaluation/test_runner.py` → **17 passed in 0.13s**（10 既有 + 7 新增）；`uv run pytest -q` → **266 passed、169 subtests passed、1 failed**（唯一失败仍是既有 dev-v1 归档哈希断言）；真实 dev-v2 只读观测汇总：`recall@1 0.75`、`recall@3 0.9167`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5556`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`，三条 Query 全部参与、无排除。未跑：结果保存与 CLI（2C）、正式运行与错误分析（功能 4） | 已讲：逐 Query 分数如何汇总为跨 Query 读数、为何 Query 等权平均、RR@4 的均值为何命名 `mrr@4`、无正例 Query 为何排除 Recall/nDCG/MRR 但 Precision 计入 0.0、为何无参与者是 `None` 而不是 0；已讲：逐 Query 分数如何汇总为跨 Query 读数、为何 Query 等权平均、RR@4 的均值为何命名 `mrr@4`、无正例 Query 为何排除 Recall/nDCG/MRR 但 Precision 计入 0.0、为何无参与者是 `None` 而不是 0；用户 2026-09-21 回复“理解 下一步”确认，2B 教学收束 | 旧 qrels 归档差异仍未解决；进行 2C（结果 JSON 复现字段与 `evaluate` 子命令） |
| 3 CLI 与复现（2C） | `src/casetrace/evaluation/runner.py` 增加 `run_evaluation` / `write_report` 与报告常量、私有辅助函数；`src/casetrace/__init__.py` 增加 `evaluate` 子命令（`--qrels` 默认活动 dev-v2、`--output` 必填）；`README.md` 补运行入口与结果说明；`tests/evaluation/test_runner.py` 追加 5 个报告层测试；新增 `tests/test_cli_evaluate.py`（6 个测试）。未改指标函数、benchmark loader、qrels、BM25 参数或 demo 行为 | `uv run pytest -q tests/test_cli_evaluate.py tests/evaluation/test_runner.py` → **28 passed in 0.48s**；`uv run pytest -q` → **277 passed、169 subtests passed、1 failed**（唯一失败仍是既有 dev-v1 归档哈希断言）；`uv run casetrace demo` → exit 0、C001 第 1 名，行为未变；`uv run casetrace evaluate --output /tmp/m2-2c-report.json` → exit 0、报告 13,406 字节；缺失 qrels → exit 2、stderr 指明文件、输出目录无任何文件；两次运行除 `generated_at` 外报告完全相等。未跑：正式结果落盘与错误分析（功能 4） | 已讲：报告里各字段为何需要、为何只记哈希不记耗时、为何先写临时文件再替换、为何默认输入与输出路径要写清楚；用户 2026-09-22 确认 2C 讲解（原话「我已理解 2C」） | 旧 qrels 归档差异仍未解决；下一步功能 4（正式运行、错误分析与最终回交） |
| 4A 正式运行与落盘 | 新增 `results/dev-v2-bm25.json`（13,460 B）、`results/dev-v2-bm25.cli.txt`（883 B）、`results/pytest-full.log`（1,891 B）、`results/README.md`；`README.md` 加运行记录入口（`ccb649f5097c…` → `6dc41106c871…`）。未改指标函数、benchmark loader、runner、`__init__.py`、qrels、BM25 参数、`demo.py` 或任何既有测试 | `uv run pytest -q` → **277 passed、169 subtests passed、1 failed in 2.26s**（唯一失败仍是既有 dev-v1 归档哈希断言，原始输出已保存）；`uv run casetrace evaluate --output results/dev-v2-bm25.json` → exit 0；重复运行到 `/tmp/4a-repeat.json` 除 `generated_at` 外完全相等；只读自测脚本 37/37 通过；`uv run casetrace demo` → exit 0、C001 第 1 名。未跑：4B 错误分析、4C 最终回交 | 已讲：为何必须同时记录输入 / 代码 / 依赖哈希、为何 `generated_at` 与耗时不能用于排名比较、为何软件测试通过 ≠ 检索质量达标；用户 2026-09-22 就「这一步是否只运行没写代码」「运行完的结论是什么」提问，Cline 就地澄清后用户要求继续 4B（未单独复述概念确认） | 旧 qrels 归档差异仍未解决；报告文件权限 600 记为可选后续项；下一步 4B 错误分析（K=4 漏检与阅读期望） |
| 4B 错误分析 | 新增 `results/dev-v2-bm25-error-analysis.md`（144 行，绑定 `evaluation-result-v1` 结果哈希 `25aca703de92…`）；`results/README.md` 追加分析入口与 4B 自测记录（`1361133f54fa…` → `c0ee20e8c207…`）。**未改任何代码、测试、qrels、标签或 BM25 参数**（`runner.py 02dbaa9c25eb…`、`demo.py 27b92bc46db1…`、`bm25.py e21e00f76bae…`、`test_runner.py 146f05f1bea9…` 与 4A 结束时一致）；未改 `current-plan.md` / `practical-todo.md` | 只读重算脚本 174/174 通过；`uv run pytest -q` 未重跑（本步骤未改代码，测试结论沿用 4A 的 277 passed、169 subtests passed、1 failed）。分析结论：三条 Query 在 K=4 **均无漏检**（Q001 在 K=3 缺 C002，第 4 名）；Q001 同异常分组 G001 位于第 1/2/3 名、仅同产品的 C002 第 4 名，Q002/Q003 唯一正例第 1 名，**符合已记录的阅读期望**；机制与三类可复现问题：本语料 N=6、`epsilon=0.25`、`average_idf=0.8373615299`，df≥4 的词项原始 idf 为负、被统一压到地板 `0.20934038248156323`（df=3 恰为 0，只有 df≤2 真正在排序），由此解释 ① 高频泛词误召（`确认`/`检查` df=6、`发现` df=5）、② Query 背景句贡献主要命中（Q002 第 2 名 C002 靠只它含有的 `调查`、df=1）、③ 否定语境被计为命中（C002 文本"未发现剥离"仍命中 `焊线`/`剥离`）；并给出「问题 → 可能原因 → 下一步实验」表（全部登记为 M3 输入）。未跑：4C 最终回交 | 待讲：K=4 漏检为 0 为何不等于质量达标、idf 与 epsilon 地板如何解释误召、为什么否定语境是词袋模型的局限而不是标签错误、为什么这些结论只登记为 M3 实验而不在 M2 调权重；待用户确认 | 旧 qrels 归档差异仍未解决；报告权限 600 与本次无关；下一步 4C（更新 Current Plan / practical-todo、最终回报并标 `ready for final Codex review`） |
| 4C 最终回交 | `docs/project/current-plan.md`（追加 2026-09-22 交付条目、更新「当前位置」与「下一项交付」）、`docs/project/practical-todo.md`（第 5、6 项勾选、顶部当前位置、追加 2026-09-22 条目）、`README.md`（「当前状态」两处）、本包（状态行、4B 用户确认、最后补充清单、4C 证据）。**未改代码、测试、数据或结果文件**；`results/` 五个文件哈希与 4B 结束时逐一相同 | 交付时复跑 `uv run pytest -q` → **277 passed、169 subtests passed、1 failed in 2.21s**（既有 dev-v1 归档哈希断言）；`uv run casetrace demo` → exit 0；只读文档核对脚本 50/50 通过（链接可达、完整与缩写哈希可解析、包内每处快照引用与文件实际哈希一致、勾选状态与证据一致） | 已讲：最终回交清单与状态含义（ready for review ≠ accepted）；用户 2026-09-22 确认 4A / 4B 后进入本步骤，并在讲解后确认 4C（原话见 4C 证据），Cline 侧 M2 交付收束，是否交 Codex 由用户决定 | 旧 qrels 归档差异仍未解决；报告权限 600 记为可选后续项；nDCG 与 M2 整体待 Codex 总审；工作止于 M2 |

最后补充（4C 收尾，2026-09-22）：**M2 已全部交付，标 `ready for final Codex review`，尚未验收。** 最终回交清单如下。

- **新增文件**（相对阶段基线 manifest，记为 `exists: false` 或未列出）：`src/casetrace/evaluation/benchmark.py`、`src/casetrace/evaluation/runner.py`、`tests/evaluation/test_benchmark.py`、`tests/evaluation/test_runner.py`、`tests/test_cli_evaluate.py`、`results/dev-v2-bm25.json`、`results/dev-v2-bm25.cli.txt`、`results/pytest-full.log`、`results/README.md`、`results/dev-v2-bm25-error-analysis.md`。`src/casetrace/evaluation/metrics.py` 与 `tests/evaluation/test_metrics.py` 在基线中已存在（nDCG 属本阶段之前的实现，纳入本次总审）。
- **改动既有文件**：`src/casetrace/demo.py`（抽出 `load_validated_dataset` / `check_source_records`，`run_demo` 行为不变）、`src/casetrace/__init__.py`（新增 `evaluate` 子命令）、`README.md`（运行入口、结果与分析索引、M2 状态）、`docs/project/current-plan.md`、`docs/project/practical-todo.md`、`results/README.md`、本包。`data/`、`AGENTS.md`、`.clinerules/rules.md`、`docs/data/` 在本阶段未由 Cline 改动。
- **基线位置**：阶段基线 `/tmp/casetrace-m2-completion-k6qwn8y1`（`handoff/files` 为起点内容，`handoff/additional/*.pre-m2-feature1|2b|2c|4a|4b|4c` 为各步骤快照，`manifest.json` / `head.txt` / `git-status.txt` 为对照）；nDCG 原基线 `/tmp/casetrace-m2-ndcg-px71dp48` 保留，审核需与本阶段增量叠加。
- **运行命令与真实结果**：`uv run pytest -q`（2026-09-22 交付时复跑）→ **277 passed、169 subtests passed、1 failed in 2.21s**（唯一失败为既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言）；`uv run casetrace evaluate --output results/dev-v2-bm25.json` → exit 0（13,460 B，`evaluation-result-v1`）；同一命令重复运行除 `generated_at` 外完全相等；`uv run casetrace demo` → exit 0、C001 第 1 名。只读自测：4A 37/37、4B 174/174、4C 文档核对全部通过。
- **结果与分析路径**：`results/dev-v2-bm25.json`、`results/dev-v2-bm25.cli.txt`、`results/pytest-full.log`、`results/README.md`（运行记录与复现步骤）、`results/dev-v2-bm25-error-analysis.md`（错误分析）。
- **版本配置**：qrels `dev-qrels-v2` / `development` / 确认日 2026-09-19（`a3dfc79ef010…`）；dataset `6923d382ba08…`；reference `f5001bddd3df…`；BM25 `k1=1.5` / `b=0.75` / `epsilon=0.25`；指标 K=1/3/4 与 RR@4（汇总命名 `mrr@4`）；Python 3.12.3 与依赖版本、源码 / `uv.lock` 哈希见 `results/README.md`。
- **未解决 / 失败证据**：旧 `dev-v1/qrels.json` 归档哈希不一致（实际 `e92e5bb1f84d…`，记录 `c01752264333…`），未刷新哈希、未改旧文件，测试失败保持可见；`results/dev-v2-bm25.json` 权限 600 记为可选后续项；工作区未提交，复现需核对源码与依赖哈希。
- **用户确认**：2A / 2B（2026-09-21）、2C（2026-09-22 原话「我已理解 2C」）、4A / 4B（2026-09-22 原话「4A 和 B 基本理解了」）；nDCG（M2-02）由用户表示该步骤已完成，仍纳入总审。
- **待教 / 未做**：M2 无未讲功能（4C 只做文档收尾）；M3 的 Embedding / Hybrid / Rerank 与后续 Grounded Answer 尚未开始，不得在本阶段提前展开。

### 功能 1 证据（Cline 追加，2026-09-20）

- 新增文件：`src/casetrace/evaluation/benchmark.py`（`load_benchmark`、`_verify_source`、`_parse_queries`、`_check_point_in_time`、`_parse_judgments`；数据类 `Benchmark` / `BenchmarkQuery` / `VerifiedSource`），`tests/evaluation/test_benchmark.py`。
- 改动既有文件：`src/casetrace/demo.py` 抽出 `load_validated_dataset` 与 `check_source_records`，`run_demo` 调用两者，行为不变（`abnormal_processes`、检索文本等未动）；快照见 Handoff Baseline。该文件相对 HEAD 的 diff 还包含本阶段之前未提交的异常站点修订，本功能净改动仅为这两个函数的抽取，已与 `handoff/additional/demo.py.pre-m2-feature1` 逐行核对。README / CLI 未改，功能 3 再接 CLI。
- 校验行为：qrels 版本 / split / `human_confirmed` / `confirmed_on`；`sources` 两个文件按原字节核对 SHA-256（报文件、预期、实际，失败不刷新哈希、不改源文件，测试已验证失败后两个哈希都不变）；Dataset 的 split 与 review_status；Query ID 唯一、`known_at` 为日期；时点一致性（语料最晚发现日期不得晚于任一 Query 时点，失败说明未实现通用时间过滤）；18 对配对完整、无重复、ID 属于本次语料、标签为整数 0/1、理由非空。标签确认与源 Case 的 `draft_pending_human_review` 分开记录于 `dataset_review_status`。
- 命令与结果：`uv run pytest -q tests/evaluation/test_benchmark.py` → `27 passed in 0.49s`；`uv run pytest -q` → `1 failed, 249 passed, 169 subtests passed in 1.98s`；`uv run casetrace demo` → 正常输出 6 条语料、C001 排名第 1。真实 dev-v2 读取实测输出：`dev-qrels-v2 development 2026-09-19`，源 Case 状态 `draft_pending_human_review`，语料最晚发现日 `2026-06-15`，正例 `Q001=C001,C002,C003,C004 / Q002=C005 / Q003=C006`，dataset / reference 哈希前缀 `6923d382ba08` / `f5001bddd3df`，与 qrels 记录一致。
- 旧 qrels 归档问题（本轮调查，仍未解决）：`find /` 全盘搜索 `qrels*.json` 只有仓库的 dev-v1 / dev-v2 与各阶段 `/tmp` 基线副本，均不含记录值；`c0175226…` 只出现在文档与测试里。dev-v1 现文件含“情况相近”、不含 v2 新表述；两种短语替换后哈希分别为 `87fd2dd8a8d47bf36b0bb4e92a73f0d5ed02784afb9506661c462fb3df2294f3` 和 `70da58b0341e66802b52678b5c39430d8953b843a5c567746241bedb4178432b`，都不等于记录值 `c0175226433332e1ac592e0850248fe7bd4dbde9173d3c8f0773c2d1602a245e`，说明差异不止该短语。保留现有文件与哈希，不猜测标签、不刷新记录；该失败保持可见并单独报告，不计入功能 1 的通过项。

### 功能 2 步骤 A 证据（Cline 追加，2026-09-21）

- 新增文件（基线 manifest 记录为 absent）：`src/casetrace/evaluation/runner.py` SHA-256 `9ed8d04fd3a2f39ce6ec749c63eb945a269aa27ab7c6f4eb757d37531b8bfcc8`；`tests/evaluation/test_runner.py` SHA-256 `6948d7a53b031094dfe930b3fd2cec78b97bfc2fe82fcdde404be60ba1f0de58`。未改动既有文件，故 Handoff Baseline 无需补快照。
- 基线对照：功能 2 步骤 A 开始时工作区与功能 1 结束时一致，无外部介入改动。活动输入未变：`data/dev/demo.json` = `6923d382ba08…`（与 qrels 记录一致）、`data/evaluation/dev-v2/qrels.json` = `a3dfc79ef010…`、`src/casetrace/evaluation/benchmark.py` = `b18f96ea1e10…`、`metrics.py` = `47e55310fc9e…`。`src/casetrace/demo.py` 现为 `27b92bc46db1…`，与阶段基线 `c442970b…` 的差异来自功能 1 抽出的 `load_validated_dataset` / `check_source_records`，已在该功能回报，本步骤未再改动。
- 实现要点：`build_retriever` 只调用已确认的 `build_documents`，并核对文档键与 `benchmark.case_ids` 完全一致；`rank_query` 以 `top_k=len(case_ids)` 请求整个语料，保留 BM25 实际返回的全部条目（不补分、不补名次），并拒绝语料之外或重复的返回 ID；`evaluate_query` 先排名、再取该 Query 的正例，最后按 `METRIC_KS = (1, 3, 4)` 与 `RECIPROCAL_RANK_K = 4` 计分，键为 `recall@k` / `precision@k` / `ndcg@k` / `rr@4`，无正例时沿用指标函数的 `None`。
- 测试（`tests/evaluation/test_runner.py`，10 passed）：覆盖全语料请求范围、未知与重复返回 ID 被拒绝、语料键不一致被拒绝、固定排名的逐 K 手算值、无正例 Query 的 `None` 与 Precision 0.0、标签全置 0 后排名不变（防泄漏）、加入 `FUTURE_CAUSE_LEAK` / `ANNOTATION_LEAK` / `QRELS_LEAK` 元数据后文档与排名不变、真实 dev-v2 的重复运行一致性及「排名 ⊆ 语料、名次连续、分数落在 0–1」结构性检查。测试未把任何具体排名写成标准。
- 命令与结果：`uv run pytest -q tests/evaluation/test_runner.py` → `10 passed in 0.08s`；`uv run pytest -q` → `259 passed、169 subtests passed、1 failed in 1.97s`；失败为既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言（文件实际 `e92e5bb1f84d…` 与记录 `c01752264333…` 不符），与阶段基线一致，非本步骤引入。`uv run casetrace demo --json` 正常输出 6 条语料，默认 top_k=4 的前 4 名为 `C001 / C003 / C004 / C002`，与运行器前 4 名一致。
- 真实观测（只读脚本，未保存为结果文件；正式结果文件属 2C）：Q001 返回 6 条（`C001 5.1445`、`C003 3.4620`、`C004 2.4802`、`C002 1.6463`、`C005 0.9556`、`C006 0.7321`），Recall@1/3/4 = 0.25 / 0.75 / 1.0，Precision@1/3/4 = 1.0 / 1.0 / 1.0，nDCG@1/3/4 = 1.0 / 1.0 / 1.0，RR@4 = 1.0；Q002 返回 5 条（`C005` 第 1 名），Precision@3 = 0.3333、Precision@4 = 0.25，其余为 1.0；Q003 返回 5 条（`C006` 第 1 名），读数与 Q002 相同。这些是当前语料与 BM25 参数下的观测读数，不构成检索质量结论或泛化能力声明。
- 尚未完成：跨 Query 汇总与无正例排除政策（2B）、结果 JSON 的复现字段与 CLI 子命令（2C）、正式运行与错误分析（功能 4）。旧 qrels 归档差异仍保留为未解决项。
- 用户确认（2026-09-21）：用户表示“基本理解”，并说明会在新窗口继续后续内容；2A 教学到此收束，下一次会话从 2B（跨 Query 汇总与无正例排除政策）开始。

### 功能 2 步骤 B 证据（Cline 追加，2026-09-21）

- 改动文件与哈希：`src/casetrace/evaluation/runner.py` SHA-256 `095627e2f0ce…`（2B 前 `9ed8d04fd3a2…`）；`tests/evaluation/test_runner.py` SHA-256 `9674f7e2b749…`（2B 前 `6948d7a53b03…`）。无新增文件；`git status` 中 `src/` 与 `tests/` 的其余条目均为阶段之前的既有改动，本步骤未触碰。
- 实现要点：`aggregate` 按 `SUMMARY_METRIC_KEYS` 的固定顺序逐指标汇总。每个指标单独判断逐 Query 分数：为 `None` 且该 Query 无正例时记入 `excluded`（`reason = no_relevant_case`）；为 `None` 却有正例说明口径不一致，直接报错，不静默少算一个分母。Precision 因指标函数口径返回 `0.0` 而被纳入均值，未做额外改造。均值只对参与 Query 等权平均，没有参与者时为 `None`，不除零、也不写成 0。逐 Query 的 `rr@4` 保留，汇总键为 `mrr@4`。另加两道输入守卫：重复 `query_id` 报错、逐 Query 分数键与 `SCORE_KEYS` 不符报错。改动仅涉及 `runner.py`，未改指标函数、benchmark loader、qrels、BM25 参数或 CLI。
- 测试（`tests/evaluation/test_runner.py`，17 passed）：新增 7 个测试覆盖等权平均的手算值（含 Q002 只返回 3 条、Q003 只返回 1 条，验证“返回不足 K 条”仍按函数口径参与均值）、单条无正例 Query 的排除与 Precision 例外、三条全无正例时 Recall / nDCG / MRR 汇总为 `None` 而 Precision 为 0.0、空输入不除零、重复 Query ID 被拒绝、`None` 与正例冲突被拒绝、缺失分数键被拒绝，以及真实 dev-v2 的汇总等于逐 Query 分数的手算均值且重复汇总结果相等。无正例政策全部用 `dataclasses.replace` 的内存合成输入测试，仓库 qrels 未被修改；测试未把任何真实排名写成期望值。
- 命令与结果：`uv run pytest -q tests/evaluation/test_runner.py` → `17 passed in 0.13s`；`uv run pytest -q` → `266 passed、169 subtests passed、1 failed in 1.98s`；失败仍是既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言，与阶段基线一致，非本步骤引入。
- 真实观测（只读脚本 `/tmp/m2-2b-observe.py`，未保存为结果文件；正式结果文件属 2C）：Q001 返回 6 条，逐 Query 读数 `recall@1 0.25`、`recall@3 0.75`，`recall@4` / `precision@1/3/4` / `nDCG@1/3/4` / `rr@4` 均为 1.0；Q002 返回 5 条，`precision@3 0.3333`、`precision@4 0.25`，其余为 1.0；Q003 与 Q002 读数相同。汇总（三条等权）：`recall@1 0.75`、`recall@3 0.9167`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5556`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`；`no_relevant_query_ids` 为空，每个指标的 `included` 都是三条 Query、`excluded` 为空。这些是当前语料与 BM25 参数下的观测读数，不构成检索质量结论或泛化能力声明。
- 尚未完成：结果 JSON 的复现字段与 `evaluate` 子命令（2C）、正式运行与错误分析（功能 4）。旧 qrels 归档差异仍保留为未解决项。
- 用户确认（2026-09-21）：用户回复“理解 下一步”，确认 2B 讲解，并要求继续下一步；2B 教学到此收束，随后进入 2C（任务包功能 3：结果保存与 CLI）。


### 功能 3 证据（Cline 追加，2026-09-21）

- 改动与新增：`src/casetrace/evaluation/runner.py`（SHA-256 `02dbaa9c25eb…`，2C 前 `095627e2f0ce…`）新增 `run_evaluation`、`write_report`，以及报告常量（`RESULT_SCHEMA_VERSION` / `HISTORY_SNAPSHOT` / `NO_RELEVANT_POLICY` / `METRIC_DEFINITIONS` / `REPRODUCIBILITY_SOURCE_FILES`）与私有辅助（`_relative` / `_file_sha256` / `_package_versions` / `_git_state` / `_benchmark_document` / `_retrieval_document` / `_metrics_document` / `_reproducibility_document`）；`src/casetrace/__init__.py`（`938fe804e20e…`，2C 前 `552dead8e8f2…`）新增 `evaluate` 子命令；`README.md`（`ccb649f5097c…`，2C 前 `2a4a747fe95b…`）补运行入口、结果位置与复现说明；`tests/evaluation/test_runner.py`（`146f05f1bea9…`）追加 5 个报告层测试；新增 `tests/test_cli_evaluate.py`（`33aec84fa7f3…`，6 个 CLI 测试）。未改指标函数、benchmark loader、已确认 qrels、BM25 参数或 demo 行为。
- 报告字段：`schema_version`、`generated_at`；`benchmark`（qrels 相对路径 / 版本 / 实际哈希 / 确认日 / split、dataset 与 reference 的记录路径和实际哈希、dataset 审阅状态、语料最晚发现日、历史快照说明）；`retrieval`（方法、实现、分词与文档构建入口、语料与请求规模、实际 `k1` / `b` / `epsilon`、不补分不补名次的说明）；`metrics`（K 列表、RR 的 K、汇总键顺序、逐指标公式口径、无正例政策、同基准比较说明）；`queries`（逐 Query 完整排名、分数、命中词项、标签与逐指标分数）；`summary`（逐指标均值及参与 / 排除清单）；`reproducibility`（Python 与依赖版本、git HEAD、脏工作区布尔与路径清单、7 个源码 / 配置文件与 `uv.lock` 的 SHA-256、`generated_at` 不得用于排名比较的说明）。
- 保存语义：`write_report` 先在同目录写临时文件再 `os.replace` 原子替换；写入失败时删除临时文件，目标无法替换（例如目标是目录）时抛错且原有文件保持不变。CLI 在输入校验或保存失败时经 `parser.error` 以退出码 2 返回，不写结果文件。
- 命令与结果：`uv run pytest -q tests/test_cli_evaluate.py tests/evaluation/test_runner.py` → **28 passed in 0.48s**；`uv run pytest -q` → **277 passed、169 subtests passed、1 failed in 2.42s**（唯一失败仍是既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言）；`uv run casetrace demo` → exit 0、输出 6 条语料、C001 排名第 1，demo 行为未变。`uv run casetrace evaluate --output /tmp/m2-2c-report.json` → exit 0，报告 13,406 字节，字段齐全。失败路径实测：`--qrels data/evaluation/dev-v2/nope.json` → exit 2、stderr 指明缺失文件、输出目录内没有任何文件。重复运行实测：一次用默认 `--qrels`、一次显式指定，除 `generated_at` 外报告完全相等，排名与分数一致，`mrr@4 = 1.0`。
- 观测读数（当前语料与 BM25 参数，非质量结论）：Q001 `C001 > C003 > C004 > C002 > C005 > C006`；Q002 `C005 > C002 > C006 > C001 > C004`；Q003 `C006 > C005 > C002 > C001 > C004`；汇总与 2B 相同。
- 尚未完成：功能 4（正式运行并保存结果文件、简短错误分析、最终回交报告）。旧 qrels 归档差异仍为未解决项；仓库内尚未创建 `results/` 与正式结果文件。（截至 2C 结束时的状态；其中「正式运行并保存结果文件」已由功能 4 步骤 A 完成，见下节，错误分析与最终回交仍待做。）
- 用户确认（2026-09-22）：用户原话「我已理解 2C」；2C 教学到此收束，随后进入功能 4 步骤 A。

### 功能 4 步骤 A 证据（Cline 追加，2026-09-22）

- 本步骤定性：只做正式运行与结果落盘，**不新增或修改任何产品代码**。检索、指标、报告生成、原子写入与 CLI 全部沿用 2C 已自测的实现；本轮也没有新增或修改测试。
- 起点核对：HEAD 仍为 `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。按 `git status --porcelain -uall` 与阶段基线 `handoff/git-status.txt` 逐路径比较（143 → 152 条），新增路径只有已回报的 M2 文件（`src/casetrace/evaluation/benchmark.py`、`runner.py`、`tests/evaluation/test_benchmark.py`、`test_runner.py`、`tests/test_cli_evaluate.py`）与本步骤的 `results/` 四个文件，**未见未回报的外部改动**。活动输入与代码哈希与 2C 回报逐字节一致：`qrels.json a3dfc79ef010…`、`demo.json 6923d382ba08…`、`runner.py 02dbaa9c25eb…`、`__init__.py 938fe804e20e…`、`benchmark.py b18f96ea1e10…`、`metrics.py 47e55310fc9e…`、`demo.py 27b92bc46db1…`、`bm25.py e21e00f76bae…`。阶段基线与 nDCG 原基线仍在原路径。
- 新增文件与哈希：`results/dev-v2-bm25.json` SHA-256 `25aca703de9270abcd4c47538aabde3691b047696db65b06f8ab55f75953f191`（13,460 B，`evaluation-result-v1`）；`results/dev-v2-bm25.cli.txt` `f159d812375f4cceb9c0149f430713321527c67582aca4e5baa3668b0ac0ab84`（883 B）；`results/pytest-full.log` `53c649d3c1b460b644680408c99c1cb6461dff9676d525464591034bbc912b20`（1,891 B）；`results/README.md` `1361133f54fadb05c1a70aa9c6a68a176ffb408e9c258cfc1bf2e124161e7ad3`。
- 改动既有文件：只有 `README.md`，加了指向 `results/README.md` 的运行记录入口，并把末尾索引表的「结果记录」一行改为指向 `results/`；哈希 `ccb649f5097c7df2…` → `6dc41106c871d54f…`。`docs/project/current-plan.md` 与 `docs/project/practical-todo.md` **本步骤未改动**，进度状态按计划留到 4C 统一更新；本包按回报需要追加。`data/`、`src/`、`tests/` 均未改动。
- 正式运行实测：`uv run pytest -q` → 退出码 1，**277 passed、169 subtests passed、1 failed in 2.26s**；唯一失败 `tests/test_benchmark_migration.py::test_v2_preserves_old_snapshot_queries_and_only_confirmed_label_correction`（断言在 `tests/test_benchmark_migration.py:19`），仍是既有 dev-v1 归档哈希问题，与阶段基线一致，**非本步骤引入**；原始输出已存 `results/pytest-full.log`。`uv run casetrace evaluate --output results/dev-v2-bm25.json` → 退出码 0，`results/` 内无 `.tmp` 残留；`uv run casetrace demo` → 退出码 0、C001 第 1 名，demo 行为未变。
- 交付读数（当前语料与参数下的观测值，不是质量结论）：Q001 返回 6 条 `C001 > C003 > C004 > C002 > C005 > C006`；Q002 返回 5 条 `C005 > C002 > C006 > C001 > C004`；Q003 返回 5 条 `C006 > C005 > C002 > C001 > C004`。汇总（三条 Query 全部参与、无排除）：`recall@1 0.75`、`recall@3 0.9166666666666666`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5555555555555555`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`。与 2A / 2B / 2C 的记录一致，未出现漂移。
- 可重复性与结构自测（只读脚本 `/tmp/m2-4a-verify.py`，临时文件，未入仓库）：同一命令写到 `/tmp/4a-repeat.json`，两份报告**除 `generated_at` 外完全相等**（`2026-09-21T16:31:32+00:00` / `2026-09-21T16:32:24+00:00`）；脚本 **37 / 37 通过**，覆盖顶层字段与顺序、schema 版本、输入哈希三层一致（报告 == 磁盘实际字节 == qrels `sources`）、逐 Query 名次连续 1..n、排名无重复且属于语料、逐 Query 正例等于已确认 qrels、10 个汇总指标等于逐 Query 分数的手算等权均值及其参与 / 排除清单、无 `.tmp` 残留。脚本只读，任何具体排名都没有被写成测试期望值。
- 复现记录内容：`results/README.md` 写明运行命令、日期、HEAD 与脏工作区、产物哈希、输入与源码 / 依赖哈希（含 `pyproject.toml a7562713a0af…`、`uv.lock 6ae96bf9c5f0…`）、Python `3.12.3` 与 `casetrace 0.1.0 / rank-bm25 0.2.2 / openpyxl 3.1.5`、指标口径、复现步骤、已跑 / 未跑检查、局限，并明确 `generated_at` 与耗时不得用于排名比较。
- 观察（不影响读数，未改代码）：`write_report` 经 `tempfile.NamedTemporaryFile` 落盘，结果 JSON 权限为 `-rw-------`（600），与 `results/` 内其它 664 文件不同；已记录为可选后续项，交 Codex 判断是否需要在后续处理。
- 未完成 / 未跑：4B（逐 Query K=4 漏检与阅读期望核对，不修改代码与标签）、4C（更新 Current Plan 与 practical-todo、汇总最终回报并标 `ready for final Codex review`）。旧 dev-v1 qrels 归档哈希差异仍为未解决项，本轮未刷新哈希、未改旧文件、未猜测标签。（本节状态截至 4B 结束时；4C 完成后 M2 标 `ready for final Codex review`，见下方 4C 一节与本包末尾。）
- 用户确认（2026-09-22）：用户就本步骤提出两处澄清问题（这一步是否只运行没写代码、运行完的结论是什么），Cline 就地澄清后要求继续 4B；4A 教学到此收束，用户未单独复述概念确认。

### 功能 4 步骤 B 证据（Cline 追加，2026-09-22）

- 本步骤定性：只做只读错误分析并写文档，**未新增或修改任何代码、测试、qrels、标签或 BM25 参数**。`runner.py 02dbaa9c25eb…`、`__init__.py 938fe804e20e…`、`demo.py 27b92bc46db1…`、`bm25.py e21e00f76bae…`、`tests/evaluation/test_runner.py 146f05f1bea9…` 与 4A 结束时逐一相同；`results/dev-v2-bm25.json` 保持 `25aca703de92…`。
- 起点核对：HEAD 仍为 `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`；两个 4B 快照哈希与 4A 记录相符，说明本步骤开始时无外部介入改动。
- 新增文件：`results/dev-v2-bm25-error-analysis.md`（144 行，SHA-256 `7c522b2675309e90558a6e6ddc623cba71224ef78d9d7f5b514294e1814ddc60`）。改动既有文件：只有 `results/README.md`，追加分析入口与 4B 自测记录（`1361133f54fa…` → `c0ee20e8c207…`）；`docs/project/current-plan.md` 与 `docs/project/practical-todo.md` 未动，留待 4C。
- 分析内容与实测事实（全部可由结果文件与语料重算）：**§1 K=4 漏检** —— Q001 正例 4 个、K=1 命中 1、K=3 命中 3、K=4 命中 4、K=3 漏检 C002、K=4 漏检无；Q002、Q003 唯一正例均位于第 1 名，各 K 值均无漏检。**§2 阅读期望对照** —— G001（`same_abnormal_process`，共同工序 P004）的 C001 / C003 / C004 位于第 1 / 2 / 3 名，仅同产品的 C002（P013）第 4 名；Q002 / Q003 唯一正例第 1 名；未出现"同异常记录排在仅同产品记录之后"的倒置。**§3 数据表** —— 逐 Query 完整排名、分数与命中词项 16 行，词项判别力 18 行（`确认` / `检查` df=6、`发现` df=5、`剥离` / `焊线` df=4、`调查` df=1、`prod_001` df=2）。**§4 机制与三类可复现问题** —— 先记录本语料的实际权重机制：`rank_bm25==0.2.2` 的 `idf = ln(N - df + 0.5) - ln(df + 0.5)`，负值被替换为 `epsilon × average_idf`；本语料 `N=6` / `epsilon=0.25` / `average_idf=0.8373615299262529` / 地板 `0.20934038248156323`，实测 `确认`/`检查`(df=6)、`发现`(df=5)、`剥离`/`焊线`(df=4) 全部等于地板，`显示`/`oqc`(df=3) 为 0，只有 df≤2 的词项有正向权重（df=2 → 0.5877866649021191；df=1 → 1.2992829841302609）。据此解释：4.1 高频泛词无判别力造成误召（Q001 第 5 / 6 名命中词项权重全部不高于地板，分数 0.9556 / 0.7321）；4.2 Query 背景句与元话语贡献主要命中（Q002 第 2 名 C002 靠只有它含有的 `调查`、df=1；Q003 的 C002 靠 `客户` 高于同样只含 `发现` 的 C001 / C004）；4.3 否定语境被计为命中（C002 检索文本含"内部焊线检查未发现剥离"，仍与 Q001 的 `焊线` / `剥离` 重合，被抬到第 4 名）；4.4 第 2 名之后的量级只由单个词项决定（0.2133–1.8190），不应解读为相关性排序。**§5** 给出「问题 → 可能原因 → 下一步实验」表，五条全部登记为 M3 输入，M2 不调整权重与分词。
- 自测：只读重算脚本 `/tmp/m2-4b-verify-doc.py`（临时文件，未入库）**174 / 174 通过**，对照项包括文档声明的结果文件哈希、排名表 16 行（名次 / Case / 分数 / 命中词项数与内容）、漏检表 3 行、判别力表 18 行的 df 与 Case 列表、机制表 18 行的实际 idf（含 `corpus_size` / `epsilon` / `average_idf` / 地板值、原始负值判定、df=3 恰为 0），以及定性结论（G001 位次、C002 位次、Q002 / Q003 第 1 名、C002 文本含 `焊线` 与 `剥离`、Q001 第 5 / 6 名命中词项权重均不高于地板、`力检` 只出现在 C001）。**未重跑 `uv run pytest`**：本步骤未改代码，测试结论沿用 4A 的 **277 passed、169 subtests passed、1 failed**（既有 dev-v1 归档哈希断言）；该限制已同时写在 `results/README.md` 与 `results/dev-v2-bm25-error-analysis.md`。
- 边界与未解决项：零漏检不代表质量达标（6 条语料 / 3 条 Query / 单一参数）；本分析不把排序差距称为标签错误，也不用额外权重"修好"M2；旧 dev-v1 qrels 归档哈希差异仍未解决，本轮未刷新哈希、未改旧文件。（本节状态截至 4B 结束时；4C 完成后 M2 标 `ready for final Codex review`，见下方 4C 一节与本包末尾。）
- 用户确认（2026-09-22）：用户原话「4A 和 B 基本理解了」；4B 教学到此收束，随后进入 4C。

### 功能 4 步骤 C 证据（Cline 追加，2026-09-22）

- 本步骤定性：只更新进度与回报文档，**不改代码、测试、数据或结果文件**。交付时复跑 `uv run pytest -q` → **277 passed、169 subtests passed、1 failed in 2.21s**（唯一失败仍是既有 `tests/test_benchmark_migration.py` 的 dev-v1 归档哈希断言）；`uv run casetrace demo` → exit 0。`results/` 五个文件哈希与 4B 结束时逐一相同：`dev-v2-bm25.json 25aca703de92…`、`dev-v2-bm25.cli.txt f159d812375f…`、`pytest-full.log 53c649d3c1b4…`、`README.md c0ee20e8c207…`、`dev-v2-bm25-error-analysis.md 7c522b267530…`。
- 起点核对：HEAD 仍为 `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`；四个 4C 快照哈希与 4A / 4B 记录相符（见 Handoff Baseline），说明本步骤开始时无外部介入改动。
- 改动文件与新哈希：`docs/project/current-plan.md` `99450cdcba7d…` → `d9b4a254402baa2c930ff23242a72f7a73dea03bf171226bfdf2d8e267a1451a`（追加 2026-09-22 交付条目，更新「当前位置」与「下一项交付」）；`docs/project/practical-todo.md` `b59495f1…` → `a552558287eb40f8e9e4a466d7a5a475214d0543c48fe5c5a110a817d896a7ce`（第 5、6 项勾选，顶部「当前位置」，追加 2026-09-22 条目）；`README.md` `6dc41106c871…` → `696a2eef882fce2f185f5a8cf653b19d052c5dce229e2fc440b30761329726bb`（「当前状态」两处改为 M2 交付完毕、待总审）；本包追加本节、4B 用户确认与最终回交清单（本包修改后的哈希不记录自身）。
- 自测：只读脚本 `/tmp/m2-4c-verify-docs.py`（临时文件，未入库）**50 / 50 通过**，核对项包括：四份文档 + `results/` 两份文档的相对链接全部可达（含 `practical-todo.md` 指向 `results/` 的两个链接）；文档中出现的完整 SHA-256 全部能对应到真实文件（或 `HISTORICAL` 中明确标注的历史 / 派生值，如迁移记录里的旧 qrels 哈希与功能 1 调查时的两个内存替换哈希），缩写哈希前缀全部可解析；包内每处 `handoff/additional/<name>` 引用后记录的 SHA-256 与该快照文件的实际哈希一致（本次由此发现并修正了一处记录笔误：`m2-completion.md.pre-m2-feature4c` 实际为 `6d19ad951bf1…`，先前误写成以 `6d19ad95` 开头、少了一位 `1` 的错误前缀）；`practical-todo.md` 第 5、6 项为 `[x]` 且其引用的 `results/` 路径存在；`current-plan.md` 与 `practical-todo.md` 含 `ready for final Codex review` 与「尚未验收」；本包 `Codex Acceptance` 一节仍为「待审核」、Verdict 仍为「待填写 `accepted`、`needs changes` 或 `blocked`」，未填入任何 M2 验收结论（本包正文中 M2-01 的「RR 讲解已验收」与基线里「RR 的已验收记录也保留」属历史记录，不是本阶段验收结论）；文档的「当前状态 / 当前位置」区域不再残留旧表述（本次由此修正两处：文首状态行原写「尚未完成或验收」，以及 4B 一节末尾原写「M2 未完成、未验收」——两处均已改为标 `ready for final Codex review` 并注明状态时点；带日期的历史条目按原文保留，不重写历史）。
- 状态：**ready for final Codex review**。M2 未验收，`Codex Acceptance` 仍留待 Codex 填写；工作止于 M2，不进入 M3。
- 用户确认（2026-09-22）：用户原话「确认 4C，但先不交 Codex；我想自己再核对一遍 results/ 下的结果与分析」。Cline 侧 M2 交付到此收束，标 `ready for final Codex review`；是否以及何时交给 Codex 由用户决定。

## Codex Acceptance

**最终 Verdict：accepted（2026-09-22）**。以下保留首次审核与修复过程，最终两轴结论及交接见本节末尾。

2026-09-22，Codex 单代理总审；按项目适配分别审查 Spec / Standards，包含 M2-02 nDCG。**Verdict：`needs changes`**。本次只写验收记录与 Current Plan 状态，不修改产品代码、测试、数据、结果或原分析。

### Spec findings

1. **[P2] 错误分析将同异常站点误写为完全相同异常。** 位置：`results/dev-v2-bm25-error-analysis.md:31`，同类表述见 `:132`。G001 的 `same_abnormal_process` 只能支持共同工序 P004；C004 的原文是第二焊点颈部断裂、pad 界面保持完整，已确认 Q001–C004 的理由是类似产品 PF_001（`data/evaluation/dev-v2/qrels.json:45`），不能据此称三条都与 Query 的剥离/脱落完全相同。第 132 行还用这“三条”解释 Recall@1，实际分母是全部四个正例。复现：对照上述 qrels 理由、`data/dev/demo.json` 的 C004 原文和分析第 31/132 行；下述 `verify_findings.py` 的 SPEC-1 会输出原文。修订要求：分别陈述症状相符、同工序、类似产品和同产品的证据，阅读期望不从 CaseGroup 自动推导；Recall 分母使用四个已确认正例。保持标签不变。
2. **[P2] BM25 归因忽略词频与长度归一化，结论超出数值证据。** 位置：`results/dev-v2-bm25-error-analysis.md:108`，相关错误见 `:128` 的“所有词项等权”。地板 IDF 为正并不意味着不参与排序：只查“发现”，C001 得分 `0.3014601163971336`、C004 为 `0.21330683183384547`，足以决定两者先后。逐词累加原 Query 的贡献，C001–C002 差值还包含 `线脱` 的 `1.313942675`、`脱落` 的 `0.594418608`；并非仅由 `prod_001` / `力检` 解释，前者在两篇中都命中。复现：下述脚本 SPEC-2 使用实际 `index.get_scores([term])`，按 Query 词频累加，所得总分与原排名一致。修订要求：区分 IDF、文档词频、长度归一化与语义相关性，删除无证据的唯一原因归因，同步更正 Current Plan 第 196 行及包内引用的结论。无需调 BM25 参数。

### Standards findings

1. **[P2] 脏工作区复现清单遗漏实际执行且不同于 HEAD 的源码。** 位置：`src/casetrace/evaluation/runner.py:69` 的 `REPRODUCIBILITY_SOURCE_FILES`；`results/README.md` 第 4/5 节与结果 JSON 继承此缺口。`src/casetrace/__init__.py` 和 `data/{constants,dataset_model,reference,validators}.py` 均有未提交改动且未记录内容哈希。它们虽多为阶段前改动，仍属于本次执行依赖；仅列脏路径不能核对具体版本。违反本包功能 3 与 AGENTS 的可复现/来源可核对要求。复现：下述脚本 STANDARDS-1 在临时目录保留报告已列源码的当前字节，将未列文件还原为报告 HEAD 版本，调用 loader 即失败：`TypeError: Case.__init__() got an unexpected keyword argument 'abnormal_processes'`；仓库文件未改。修订要求：补齐实际运行所需源码的版本指纹及独立覆盖检查，重新生成正式报告并同步产物哈希；保留本次原结果作比较，排名/分数/指标应不变。无需重开冻结数据设计。

### 独立复跑与证据

以下均为 Codex 本次实际执行，在写入验收文档之前完成：

| 命令 | 实测 |
|---|---|
| `uv run pytest -q` | exit 1；277 passed、169 subtests passed、1 failed，2.29s；唯一失败为 `tests/test_benchmark_migration.py:19` 的旧归档哈希断言 |
| `uv run casetrace evaluate --output /tmp/codex-review.json` | exit 0；完整排名、分数及指标与保存结果一致 |
| `uv run casetrace demo` | exit 0 |
| `uv run python /tmp/m2-4c-verify-docs.py` | exit 0；50/50 |
| `uv run python /tmp/m2-4b-verify-doc.py` | exit 0；174/174 |
| `uv run casetrace evaluate --output /tmp/4a-repeat.json && uv run python /tmp/m2-4a-verify.py` | exit 0；37/37；重复报告除 generated_at 外完全相等 |
| `uv run python /tmp/codex-m2-review-j0bpgaob/verify_findings.py` | exit 0；上述三项反例均复现；隔离的 HEAD 重建子进程按预期 exit 1 |

三份辅助脚本的通过数与 Cline 记录一致，但检查范围不覆盖上述语义归因和依赖清单完整性；174/174 不能证明全部分析结论成立。4C 脚本还硬编码“验收待填写”及历史哈希可解析条件，本次写入结论后不再作为当前验收状态检查器，未改脚本让它变绿。

nDCG 已对照原始基线逐行审核，增量为 `math` 导入、新函数和 15 个用例；阶段基线里的指标实现/测试与当前字节相同。全套复跑已包含全部 54 个指标用例（39 既有 + 15 个 nDCG），唯一失败在迁移测试；本次未发现 nDCG 的 Spec / Standards 缺陷，不要求重新交付该函数。

### 基线、已知问题与比较限制

- 当前 HEAD 与两份 `head.txt` 一致：`1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87`。阶段 manifest 46 条、nDCG manifest 13 条，所有标为存在的快照均通过自身 SHA-256 校验。阶段现有文件内容变化为 README、Current Plan、practical-todo、本包、CLI、demo 六项；完整 git 状态相对阶段起点新增 10 个路径，与回交清单一致，无移除。demo 净增量为公共读取/校验抽取，未将早先异常站点改动归入本次。
- 阶段基线中的活动数据、qrels、BM25、已有测试及依赖文件与当前一致；追加快照引用哈希由 4C 脚本复核。nDCG 原基线对其他早先脏文件未全部保存内容，因此保留 M2-02 已披露的历史比较限制；不能用后来的阶段快照补称早期所有文件均未改动。
- 旧 dev-v1 qrels：当前与阶段基线同为 `e92e5bb1f84d0e69b3a05753664b57b689bf330059c6a11cf1ccd4194e9fe933`，预期仍为 `c0175226433332e1ac592e0850248fe7bd4dbde9173d3c8f0773c2d1602a245e`。确认是继承问题，未修复；不把它算成本次新增缺陷，不刷新哈希或猜测原件。当前 v2 的来源核对与旧版迁移溯源分别报告。
- `results/dev-v2-bm25.json` 权限实测为 600，与回报一致。本地当前用户可读，任务无跨用户读取要求，**不作为验收阻塞项**，本次未 chmod。
- 结果中已列的七项源码/配置哈希全部匹配当前文件；问题是清单不完整，而非记录值漂移。
- 本次文档编辑前快照、manifest、HEAD、git 状态、辅助脚本副本与缺陷复现脚本/输出保存在 `/tmp/codex-m2-review-j0bpgaob`；原两套基线继续保留。临时目录不保证长期存续，关键发现及数值已写入本包。

### Verdict、下一步与学习状态

- **Spec：needs changes（2 项）；Standards：needs changes（1 项）；总 Verdict：needs changes。** 待上述分析和复现记录修订后，沿用本包进行针对性复核；不新增指标或检索实验，不进入 M3。
- 下一交付限定为三项修订：纠正相关依据及 BM25 归因；补齐执行源码指纹并用独立预期检查覆盖范围；重跑 evaluate 与相关测试、同步结果及文档哈希后回交。全套检查继续原样报告旧归档失败，不通过删除/弱化断言消除它。
- 用户学习状态沿用 Cline 原始确认：2A/2B、2C、4A/4B 的“基本理解”及 4C 确认；nDCG 用户表示本步完成。Codex 没有重放教学，也不将代码审核等同于用户理解；本次两项分析纠正尚未讲解确认。
- Current Plan 已记录本次总审与 M2 修订边界。未提交、推送、部署，未启动子代理。

### 2026-09-22 复现清单修复与现有 M2 debug 复核（Codex）

**授权与必要性：** 用户要求确认必要性后实施，并以现有实现的 debug 审查为主，不新增功能。功能 3 明确要求未提交源码版本可核对；已有缺陷可复现，因此只补清单及一个回归测试。沿用本包，无新任务、依赖、仓库文件或检索实验。

**本轮基线：** `/tmp/casetrace-m2-repro-fix-fbr57lij/before/` 保存编辑前相关源码、测试、数据、结果及两份计划文档，`manifest.json` 记录存在状态与哈希，HEAD / git-status / staged.patch / unstaged.patch 均已保存。原两套阶段基线继续保留。用户既有改动：Q001–C004 rationale 增加“描述均为焊线相关异常，可能存在关联性。此外”，本轮接手时已在 qrels；其余字段和 18 对标签未改变。分析文档接手时仍是此前的 `7c522b267530…`，所以不能将用户更新误记成分析文字已修好。

**实际修复：** `runner.py` 的 `REPRODUCIBILITY_SOURCE_FILES` 从 7 项扩为 12 项，补 CLI 和 `data/constants.py`、`dataset_model.py`、`reference.py`、`validators.py`；这些文件实现未改。`test_runner.py` 新增独立要求这五项存在且哈希正确的回归测试，不从生产清单生成期望。根因已由此前隔离重建确定，本轮不重复多假设探索；先实测该用例失败，再补清单，相关 runner/CLI 测试 29 passed。

**验证与文件衔接：**

- 全套 `uv run pytest -q`：278 passed、169 subtests passed、1 failed in 2.32s；唯一失败仍为 `tests/test_benchmark_migration.py:19` 旧归档哈希。日志已同步到 `results/pytest-full.log`，未修改/删除失败测试。
- 正式 evaluate 与 demo 均 exit 0；正式报告及 CLI 输出重新生成。修复前后逐 Query 排名、原始分数、命中词项、指标及汇总完全相同。与旧报告相比，除时间、源码指纹外，qrels 哈希也变化，原因是上述用户既有 rationale 修改；未将其错误归因于清单补齐。
- 同一固定输入重复运行报告除 generated_at 外完全相等；本轮两次时间戳恰好相同，属于秒级精度的正常情况，因此未用“时间戳必须不同”作为通过条件。
- 临时目录 `reconstruction/` 从 HEAD 源码加报告清单覆盖重建，复制已校验输入，独立进程执行 CLI evaluate exit 0；benchmark / retrieval / metrics / queries / summary 与正式结果一致。日志为 `reconstruction.log`，对比结论为 `integration-summary.txt`。已核对实际加载的非空 CaseTrace Python 模块均在清单中。
- 报告 12 项源码/配置指纹、输入实际哈希、results README 的产物/源码表、分析引用的报告哈希均一致；分析只替换结果哈希，正文未改。`uv run python /tmp/m2-4b-verify-doc.py` 本轮为 174/174，数值通过仍不代表文字结论通过。
- 按原包复核 benchmark 校验 → 文档构建/防泄漏 → 全排名 → 四指标/None 汇总 → CLI 保存这条现有调用链，并用全套测试及隔离 CLI 实测交叉验证；未发现新的重大运行漏洞或本轮引入的文件衔接缺陷。此结论限于本轮范围，不证明所有环境或未来代码均无 bug。
- Current Plan 第 4 节曾残留“MRR 尚未实现 / nDCG 待总审”，已按实际状态更正。带日期的历史回报不改写；results README 明确当前分析仍待修订。

**两轴结论：** Standards 的源码清单 finding 已修复并验证关闭；Spec 两项分析 finding 仍在当前磁盘正文中，位置为 `results/dev-v2-bm25-error-analysis.md:31/:132` 及 `:108/:128`，复现依据沿用上节。新增 qrels 理由说明“可能存在关联性”，不能推导 C004 与 Query 完全相同。M2 总 Verdict 仍为 **needs changes**；剩余工作是纠正这两处解释，无须调整算法或重做标签。通用词优化仍属于 M3 实验，本轮不开始。

**学习与收尾：** 本次已解释 CLI、数据模块、哈希与存档的区别，未替用户宣称已理解；原学习确认保留。旧 dev-v1 溯源差异与权限 600 的判断不变。无 Git 暂存/提交/推送，Git 状态路径集合与本轮起点一致；仅已有文件内容更新。下一步仍停留在 M2 的待修订分析与复核。

本次正式报告 SHA-256：`bc457e9576ece6ad29cb2d3991da7c69e939bb4c5a2d0b7330c6039c8441f26d`；qrels 实际 SHA-256：`9112d64cac25e8af0b7b183ca0d083de2c460dc6427cf1c57785f4e0fdfc38b7`。

### 2026-09-22 最终验收与交接

- **Spec findings：已关闭。** 对照当前分析正文，已按用户明确判断写明 C001 完全相同、C003/C004 相关且 C003 更接近；Recall 分母为四个已确认正例。已纠正通用词不参与排序、所有词等权及仅用两个词解释分差的表述。排名、指标表及二值标签未因文字修订改变。
- **Standards findings：已关闭。** 源码清单补齐及回归验证见上节。nDCG 原基线已纳入审核，无未完成的单函数验收要求。
- **验证证据：** 最近一次代码修订后完整测试为 278 passed、169 subtests passed、1 failed；唯一失败为旧 dev-v1 归档哈希。相关 runner/CLI 测试 29 passed；evaluate、demo 及隔离重建 CLI 已成功，排名/分数/指标一致。本次仅作文本与交接收尾，复核现有源码/输入哈希仍匹配正式报告、分析改文及文档链接；未无故重跑全套测试，未声称失败已消失。
- **历史限制：** 用户确认后续以现有 dev-v2 继续，旧归档问题不阻塞收尾；原因线索与处理决定统一记录在 [dev-v2 迁移记录](../../../data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)。保留失败测试与旧哈希，不称迁移校验通过。结果权限 600 对当前本地使用非阻塞。
- **Verdict：accepted。** M2 功能、结果、错误分析与本轮必要修订已收尾，无待交付 M2 功能；验收不表示检索泛化质量已达标。
- **学习状态：** 保留此前逐步理解确认。用户已明确案例接近程度，并要求纠正两处文字；CLI/数据模块/哈希的解释已交付。不将本次代码验收视为对所有概念掌握程度的额外认证。
- **下一窗口：** 先读 Current Plan，再按需查本包最终结论、results README 和已纠正的错误分析；由 Codex 规划 M3 第一个小交付，再实施。沿用当前 dev-v2 benchmark 和指标口径，逐步比较 BM25 / Embedding / Hybrid / Rerank；不重新要求确认已确认标签，不将历史 dev-v1 恢复列为前置，不将阅读意见自动变为分级标签。本轮没有创建 M3 实施包或启动实验。
- 文档收尾前快照：`/tmp/casetrace-m2-closeout-gcqwg9_j`。仅修改既有 Markdown 记录及入口；无 Git 暂存、提交、推送或部署。原阶段基线保留。
