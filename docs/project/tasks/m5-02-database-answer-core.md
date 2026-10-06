# M5-02 — 数据库接入回答核心

状态：**accepted（2026-10-05）**。Cline 已按 SD1～SD3 实施；首次验收发现的数据库异常回显密码问题，已按用户要求由 Codex 最小修复并复验通过。详见下方 Codex Acceptance；M5-03 尚未实施。

## Codex Plan

### 目标与范围

让 `casetrace answer` 可选择文件或 PostgreSQL 数据源，两条加载路径汇入同一套 R3 检索、证据上下文、生成与引用校验。固定 dev-v3 输入切换存储后，排名、原文、来源、实际模型消息与离线响应回放保持一致。

范围及简化原则以 [Current Plan §§2、5、7](../current-plan.md) 为准。复用 M5-01 的内容检查结果；本包只改回答的数据加载接缝、CLI 适配和运行元数据，不实现 FastAPI、Schema 迁移、CRUD、连接池、缓存或通用 Repository。不改检索策略、提示词、数据和 qrels，不新增真实模型调用。

必要输入与入口：

- [M5-01 验收](m5-01-postgresql-roundtrip.md#codex-acceptance)、[数据库运行说明](../../development/postgresql.md)、[M4 → M5 接缝](../handoffs/m4-04-m5-handoff.md)。交接文档描述迁移前状态；当前存储检查分工以本包和 M5-01 为准。
- `storage.connect` / `load_snapshot` 返回已检查的 `LoadedSnapshot`：`records`、`reference`、`payload`、`snapshot`、`counts`。字段和关系继续遵守[冻结结构](../../data/CaseTrace_Data_Structure_V2_No_Scenario.md)，不新增业务规则。
- `answer.context.prepare_answer_run`、`answer.cli.run_answer_question` / `resolve_query` / `run_answer_command`；复用 `build_retriever_from_records`、`build_evidence_context` 和原生成、引用守卫。
- dev-v3 JSON 与主数据 Excel；五条固定 Query 及回放响应见 `results/m4/dev-v3-answer-v10/q001.json`～`q005.json`，不读取 qrels 来决定排名或回答。

### 最小实现决定

**1. 数据源选择放在 CLI 边界。** 新增 `answer --data-source {file,postgres}`，默认 `file`；数据库连接沿用 `CASETRACE_DATABASE_URL`，新增 `--db-schema`，默认 `casetrace`。不新增连接 URL 命令行参数或测试数据库开关。文件模式保持原 `--data` / `--reference` 行为；数据库模式从数据库取案例、主数据及示例 Query，这两个文件参数不参与读取，帮助文字写清即可。

数据库路径用短连接调用一次 `load_snapshot`，完成读回后关闭连接，再检索和调用模型。初始化、导入由 M5-01 命令负责；回答入口不自动建表、导入或回退到文件。

**2. 直接传递已有快照对象。** 为 `prepare_answer_run` 与 `run_answer_question` 增加可选关键字 `loaded_snapshot`，接受已有的 `LoadedSnapshot`；文件路径参数允许不传，但文件路线仍要求两份路径。保留现有显式文件调用形式、`model_factory` 注入、返回类型及状态。传入 `loaded_snapshot` 时使用它的对象和元数据，不打开原文件；文件路径只用于文件路线。已有对象不携带 schema 名，因此另传 `db_schema`（默认 `casetrace`），只用于记录实际来源，不建立连接；CLI 将读取时使用的 schema 原样传入。

加载之后共用一次 R3 建索引/检索、同一 `AnswerRun` 和原回答流程。只提取确实共享的小段代码，不新增通用数据源接口，也不为命名移动整个应用模块。

**3. 检查按职责分工。** 文件路线继续执行现有文件身份、CR/GR、来源及快照检查。数据库路线不重跑 CR/GR/来源校验，不调用 `verify_snapshot`，不再次计算摘要；这些工作已由导入和 `load_snapshot` 承担。回答准备入口只核对库内描述是否对应请求的快照：`snapshot_id`、`known_at`、两份原文件哈希及 `basis`，并保留已有 Query `known_at` 的适用性和时点一致性行为。只支持当前记录的 dev-v3 可用快照，不从 detection_time 推定结案时间。

**4. 示例查询复用已读 payload。** `resolve_query` 可接收数据库读回的 payload；`--query-id` 从其 `queries` 取原始 text 和 known_at，随后把同一个 `loaded_snapshot` 传给准备入口。显式 `--query` / `--known-at` 规则、未知 Query 错误和 `--check-only` 语义保持不变。一次数据库 CLI 运行只读回一次，不因解析示例或 check-only 再读库。

**5. 最少元数据增量。** 在 `corpus` 增加 `data_source`；数据库记录再保存 `schema`、`content_digest`、`digest_version`。快照描述使用实际读回值，仍保留原文件哈希和原始导入路径；数据库路径字段表达来源位置，不表示本次读取了这些文件。保留原字段和 `m4-04-answer-run-2`，以可选字段扩展记录，旧记录缺少 `data_source` 按文件来源理解，不重写历史产物。正文、JSON、落盘记录仍来自同一个 `AnswerOutcome`。

数据库配置、连接、未初始化/未导入、内容或快照错误属于回答前提失败：CLI stderr 给出可理解且不含凭据的错误，返回现有 `EXIT_USAGE=2`，不调用模型、不写回答记录；不包装成 `model_failed` 或 `no_hits`。沿用现有错误适配，不建立新的错误层级或重试机制。

### 预计修改位置

主要是 `src/casetrace/answer/{context,cli}.py`、`src/casetrace/__init__.py`；测试扩充已有 `tests/answer/`，真实数据库对照建议放 `tests/storage/test_answer_integration.py` 以复用现有隔离夹具。补充 README 与 PostgreSQL 运行说明中的数据源命令。存储、检索、生成和提示词实现默认不改；发现必要接缝问题再在 Report 说明。

### 小步实施与教学停点

| 小步 | 产物与检查 | 教学重点 |
|---|---|---|
| SD1 回答核心接缝 | 接受 `LoadedSnapshot`，两条路线汇入现有准备/回答核心；文件回归与一个真实 DB 准备对照 | 换数据来源为何不必复制检索和生成 |
| SD2 CLI 与记录 | 数据源/schema 参数、DB 示例 Query、check-only、前提错误与来源元数据；一次读取 | CLI 负责连接和参数，核心负责业务流程 |
| SD3 等价验证与交接 | 五 Query 离线回放、少量代表性边界、使用说明、Cline Report | 用固定输入和固定响应隔离存储变化 |

Cline 每次实施、验证、讲解一个小步，按 AGENTS 的教学边界等待用户理解/继续；M5 不强制留白练习。用户选定亲自编码时再保留该部分并单独记录贡献。完成本包后停止，不进入 M5-03。

### 测试接缝与验收

以 `prepare_answer_run`、`run_answer_question` 和 CLI 为公开接缝，不围绕内部帮助函数写测试，不复制 M5-01 的全部存储约束/篡改用例。

1. **五 Query 的真实数据库对照：** 在测试库独占 schema 导入 dev-v3，再按 Q001～Q005 分别走文件和 DB 核心。对照排名（ID、顺序、分数、matched_terms）、完整证据上下文及 Case/Detail/checkpoint/字段来源；与保存的 v10 排名、上下文和实际消息对照。不能只断言状态为 ok。
2. **响应回放：** 用现有 `OfflineChatModel` 分别回放对应 v10 `answer_text`，比较两条路线的实际发送消息、状态、解析后的回答、原始响应文本、引用报告及展示正文。数据源/schema/摘要等来源元数据按各自路线验证；源码身份和耗时不要求等于历史记录。回放证明软件等价，不新增模型质量结论或重做语义审阅。
3. **DB 独立性与单读取：** CLI `--query-id Q005 --data-source postgres --check-only` 即使 `--data` / `--reference` 指向不存在的文件也可运行；示例和显式 Query 都来自选定路线。用一次入口调用计数确认示例解析和回答/check-only 复用已读快照，不重算存储摘要。
4. **代表性边界：** DB 空命中不构造模型；一个离线模型失败保持原状态；不匹配快照/known_at 和一个数据库前提失败均在模型之前退出。其余成功/格式/引用/参数边界由现有回答回归覆盖，不另建每项检查的交叉组合。
5. **兼容性：** 默认和显式 `file` 路线一致，现有 CLI/应用调用和旧记录读取保持兼容；DB 记录可序列化、有来源身份，不含连接 URL/密码。

集成测试只用真实 PostgreSQL，复用现有测试库与独占 schema 清理方式；测试环境可将 `CASETRACE_DATABASE_URL` 临时映射到测试 URL，结束恢复环境，不改真实 `.env`。缺库可为普通回归显式 skip，但实际 DB 对照未执行不能验收通过。记录实际执行数，不为计数故意断开数据库再跑一次。

预定检查：

```bash
uv run --locked pytest tests/answer tests/storage -q
uv run --locked pytest -q
uv run ruff check
uv lock --check
git diff --check
```

实施后固定的演示命令：

```bash
uv run --locked casetrace answer --query-id Q005 --check-only
uv run --locked casetrace answer --data-source postgres --query-id Q005 --check-only
uv run --locked casetrace answer --data-source postgres --query "焊线脱落，已排除运输碰伤" --known-at 2026-09-15 --check-only
```

移除 `--check-only` 才会走正常模型生成路径；本包验收使用离线注入，不需要真实调用。连接和准备命令见 M5-01 说明，CLI 输出中区分实际数据源。

选用技能：已读取 [to-spec](../../../.agents/skills/to-spec/SKILL.md)、[handoff](../../../.agents/skills/handoff/SKILL.md)，按 AGENTS 的单包规则执行。Cline 按需使用 implement / tdd / teach；不创建 tracker、独立完成报告或自动 commit。

## Handoff Baseline

- 起始 HEAD：`bb6ff09e490eb77cf7562396d401dcfeaa6ec1d8`（`M5 started & M1~M4 code review.`）。任务准备前工作区干净，tracked/untracked/staged 均无变化；本次只新增本包并更新 Current Plan，不归因于 Cline。
- 实施基线：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-02-regeq6nm/`。`before/` 保存相关源码/测试、dev-v3 输入、五条 v10 回放、README、计划和存储说明，共 49 个文件；`sha256.json`、`head.txt`、`status.txt`、`working-tree.patch`、`staged.patch` 可供核对。未保存真实 `.env` 或凭据。
- `absent.txt` 记录本包和建议的新集成测试文件起点不存在。Cline 编辑前核对基线与期间变化；若涉及其它文件再补对应快照。保留基线至验收，不制造提交充当基线。
- 已有验收证据：M5-01 于 2026-10-05 accepted；storage 69 passed / 0 skipped（49 项真实 PG），全套 640 passed、169 subtests passed。属于上一包实测，本轮设计没有重跑测试、连接数据库或调用模型。
- 当前两个数据源仍未接到同一回答入口；上面的新参数和接口是本包目标，不是已实现能力。

## Cline Report

状态：**ready for acceptance（2026-10-05）**。按 AGENTS 就地实施 SD1～SD3，未新建分支 / PR / worktree（不启用 implement-spec 的并行分支流程）；用户要求实现完成后统一 review，故本轮未插入教学停点。Cline 自建基线 `/tmp/casetrace-m5-02-cline-IxeFSB/`（`before/`、`head.txt` = `bb6ff09`、`status.txt`），与包内 Handoff Baseline 的 HEAD 一致。

### SD1 回答核心接缝（`src/casetrace/answer/context.py`）

- 新增 `DATA_SOURCE_FILE` / `DATA_SOURCE_POSTGRES` 与 `SNAPSHOT_IDENTITY_FIELDS`。
- `prepare_answer_run` 增加可选关键字 `loaded_snapshot`、`db_schema`（默认 `casetrace`）；`dataset_path` / `reference_path` 改为可选，文件路线仍要求两份路径，只给一份即报错。
- 抽出确实共享的小段：`_check_known_at`、`_check_detection_times`、`_snapshot_metadata`。文件路线保留原文件身份、CR/GR、来源与内容时点检查；数据库路线新增 `_check_loaded_snapshot`，只核对 5 个快照身份字段并保留 `known_at` 适用性与时点一致性，不调用 `verify_snapshot`、不重算摘要、不重跑来源校验。
- 运行元数据：`corpus` 增加 `data_source`；数据库记录再存 `schema`、`content_digest`、`digest_version` 与库内原始导入路径（表示来源位置，不代表本次读了文件）；快照描述取库内实际读回值；记录版本仍为 `m4-04-answer-run-2`，旧记录不改写。
- `build_evidence_context` 的 `source` 改为按 `SOURCE_FIELDS` 固定字段顺序。原因：库内 payload 经 jsonb 读回后字典键顺序与文件不同，会让模型消息逐字不等；文件路线的顺序本来就是 `SOURCE_FIELDS` 顺序，因此该改动不改变文件路线与 v10 的既有输出。

### SD2 CLI 与记录（`answer/cli.py`、`src/casetrace/__init__.py`）

- `run_answer_question` 透传 `loaded_snapshot` / `db_schema`，原有文件调用形式、`model_factory` 注入与返回类型不变。
- 新增 `load_database_snapshot(schema)`：`connect()` + `load_snapshot()`，读完即关；连接、驱动与读回错误统一转 `ValueError`（沿用现有错误适配），消息不回显连接串，不新建错误层级或重试。
- `resolve_query(args, *, loaded_snapshot=...)` 可用库内 payload 解析示例 Query；`run_answer_command` 选定数据源并只读回一次，示例解析与 `--check-only`/完整回答复用同一对象；`_report_inputs`、`format_answer_text` 用 `_data_source_label` 区分实际数据源，旧记录缺 `data_source` 按文件来源理解。
- `__init__.py` 新增 `--data-source {file,postgres}`（默认 `file`）与 `--db-schema`（默认 `casetrace`），帮助文字写明 postgres 路线不读 `--data` / `--reference`；`demo`、`evaluate` 未改。

### SD3 测试、说明与执行结果

新增 `tests/answer/test_data_source.py`（24 项，合成 `LoadedSnapshot` + CLI 假读回）与 `tests/storage/test_answer_integration.py`（7 项，真实 PostgreSQL）。覆盖五 Query 文件/DB 对照与 v10 排名·上下文·实际消息对照、离线响应回放（消息/状态/回答/响应文本/引用/展示正文，仅「数据源」一行按路线各自校验）、CLI 与文件无关且一次读取、空命中与模型失败、快照不匹配与 `known_at`、未导入 schema 的前提失败、旧记录与默认 file 路线兼容。

```bash
uv run --locked pytest tests/answer tests/storage -q   # 219 passed（answer 143 / storage 76）
uv run --locked pytest -q                              # 671 passed, 169 subtests passed
uv run --locked ruff check                             # All checks passed
uv lock --check                                        # Resolved 65 packages
git diff --check                                       # 无输出
```

真实 PG 执行数：`tests/storage` **76 passed / 0 skipped**，其中新增对照 7 项全部连真实 PostgreSQL 并各用独占 schema（未断开数据库凑计数）。演示命令三条均已实际执行，输出分别标注 `数据源：文件` 与 `数据源：PostgreSQL schema=casetrace`，排名一致（Q005：`1.C007 > 2.C001 > 3.C004 > 4.C003`）。本轮唯一真实模型调用数：0。

### 自查修复（code-review 后）

- `run_answer_command` 去掉多余的 `getattr(args, ...)` 默认值，与 `_report_inputs` 一致使用 argparse 一定提供的属性。
- `prepare_answer_run` 把两条路线共有的 `case_count` / `review_status` / `source_cases_are_draft` 提到分支外，去掉重复字面量。
- 集成测试的局部 import 提到模块顶部；删掉与单测重复的默认 file 用例，换成「文件路线不依赖数据库配置」的兼容用例（不含未使用变量）。
- 回放比对补「数据源」行存在性断言，避免 `body_without_source_line` 变成空比较。

### 偏差与剩余问题

- 数据库路线按 §3 决策不再重跑文件哈希、CR/GR 与来源校验；「绕过 `load_snapshot` 直接改表」不在回答入口重复检测，仍由 `load_snapshot` 的摘要核对与 `storage verify` 负责。
- `build_evidence_context` 的字段顺序统一是本次唯一改动上下文的代码点，已由 v10 逐字消息对照回归覆盖。
- `tmp/m4_04_run_all.py` 未改：新增参数均为可选关键字，仍走文件路线。
- 未实现 FastAPI、Schema 迁移、CRUD、连接池、缓存或通用 Repository；未新增依赖，未改检索、提示词、数据与 qrels。

### 教学与贡献记录

- 本轮由 Cline 连续编码，用户实际编码贡献 0。
- **教学状态：已教学（2026-10-05）。** SD1～SD3 已逐段讲解，用户确认理解。
- 已讲要点：换数据源为何只需把 `LoadedSnapshot` 传进同一核心（而不是复制检索与生成）；职责分工（CLI 连接与参数，核心业务与前提检查）；一次读取的边界与错误映射；`load_snapshot` 读回与 `LoadedSnapshot`／`StoredSnapshot` 的区别；离线回放与「固定输入＋固定响应」等价验证；两条路线并存的原因与边界（数据库面向服务化，文件为默认／demo／evaluate／对照基准）。
- 可选练习：为 `prepare_answer_run` / `run_answer_question` 写接缝测试（合成 `LoadedSnapshot`）；用保存的 v10 响应做离线等价回放。


## Codex Acceptance

结论：**accepted（2026-10-05，最小修复后）**。使用仓库 code-review 技能，按 AGENTS 的单代理与工作区基线规则分别审查 Spec / Standards。首次验收为 needs changes；用户随后明确要求最小修复，Codex 修复并复验通过，未进入 M5-03。

### 审查范围与基线

- 已核对 Handoff Baseline：相关源码、README、数据库说明的 `before/` 与起始 `bb6ff09` 一致。当前实现差异为 `__init__.py`、`answer/cli.py`、`answer/context.py`，以及两份新增测试和使用说明；数据、检索策略、提示词、历史产物及依赖未改。
- Current Plan 和本任务包的准备改动不归因于 Cline。此次验收文档修改前另存 `/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-02-codex-review-ptv2pf_6/before/`，含已有未跟踪任务包；原实施基线继续保留。
- 本次修复前另存 `/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-02-credential-fix-9k_34hbc/`，包含 CLI、新增测试、Current Plan、任务包的 `before/` 以及 HEAD/status；修复仅归属 Codex。

### Spec

**首次发现 1 项，现已修复：[P2] 数据库配置错误可能向 stderr 泄露密码。** 原 `src/casetrace/answer/cli.py:119–120` 将 `psycopg.Error` 的原文拼进 `ValueError`，CLI 随后直接打印。驱动解析无效连接配置时会在异常中包含密码字段的原始片段，违反 Codex Plan「错误不含凭据」要求。以下保留修复前复现证据。

复现（仅使用虚构密码，不修改 `.env`，不实际连接数据库）：

```bash
CASETRACE_DATABASE_URL='postgresql://review_user:DUMMY%REVIEW_PASSWORD@127.0.0.1:1/db' \
  uv run --locked casetrace answer --data-source postgres --query-id Q005 --check-only
```

实际 stderr：`运行前提不满足：数据库路线不可用（ProgrammingError）：invalid percent-encoded token: "DUMMY%REVIEW_PASSWORD"`，退出码 2。另用未正确引用的 conninfo 密码复现了同类回显。完整回答模式也复现；模型工厂调用数 0、未写回答记录，其余前提失败行为正确。

修复边界：对连接/驱动异常使用不含原始异常文本的可理解提示，可保留异常类型并提示检查 `CASETRACE_DATABASE_URL`、连接可用性与初始化状态；保留存储层安全的快照/摘要/未导入诊断。补一个公开 CLI 回归，使用上述虚构密码，断言 stderr 无密码片段、退出码 2、不构造模型、不写记录。无需新增错误层级、重试或通用脱敏机制。

其余约定的数据源选择、快照身份、单次读回、来源元数据、文件兼容性和五 Query 等价要求通过，未发现其它影响验收的问题。

### Standards

上述同一缺陷原先也违反数据库连接模块及运行说明的「凭据不写入日志、错误不回显连接串」约定，最小修复后已满足。无额外独立缺陷；职责划分与复杂度符合本包要求：连接留在 CLI 边界，核心复用 `LoadedSnapshot`，未重复校验摘要，未新增通用 Repository 或不必要抽象。

### 独立验证证据

- `uv run --locked pytest tests/answer tests/storage -q -ra`：**219 passed / 0 skipped**，包含新增 7 项真实 PostgreSQL 测试；五 Query 的排名、完整上下文/来源、实际发送消息与 v10 一致，固定响应回放通过。
- `uv run --locked pytest -q -ra`：**671 passed、169 subtests passed / 0 skipped**。
- `uv run --locked ruff check`、`uv lock --check`、`git diff --check`：全部通过。
- 本包三条 check-only 演示命令实际执行成功；Q005 文件/DB 排名同为 `C007 > C001 > C004 > C003`，显式数据库 Query 也可运行，输出准确标记来源。
- 额外异常复现使用虚构配置及离线模型工厂拦截；本轮真实模型调用数 **0**。现有测试通过未覆盖上述配置解析泄密场景，不足以消除此缺陷。

### 最小修复与复验

- `load_database_snapshot` 的原异常分支改为固定提示「请检查 CASETRACE_DATABASE_URL、数据库连接及初始化状态」，只保留异常类型；不输出驱动异常原文。不新增错误层级、重试或脱敏工具，存储层的快照/摘要/未导入 `ValueError` 仍保留原诊断。
- 新增 1 个公开 CLI 回归 `test_cli_postgres_invalid_connection_does_not_echo_password`，使用虚构的无效 URI 触发真实驱动解析错误，检查密码/URL 不回显、退出码 2、模型工厂调用 0、未写记录。测试只使用注入的环境变量，不加载本机 `.env`。
- 修复前新测试失败，stderr 确认泄露虚构密码。修复后回答/存储 **220 passed / 0 skipped**；首次全套因新用例加载 `.env` 污染后续环境测试，结果为 **1 failed、671 passed**。在该用例隔离配置加载后，全套复验为 **672 passed、169 subtests passed / 0 skipped**，包含原有 7 项真实 PostgreSQL 对照。
- ruff、lock、diff 检查通过；本轮真实模型调用 **0**。Spec / Standards 无剩余验收缺陷，M5-02 accepted。

下一入口：准备 M5-03 FastAPI 任务包；本次仅完成 M5-02 修复、复验和计划状态更新，未实施下一包。
