# M3-01 — 多方法评估入口

创建：2026-09-22。状态：当前交接包，待 Cline 接手；尚未实施。

## Codex Plan

**执行入口：** 先读 [Current Plan](../current-plan.md) 确认活动包，再按 [AGENTS 的 M3 工作流](../../../AGENTS.md#m3-delivery-workflow--user-confirmed-override) 执行。下列要求是本包边界，不是替 Cline 预排的子交付；由 Cline 在 Report 中安排最多 5 个子交付，每次只推进当前一步。

**目标与范围：** 在现有 dev-v2 上把评估器与 BM25 的具体实现适度分开，支持方法选择及各方法自己的元数据；本包只接入现有 BM25。继续复用输入校验、指标、汇总和原子保存，不构建插件框架。

**任务来源与阅读：** [Current Plan](../current-plan.md) 第 4、5 节、[M2 最终交接](m2-completion.md#2026-09-22-最终验收与交接)、[运行记录](../../../results/README.md)；按需读 [runner](../../../src/casetrace/evaluation/runner.py)、[BM25](../../../src/casetrace/retrieval/bm25.py)、[CLI](../../../src/casetrace/__init__.py) 及对应测试。

**输入 → 输出：** 已确认 dev-v2、现有 BM25 实现及正式报告 → 可接入其他方法的评估入口、方法与耗时元数据、独立保存的 BM25 回归结果。

**必须保留的行为：**

- 检索仍消费 Case ID → 历史文本和 Query 文本，返回有效、唯一的 Case ID 与分数；标签和理由只参与计分。最小公共接口沿用 `search(query, *, top_k)`，具体类型由 Cline 根据现有代码选择。
- 默认方法为 BM25；CLI 增加 `--method bm25`，未知或尚未实现的方法明确报错，不偷偷回退。未指定参数的既有 CLI 和 `run_evaluation` 调用继续有效。
- runner 和报告层不再必须访问 BM25 的 `index` 才能工作；BM25 的命中词项和参数仍保留，其他方法允许没有词项信息。用测试替身验证入口可接入第二种返回，无需预写 Embedding。
- 记录索引构建和逐 Query 检索耗时及测量边界；耗时和生成时间不参与确定性结果比较。保留数据、指标、实际执行源码与依赖版本追溯；结果格式变动应明确记录，不覆写 M2 原报告。
- 指标口径、语料、Query、qrels、分词与 BM25 参数不变；dev-v2 的排名、分数、逐 Query 指标和汇总与原报告一致。demo 保持可用。

**实现边界：** 主要涉及 runner、CLI、必要的最小公共检索类型、对应测试和运行说明；复用当前来源加载路径，不重写数据基础，不接入模型或新服务。

**用户亲手部分（预留）：** 建议由用户在现有 CLI 中加入方法选项并传入评估入口。目标是默认仍可运行、显式 BM25 等价、未知值被拒绝；Cline 在接口就绪后指出修改位置、参数契约和必要提示，留实现给用户，再检查行为。若实际拆分更适合另一个同等大小的代码片段，在 Report 记录替换原因。

**测试边界与命令：** 使用可控检索替身验证方法切换、排名 ID 守卫及防标签泄漏；验证默认/显式 BM25 一致、错误方法不写半份报告、方法元数据与执行一致。运行 `uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py tests/test_demo.py` 及新增类型相关测试；实际运行 `uv run casetrace demo`、`uv run casetrace evaluate --method bm25 --output <本包独立结果路径>`，与 M2 的事实字段比较。尖括号路径由 Cline 换成真实路径并记录。命令为计划，尚未执行。

**验收与教学停止点：** 公共入口可替换、BM25 回归一致、来源与耗时可核对、用户代码已检查。讲清“换检索方法，继续用同一套计分”的调用链和原始分数并非概率；完成本包回交，不提前讲解或实现 Embedding。

**使用 skills：** Cline 按需读取 [implement](../../../.agents/skills/implement/SKILL.md)、[teach](../../../.agents/skills/teach/SKILL.md)，纯逻辑与回归测试采用 [tdd](../../../.agents/skills/tdd/SKILL.md)；均按 AGENTS 项目适配。Codex 回交时用 [code-review](../../../.agents/skills/code-review/SKILL.md) 分开审阅 Spec / Standards，默认单 agent。

## Handoff Baseline

- 起始 HEAD：`b8aaea4151b74d4b2bf80255a5cc22b5105a7205`。
- 基线目录：`/tmp/casetrace-m3-packages-ozbqut0a`；`preparation/` 为成包前内容，**Cline 对照成包后的 `handoff/`**。manifest 记录文件哈希和缺失目标，files 保存原字节，head / git-status / staged.patch / unstaged.patch 保存版本及已有改动；保留至验收。
- 成包前已有未暂存改动仅为 `docs/project/current-plan.md`（本会话上一轮 M3 规划）；七份 M3 包原先不存在。成包后的文档修改和新文件属于 Codex 规划，不归因于 Cline，完整状态见 handoff。
- Cline 编辑前核对当前内容与 handoff，记录介入修改；对新增或首次涉及文件追加编辑前快照、标记缺失目标。基线缺失时报告比较限制并重建，不用提交伪造基线。
- 历史证据见 M2 最终交接：278 passed、169 subtests passed、1 failed（旧 dev-v1 归档）；本轮只写文档，未复跑软件测试。
- **Cline 介入核对（2026-09-22，SD1 开始前）：** 与 `handoff/files/` 逐字节比较，`src/casetrace/retrieval/bm25.py`、`src/casetrace/evaluation/runner.py`、`src/casetrace/__init__.py`、`tests/evaluation/test_runner.py`、`tests/test_cli_evaluate.py` 全部 MATCH_HANDOFF；`src/casetrace/retrieval/base.py` 记录为缺失目标。编辑前快照 `/tmp/casetrace-m3-01-cline-1790069062/before/`（另含 `tests/retrieval/test_bm25.py`、`docs/project/*`、`results/README.md`）；接手期间无他人代码改动。

## Cline Report

状态：**SD1–SD4 全部完成并自测**（SD3 由用户亲手实现 CLI `--method`，SD4 由 Cline 实现耗时记录与独立回归结果），本包交付完毕，**标 ready for acceptance**；等用户确认后回交 Codex 验收，未进入 M3-02。

| 子交付 | 目标与产物 | Cline / 用户负责的代码 | 检查与教学停止点 | 实际状态 |
|---|---|---|---|---|
| SD1 公共检索契约 | 新增 `src/casetrace/retrieval/base.py`（`SearchHit` / `Retriever` / 契约说明）；`bm25.py` 复用 `SearchHit` 并新增 `describe()`；报告层改用 `describe()`、不再读 `retriever.index`；行为与 M2 报告字段不变 | Cline 全部实现；用户本步只听取讲解 | `uv run pytest -q tests/retrieval/test_bm25.py tests/evaluation/test_runner.py tests/test_demo.py` 全绿 | 已自测（53 passed）；讲解已发出，等用户确认 |
| SD2 方法选择入口 | `runner.py` 增加 `RETRIEVER_FACTORIES` + `DEFAULT_METHOD`、`build_retriever(..., method=)`、`run_evaluation(..., method=)`；未知方法明确报错且不写半份报告；用替身注册第二方法 | Cline 实现与测试；用户无代码 | 默认与显式 bm25 结果一致；未知方法 exit 2 且不留文件；替身方法（无词项）可跑通 | 已自测（138 passed / 全套 286 passed、1 failed 旧归档）；用户表示「数据链路懂了」后进入 SD3 |
| SD3 CLI `--method`（用户亲手） | `evaluate` 子命令增加 `--method` 并透传给 `run_evaluation`；终端头部显示方法名 | 用户：`add_argument` 与传参；Cline：先给参数契约与提示，再补 CLI 测试与打印行，最后检查行为 | 不写参数等价现状；`--method bm25` 与默认一致；未知值报错且不留文件 | 已完成并自测（用户代码经复核通过：默认/显式一致、未知方法 exit 2 且不留文件）；等用户确认后进入 SD4 |
| SD4 耗时与独立回归结果 | 顶层 `timing` 文档与测量边界说明；独立结果文件（不覆写 `results/dev-v2-bm25.json`）；`results/README.md` 记录格式变动与对照结论 | Cline 实现、正式运行与 M2 事实字段对照 | `uv run pytest -q`（旧归档 1 failed 保留）、`uv run casetrace demo`、新旧报告逐字段对照 | 已完成并自测（全套 289 passed、1 failed 旧归档；独立产物 14,741 B，与 M2 面板字段全部一致）；等用户确认后回交验收 |

**文件级改动（实施计划）**

| 文件 | 子交付 | 改动部位 |
|---|---|---|
| `src/casetrace/retrieval/base.py` | SD1 | 新增：`SearchHit`（`matched_terms` 允许 `None`）、`Retriever` Protocol（`search` / `describe`）与契约说明 |
| `src/casetrace/retrieval/bm25.py` | SD1 | 删除本地 `SearchHit` 定义，改为从 `base` 导入并继续导出；新增 `describe()`，读数取自 `self.index` |
| `src/casetrace/evaluation/runner.py` | SD1 | `RankedCase.matched_terms` 允许 `None`；`build_retriever` / `rank_query` / `evaluate_query` 改用公共 `Retriever` 类型；`_retrieval_document` 改用 `describe()` 并补 `document_builder` / `corpus_size` / `requested_top_k`；`REPRODUCIBILITY_SOURCE_FILES` 增加 `base.py` |
| `src/casetrace/evaluation/runner.py` | SD2 | `RETRIEVER_FACTORIES`、`DEFAULT_METHOD`、`build_retriever(..., method=)`、`run_evaluation(..., method=)`、未知方法报错 |
| `src/casetrace/__init__.py` | SD3 | `evaluate` 增加 `--method`（用户实现）与透传；终端头部显示方法名 |
| `src/casetrace/evaluation/runner.py` | SD4 | `time.perf_counter()` 计时与顶层 `timing` 文档；`RESULT_SCHEMA_VERSION` 升为 `evaluation-result-v2` |
| `tests/retrieval/test_bm25.py` | SD1 | `describe()` 读数与 `SearchHit` 默认值回归 |
| `tests/evaluation/test_runner.py` | SD1/SD2/SD4 | 报告字段与方法元数据、方法选择、替身第二方法、timing；两处确定性比较改为剔除 `generated_at` 与 `timing` |
| `tests/test_cli_evaluate.py` | SD3/SD4 | 默认与显式 `--method` 一致、未知方法 exit 2 且不留文件 |
| `results/dev-v2-bm25-m3-01.json`（新增） | SD4 | 本包独立回归结果，不覆写 M2 的 `results/dev-v2-bm25.json` |
| `results/README.md` | SD4 | 命令、新文件哈希、格式变动与 M2 事实字段对照 |

**数据流（M3-01 完成后）**：`qrels + dataset + 主数据 → load_benchmark（校验与哈希绑定）→ build_documents（只拼历史记录）→ RETRIEVER_FACTORIES[method](documents) → 逐 Query search → rank_query（ID 守卫）→ evaluate_query（qrels 只在此步进场计分）→ aggregate → report{benchmark, retrieval, timing, metrics, queries, summary, reproducibility} → write_report（原子落盘）`。

**已与用户确认的技术决定（2026-09-22）**：schema 升为 `evaluation-result-v2`；新结果文件用 `results/dev-v2-bm25-m3-01.json`；`describe()` 保留 `"method": "bm25_okapi"` 字样；用户亲手代码为 CLI `--method`（SD3）。注册表与默认方法常量放在 `runner.py`（组合根），避免 `base.py` 反向导入 `bm25.py` 产生循环导入。

- **完成内容（SD1）：** 新增 [base.py](../../../src/casetrace/retrieval/base.py)（`SearchHit` / `Retriever` / 契约说明）；[bm25.py](../../../src/casetrace/retrieval/bm25.py) 删除本地 `SearchHit` 定义、改为从 `base` 导入并继续导出，新增 `describe()`；[runner.py](../../../src/casetrace/evaluation/runner.py) 的 `RankedCase.matched_terms` 允许 `None`、`build_retriever` / `rank_query` / `evaluate_query` 改用公共 `Retriever`、`_retrieval_document` 改为 `retriever.describe()` 合并评估器自有字段、`REPRODUCIBILITY_SOURCE_FILES` 增加 `base.py`；`tests/retrieval/test_bm25.py` 与 `tests/evaluation/test_runner.py` 增加契约与默认值回归。未改指标函数、benchmark loader、`demo.py`、qrels、分词与 BM25 参数，未接入其他检索方法。范围无偏差；唯一提前动作是把 `base.py` 加入复现源码清单（它已进入执行链，M2 曾因清单漏项被审出问题）。
- **关键实现（SD1）：** 输入输出：`search(query, *, top_k) -> list[SearchHit]`、`describe() -> dict`，`SearchHit.matched_terms` 默认 `None` 表示该方法不提供词项。调用关系：`run_evaluation → build_retriever(benchmark) → build_documents → BM25Retriever`；`rank_query → retriever.search`；报告层只读 `describe()`。取舍：`SearchHit` 迁到 `base` 但 `bm25` 继续导出，现有导入路径不变；`describe()` 只声明方法自身元数据，`document_builder` / `corpus_size` / `requested_top_k` 仍由评估器补充，因此 M2 报告字段值完全不变。
- **完成内容（SD2）：** [runner.py](../../../src/casetrace/evaluation/runner.py) 增加 `from collections.abc import Callable`（L10）、注册表与默认常量（L138-143：`DEFAULT_METHOD = "bm25"`、`RETRIEVER_FACTORIES = {"bm25": BM25Retriever}`）、`build_retriever(benchmark, *, method=DEFAULT_METHOD)`（L146-161：先查注册表，未知方法报错并列出可用方法，再建文档并保留语料一致性校验）、`run_evaluation(qrels_path, *, base_dir=None, method=DEFAULT_METHOD)`（L377-387）；`tests/evaluation/test_runner.py` 新增 4 个用例（默认 == 显式默认、未知方法在构建前报错、替身第二方法可注册并跑通、注册表只含正式方法）。未改 CLI（`--method` 属 SD3，由用户实现）、指标函数、报告字段与 BM25 实现。
- **关键实现（SD2）：** 方法选择由一个 dict 完成：`build_retriever` 用 `RETRIEVER_FACTORIES.get(method)` 取构造函数，取不到就 `ValueError("未实现的检索方法：'x'；当前可用：bm25")`，**在校验方法名之后才构建文档**，因此不会静默回退，也没有任何半份结果。报告记录的 `retrieval.method` 仍是**实际执行那个方法** `describe()` 的自报值（测试用替身方法验证），不是写死的常量。用户可见入口（CLI `--method`）留给 SD3。
- **用户亲手代码与检查（SD3，已复核通过）：** 由用户独立完成 [__init__.py](../../../src/casetrace/__init__.py) 的 `evaluate.add_argument("--method", ...)` 与 `run_evaluation(args.qrels, method=args.method)`。第一版出现两处缺陷，均由用户自行修正：(1) `default=bm25` 未加引号，取到的是当时导入的**模块对象**而非字符串（Cline 给出 `type(bm25) == module`、`repr("bm25") == 'bm25'` 的实测证据）；(2) 只声明参数、未传参，导致 `--method embedding` 也 exit 0 并写出 bm25 报告，即"静默忽略用户输入"，违反本包"不偷偷回退"的要求；Cline 用"`--method embedding` 必须报错"这一条对照指出缺失传参，用户修正后三条判据全过。Cline 复核时只做格式统一（补逗号空格、去掉冗余 `type=str`、删多余空行、help 文案改为"检索方法名；默认 bm25，可用方法以 runner 的 RETRIEVER_FACTORIES 为准"），未改动用户的两处逻辑。
- **测试结果（SD1）：** `uv run pytest -q tests/retrieval/test_bm25.py tests/evaluation/test_runner.py tests/test_demo.py tests/test_cli_evaluate.py` → **53 passed in 1.00s**（含新增 4 个用例）。过程中一次失败是我方测试期望写错（`recall@1` 写成 1.0，Q001 有 4 个正例、实际 0.25），按已确认口径改为 0.25 后通过，非产品代码缺陷。`uv run pytest -q` 全套 → **282 passed、169 subtests passed、1 failed in 2.31s**，唯一失败仍是既有 `tests/test_benchmark_migration.py` 的旧 dev-v1 归档哈希断言（`e92e5bb1…` vs 记录 `c017522643…`），与 SD1 无关；通过数由 278 增至 282 即本次新增的 4 个用例。`uv run casetrace evaluate --output /tmp/m3-01-sd1-report.json` → exit 0；`uv run casetrace demo` → exit 0（C001 第 1 名、排名与匹配词未变）。只读对照 M2 正式结果：`schema_version` / `benchmark` / `retrieval` / `metrics` / `queries` / `summary` 全部 `identical=True`；`retrieval` 仅键顺序变化（不表语义），`reproducibility.source_files` 由 12 项增至 13 项并包含 `base.py`。未跑：M3 其他实验（Embedding / Hybrid / Rerank），也未改任何结果文件。
- **遗留问题（SD1）：** 无阻塞。`results/dev-v2-bm25.json` 权限 600 与旧 dev-v1 归档哈希仍按历史限制保留，本包不处理。
- **测试结果（SD2）：** `uv run pytest -q tests/evaluation tests/retrieval tests/test_cli_evaluate.py tests/test_demo.py` → **138 passed in 1.47s**；`uv run pytest -q` 全套 → **286 passed、169 subtests passed、1 failed in 2.47s**（唯一失败仍是旧 dev-v1 归档哈希断言，与 SD2 无关；通过数 282 → 286 即本次新增 4 个用例）。`uv run casetrace evaluate --output /tmp/m3-01-sd2-report.json` → exit 0，与 M2 正式结果对照 `schema_version` / `benchmark` / `retrieval` / `metrics` / `queries` / `summary` 全部 `identical=True`。程序化验证：`DEFAULT_METHOD = bm25`、注册表 `['bm25']`、`method="embedding"` → `未实现的检索方法：'embedding'；当前可用：bm25`。过程中一次失败为我方测试设计错误（在 `monkeypatch.setitem` 生效期间断言"注册表只有 bm25"），拆为独立用例 `test_registry_ships_only_real_methods` 后通过，非产品代码缺陷。未跑：CLI 层 `--method` 检查（SD3 实现后）、耗时（SD4）。
- **遗留问题（SD2）：** 无阻塞。已知取舍：报告记录的是方法自报的 `retrieval.method`（如 `bm25_okapi`），注册表名（如 `bm25`）不额外写入报告；如需按注册表名核对方法配置，可在 SD4 或 M3-07 需要时再加字段，本步不加。
- **完成内容（SD3）：** 用户实现 [__init__.py](../../../src/casetrace/__init__.py) L26-27（`evaluate.add_argument("--method", default="bm25", help=…)`）与 L36（`run_evaluation(args.qrels, method=args.method)`）；Cline 补 L43-45 终端头部"检索方法：方法自报名；语料 N 条；结果已写入 …"（取 `report["retrieval"]["method"]`，实测 `bm25_okapi`），并在 `tests/test_cli_evaluate.py` 新增 2 个用例：`test_evaluate_explicit_bm25_matches_default`（显式与省略参数除 `generated_at` 外一致、终端显示的方法名等于报告记录的方法名）、`test_evaluate_rejects_unknown_method_without_writing_a_report`（exit 2、stderr 含"未实现的检索方法"与 `embedding`、目录内无任何文件）；模块 docstring 同步提及方法选择。未改 `runner.py`、指标函数、报告字段、BM25 实现、qrels 与 demo 行为。
- **关键实现（SD3）：** 用户可见入口只做两件事——声明参数、把值以**关键字**形式交给 `run_evaluation`（`method` 在 `*` 之后，只能关键字传）。方法合法性、报错文本与"不写半份结果"仍由 runner 的注册表负责：`RETRIEVER_FACTORIES.get(method)` 取不到即 `ValueError` → CLI 既有 `except (OSError, ValueError, …)` → `parser.error` → exit 2，而 `write_report` 尚未执行。因此 CLI 里没有任何方法名判断、没有 `choices=` 白名单，接入第二个方法不需要改 CLI。报告与终端显示的都是方法自报名（`bm25_okapi`），与命令行输入的注册表名（`bm25`）属于不同层次，二者不需要对齐。
- **测试结果（SD3）：** `uv run pytest -q tests/test_cli_evaluate.py tests/evaluation/test_runner.py tests/test_demo.py tests/retrieval/test_bm25.py` → **59 passed in 1.02s**（较 SD2 的 57 增加本次 2 个用例）。`uv run pytest -q` 全套 → **288 passed、169 subtests passed、1 failed in 2.46s**（唯一失败仍是既有 `tests/test_benchmark_migration.py` 的旧 dev-v1 归档哈希断言，与 SD3 无关；通过数 286 → 288 即本次新增 2 个用例）。CLI 实测：`uv run casetrace evaluate --output /tmp/m3-01-sd3-default.json` → exit 0，输出第 2 行为 `检索方法：bm25_okapi；语料 6 条；结果已写入 …`；`--method bm25 --output /tmp/m3-01-sd3-report.json` → exit 0，与默认运行除 `generated_at` 外完全一致，且与 M2 正式结果 `results/dev-v2-bm25.json` 逐节对照 `schema_version` / `benchmark` / `retrieval` / `metrics` / `queries` / `summary` **全部 `True`**；`--method embedding --output /tmp/m3-01-sd3-nope.json` → **exit 2**、stderr 为 `casetrace: error: 未实现的检索方法：'embedding'；当前可用：bm25`、目标文件不存在、目录内无残留；`uv run casetrace evaluate --help` 显示新增的 `--method METHOD` 与 help 文案；`uv run casetrace demo` → exit 0。未跑：耗时与独立结果文件（SD4）、Embedding / Hybrid / Rerank 实验。
- **遗留问题（SD3）：** 无阻塞。已知取舍三项：(1) CLI 默认方法写作字面值 `"bm25"`，与 runner 的 `DEFAULT_METHOD` 是两份值；本次保留用户写法不改（行为正确，help 文案已指向注册表），如需单一来源可在 SD4 或 M3-07 统一。(2) 两处用户可见文案仍写死 BM25（子命令 help「在已确认的 benchmark 上评估 BM25 检索」、结尾提示「BM25 分数不是相关概率」），在接入第二方法前依然成立，M3-02 需改为方法中立表述，本步未改。(3) [practical-todo.md](../practical-todo.md) 的 M3 入口描述仍是成包前版本（写"尚未创建 M3 实施包"），已过时，按 M3 工作流由 Codex 验收后随 Current Plan 一起刷新，本步未改。
- **完成内容（SD4）：** [runner.py](../../../src/casetrace/evaluation/runner.py) 增加 `from time import perf_counter`（L22）、`RESULT_SCHEMA_VERSION` 升为 `evaluation-result-v2`（L56-57，注释写明 v2 = v1 + 顶层 `timing`）、`TIMING_BOUNDARIES` / `TIMING_COMPARISON_NOTE`（L73-84）、`_timing_document`（L358-380），并把 `run_evaluation` 改为带计时地逐 Query 计分、把 `timing` 放在 `retrieval` 之后（L427-448）；`tests/evaluation/test_runner.py` 新增 `_without_run_metadata`，两处确定性比较同时剔除 `generated_at` 与 `timing`，新增 `test_report_timing_records_boundaries_and_stays_out_of_scores`；`tests/test_cli_evaluate.py` 的 `_drop_timestamp` 改名为 `_drop_run_metadata` 并同样剔除 `timing`（不改会因耗时不同而误报不一致）；新增本包独立产物 `results/dev-v2-bm25-m3-01.json`；`results/README.md` 增加第 8 节并修正第 5 节的复现警告。未改指标函数、benchmark loader、检索实现、qrels、标签与 BM25 参数。
- **关键实现（SD4）：** 计时只用 `time.perf_counter`（单调时钟），三个数值各有明确边界并写进报告自身的 `boundaries`：`index_build_seconds` 只包 `build_retriever`（历史文本构建 + 建索引）；`per_query[].seconds` 包该 Query 的 `evaluate_query`（检索 + 返回 ID 守卫 + 指标计算，qrels 仍只在此步进场）；`total_seconds` 从进入 `run_evaluation` 计到 `aggregate` 完成。报告同时写入 `comparison_note`，明确"耗时与 `generated_at` 不参与确定性比较"、单次读数不足以评价效率。确定性比较改为剔除这两个字段后，本包其余字段仍逐字段可比；测试另加一条守卫，禁止耗时类键值漏进 `metrics` / `queries` / `summary`。
- **测试结果（SD4）：** `uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py tests/retrieval/test_bm25.py tests/test_demo.py` → **60 passed in 1.14s**（较 SD3 的 59 增加本次 1 个耗时用例）；`uv run pytest -q` 全套 → **289 passed、169 subtests passed、1 failed in 2.53s**（唯一失败仍是既有 `tests/test_benchmark_migration.py:19` 旧 dev-v1 归档哈希断言；通过数 288 → 289）。正式运行：`uv run casetrace evaluate --method bm25 --output results/dev-v2-bm25-m3-01.json` → exit 0，终端首行含 `检索方法：bm25_okapi`，产物 14,741 B、SHA-256 `013738a2d238ecdb01aa0e57295799009ef1160af4f9b3f8236cd6b495f10108`；只读对照 M2 正式结果：`benchmark` / `retrieval` / `metrics` / `queries` / `summary` **全部一致**，schema 由 v1 升为 v2，顶层键只有新增 `timing`，`source_files` 如实变化（新增 `base.py`，`__init__.py` / `runner.py` / `bm25.py` 随本包实现更新）。`uv run casetrace demo` → exit 0。重复运行实测：两次运行的差异**只有** `generated_at`、`timing.*` 与 `reproducibility.git_status_paths`（第 2 次多出 `results/dev-v2-bm25-m3-01.json`，因该产物在第 1 次运行时尚未写入），排名、分数、指标与汇总完全一致。本次读数（观测值）：`index_build 0.00195 s`、逐 Query `0.00037 / 0.00026 / 0.00022 s`、`total 0.02311 s`。未跑：Embedding / Hybrid / Rerank（M3-02 起）、Locked Test（M6）。
- **遗留问题（SD4）：** 无阻塞。(1) 新产物权限仍为 600（`write_report` 用临时文件创建所致），与 M2 属同一已知观察，本轮未改代码。(2) `results/README.md` 第 5 节原命令会覆写 M2 的 v1 产物，已在该节加注意并在第 8 节给出当前正确路径；按字节复现 M2 文件须使用第 4 节记录的源码版本。(3) 本包未设耗时阈值或跨方法耗时对比，M3-02 起才在不同方法间比较，届时沿用同一 `boundaries` 口径并注明硬件与冷启动条件。
- **教学状态（SD1–SD4）：** 已讲并确认：契约三要素、`Protocol` 的作用（没有运行时强制，作用是接口声明）、`describe()` 与评估器的职责分工、词项允许缺失。SD2 部分已讲：查表分发（名字层 → 对象层）与"先校验后构建"，用户 2026-09-22 表示「数据链路懂了」。SD3 已讲：`add_argument` 做什么（造"格子"、`--method` → `args.method`、`default` / `help` / `type` 各自作用，用最小 argparse 实测对照）、为什么必须关键字传参、退出码 2 的含义与出处（argparse 源码里写死的 `self.exit(2, …)`，用户在 `except` 里调用 `parser.error`）、以及"命令能跑"不等于"参数生效"（要用被忽略就会露馅的值验证）。SD4 已讲（待用户确认）：为什么用 `perf_counter` 而不是墙上时钟、为什么"测量边界"比数字本身重要、为什么耗时与生成时间不能参与确定性比较（用两次运行实测：只有 `timing.*` 与 `generated_at` 变，面板字段全等）。待讲（按需）：替身方法如何证明入口可替换（SD2 遗留）。
- **基线核对及接手间变化：** 见 Handoff Baseline 的「Cline 介入核对」；接手时工作区只有 M3 规划类文档改动，无他人代码改动。SD2 只改 `runner.py` 与 `tests/evaluation/test_runner.py`，均在快照覆盖范围内。SD3 编辑前追加快照 `/tmp/casetrace-m3-01-sd3-cline-1790095825/before/`（`src/casetrace/__init__.py` `42e6afddfe697845…`、`tests/test_cli_evaluate.py` `33aec84fa7f394f2…`（与 M2 记录一致）、`docs/project/tasks/m3-01-evaluation-entry.md` `b4851e034b45ad02…`）；该时点 `__init__.py` 已含用户对 `--method` 的修改，已按用户代码而非我方改动记录。SD4 编辑前追加快照 `/tmp/casetrace-m3-01-sd4-cline-1790129931/before/`（`src/casetrace/evaluation/runner.py` `639d75462e961515…`、`tests/evaluation/test_runner.py` `1a7257d190b6c40a…`、`tests/test_cli_evaluate.py` `ca3291e857e3389c…`、`results/README.md` `2950462bb8a845f0…`）；目标新文件 `results/dev-v2-bm25-m3-01.json` 记录为 absent。
- **下一步入口：** SD1–SD4 已全部完成并自测，本包**标 ready for acceptance**（等用户确认后回交 Codex）；Codex accepted 后按 Current Plan 激活 [M3-02 — Embedding 首次接入](m3-02-embedding.md)：先检查本机资源与运行环境，确定本地或 API 方式，经 uv 增加必要依赖，复用同一历史检索文本编码文档与 Query，保存向量与 Case ID 映射并记录模型版本、文本处理、截断策略与缓存绑定，再在同一 dev-v2 上跑第一次语义检索评估。耗时对比沿用本包 `timing` 的边界口径，并注明硬件与冷启动条件。

## Codex Acceptance

- **Spec：accepted（0 findings）。** 对照本包 Codex Plan 与成包后 handoff：公共 `Retriever.search` / `describe` 契约已使 runner 不再读取 BM25 `index`；替身第二方法可在无命中词项时完成同一计分链；默认与显式 `bm25` 等价，未知 / 未实现方法明确失败且不落盘；报告新增有边界说明的建索引、逐 Query 和总耗时；独立 v2 结果未覆写 M2 原件。只读逐字段比较确认 `benchmark` / `retrieval` / `metrics` / `queries` / `summary` 与 M2 正式结果完全一致。注册名 `bm25` 与实现自报名 `bm25_okapi` 分层、CLI 两处 BM25 文案在 M3-02 接入第二方法时再中立化，均已在 Report 记录且不影响本包只接入 BM25 的范围。
- **Standards：accepted（0 findings）。** 变更保持小而显式：公共类型只包含评估器实际依赖的两项行为，方法注册留在组合根，BM25 原导入路径继续可用；未见任务外抽象、重复分支、标签泄漏或需阻塞验收的 smell。`base.py` 已纳入实际执行源码哈希；结果记录区分事实读数、运行元数据和质量结论。旧 dev-v1 哈希失败及结果权限 600 均是已记录的既有限制，不归因于本包。
- **独立验证证据与比较限制：** 2026-09-23 实测 `uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py tests/retrieval/test_bm25.py tests/test_demo.py` → **60 passed**；`uv run pytest -q` → **289 passed、169 subtests passed、1 failed**，唯一失败仍为 `tests/test_benchmark_migration.py:19` 的旧 dev-v1 归档哈希断言（实际 `e92e5bb1…`，历史记录期望 `c0175226…`）。`evaluate --method bm25` exit 0；`--method embedding` exit 2 且目标文件不存在；`demo` exit 0。新产物 SHA-256 为 `013738a2d238ecdb01aa0e57295799009ef1160af4f9b3f8236cd6b495f10108`，M2 产物仍为 `bc457e9576ece6ad29cb2d3991da7c69e939bb4c5a2d0b7330c6039c8441f26d`。本次没有提交可直接隔离 diff，归因依赖 handoff、SD3 / SD4 快照与当前工作区；规划文档的成包改动未算作 Cline 实现。
- **用户代码/教学记录核对：** SD3 快照确认用户提交的 `--method` 声明与 `method=args.method` 透传均保留，Cline 后续只统一格式 / help 并增加展示与测试；默认、显式 BM25、未知方法三条行为均独立通过。教学与用户确认按 Cline Report 保留，不把软件验收当作 Ground Truth 或学习确认。
- **Verdict：accepted（2026-09-23）。** Spec 0 findings；Standards 0 findings。M3-01 完成，未提前实现 Embedding。
- **Current Plan 刷新及下一包基线：** Current Plan 与 practical-todo 已转到 [M3-02](m3-02-embedding.md)。M3-02 实施基线为 `/tmp/casetrace-m3-02-codex-78mz0Z`，记录当前 HEAD、完整 tracked / untracked 状态、patch 与相关文件快照；M3-01 的已验收未提交改动属于该基线，不能在后续误归因或覆写。
