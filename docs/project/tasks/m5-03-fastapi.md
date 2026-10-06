# M5-03 — FastAPI 回答接口

状态：**accepted（Codex 最小修复后复验，2026-10-06）**。前置 M5-02 accepted；SD1～SD3 已完成，首次验收的三项问题已修复，真实 PostgreSQL 回放、HTTP 入口与回归通过。

## Codex Plan

### 目标、范围与必读入口

提供可本机启动的 FastAPI 服务：JSON 请求 → PostgreSQL 快照 → 现有回答核心 → JSON 与明确 HTTP 状态。相同输入和离线模型响应下，API 与 CLI 核心的排名、上下文、消息、回答及来源一致。

先读 [AGENTS.md](../../../AGENTS.md)、[Current Plan §§2、5、7](../current-plan.md)、[M5-02 验收](m5-02-database-answer-core.md#codex-acceptance)。连接、初始化与导入使用[数据库运行说明](../../development/postgresql.md)；涉及存储接缝时再查 M5-01，不重开冻结模型设计。

实现入口为 `answer.cli.run_answer_question` / `load_database_snapshot` / `build_model`，返回 `AnswerOutcome`；准备、检索、生成和引用校验已有实现。模块名字含 `cli` 不要求移动代码。运行记录结构见该模块及 `results/m4/dev-v3-answer-v10/q001.json`～`q005.json`；测试借鉴 `tests/answer/test_data_source.py`、`tests/storage/test_answer_integration.py` 和存储夹具。

遵守 Current Plan 的简化原则。保持 R3、top_k 默认 4、v10 提示词和现有模型配置；API 不改数据、qrels 或旧产物。范围不含 CRUD、连接池、缓存、异步数据库/模型改造、流式响应、后台任务、重试、认证系统、Web 页面或应用 Docker 化。当前只做本机学习展示，默认绑定 `127.0.0.1`；M6 另行负责 Demo 与工程收束。本包测试和验收不新增真实模型调用。

### 接口与实现决定

**1. 一个应用入口。** 新增 `src/casetrace/api.py`，提供 `create_app(*, db_schema=DEFAULT_SCHEMA, model_factory=None)` 和默认 `app`。默认 schema 为 `casetrace`，默认工厂复用 `build_model(DEFAULT_MODEL)`；工厂传入的是可调用对象，模型仅在核心确需生成时构造。应用创建、模块导入、健康检查均不连接数据库或模型。

服务固定走 PostgreSQL：连接沿用 `CASETRACE_DATABASE_URL` / 项目 `.env`，schema 由服务端应用工厂配置。客户端只提交问题，不提交连接 URL、凭据、文件路径、schema、模型选择或数据源。CLI 的两条数据源路线保持现状。

**2. `POST /answer` 请求。** JSON 对象仅有以下字段，额外字段拒绝（422）：

| 字段 | 约定 |
|---|---|
| `query` | 必填字符串，拒绝空白；保留原始文本传给核心，不改写、截断或从历史反填 |
| `known_at` | 必填 `YYYY-MM-DD` 日期字符串；当前仅支持 `DEV_V3_SNAPSHOT.known_at`，不接受时间戳、datetime 或其它日期 |
| `top_k` | 可省略，默认现有 `DEFAULT_TOP_K=4`；严格正整数，拒绝 bool、小数和数字字符串 |

以小型 Pydantic 请求模型完成 HTTP 字段校验；日期约定引用现有快照常量，不另建时点规则。无效 JSON、类型和字段错误用框架的 422 `detail` 响应，不必统一成另一套错误框架。请求不提供 `query_id`；演示/回放将保存的 Query 原文作为 `query`，核心运行记录的 `query_id` 为 null。

**3. 调用链。** 有效请求用 `load_database_snapshot(db_schema)` 一次短连接读回，关闭连接后把同一 `LoadedSnapshot`、schema、原始 query、日期和 top_k 传给 `run_answer_question`。核心仍负责快照身份与业务前提、R3、上下文、生成和引用守卫。复用读回检查，不再调用 `verify_snapshot`、重读文件或重算摘要。回答记录从返回的 `AnswerOutcome` 获取，API 不复制业务流程。

路由使用普通同步 `def`，适配现有同步 Psycopg 与模型 SDK；依据 [FastAPI 同步调用说明](https://fastapi.tiangolo.com/async/)。本包不为异步语法改写已验收核心。

**4. `POST /answer` 输出与 HTTP 状态。** 获得 `AnswerOutcome` 时返回顶层 `status`、`message`、`record`，其中 `record` 沿用完整运行记录，不逐层复制 dataclass / 业务模型；顶层与记录状态一致。保留 ranking、context、实际模型消息、answer / answer_text、citations、数据/源码/模型身份、耗时和用量。状态映射如下：

| 情况 | HTTP | 响应行为 |
|---|---|---|
| `ok` | 200 | 返回成功记录与回答 |
| `no_hits` | 200 | 保留具体不足与空候选，不构造模型 |
| `model_failed`，`record.error.type == ModelConfigError` | 503 | 服务端模型配置不可用；保留原核心状态 |
| 其它 `model_failed` | 502 | 模型调用失败；保留原核心状态 |
| `format_failed` | 502 | 模型返回格式不可用；保留失败证据 |
| `citation_failed` | 502 | 引用校验失败；保留失败证据 |
| 请求校验失败 | 422 | 框架 `detail`；不读数据库、不构造模型 |
| DB 配置/连接/未导入/内容或快照前提失败 | 503 | `status=service_unavailable`、安全的 `message`、`record=null`；无回答记录、不调用模型 |
| 未预期异常 | 500 | 通用安全说明，不暴露 traceback 或原始异常文本，不伪装成上述业务状态 |

客户端依据 HTTP 与 status 判断成功；格式/引用失败记录中虽可能有模型文本或解析后的回答，也不能当成成功展示。`service_unavailable` 仅为 HTTP 边界状态，不加入 `AnswerOutcome` 或 CLI 退出码。

**错误文本边界：** DB 继续使用已修复的加载入口；503/500 给简短可操作说明，不拼接任意异常原文。模型失败记录当前含 SDK 异常原文，HTTP 适配时对返回副本中的 `error.message` 和顶层 `message` 使用固定安全说明，保留错误类型、调用标记及其余证据；不修改核心对象或既有 CLI 行为。用虚构凭据片段测试这一条，不建设通用脱敏平台，也不打印连接串/凭据。错误处理限于必要的入口适配和一个未预期异常兜底。

**5. `GET /health` 与文档。** 返回 200 `{"status":"ok"}`，仅证明 HTTP 进程能响应，不代表 DB / 模型可用。保留 `/docs` 与 `/openapi.json`；请求模型、成功形状、200/422/502/503/500 和示例在 OpenAPI 中可见。无需另建运行记录文件或服务端历史存储：本包的记录通过 JSON 返回，调用方可自行保存；CLI 原落盘行为不变。

### 修改位置与依赖

预计新增 `src/casetrace/api.py`、`tests/api/test_answer_api.py`、`tests/storage/test_api_integration.py`、`docs/development/api.md`；更新 `pyproject.toml` / `uv.lock` 和 README 的入口链接。现有回答/存储实现原则上不改，必要接缝修复在 Report 说明。

运行依赖只加 FastAPI 与 Uvicorn；直接使用 Pydantic 时明确声明它，HTTPX 放 dev 依赖用于 TestClient。复用现有 uv 配置和锁文件，避免顺带升级既有模型/检索依赖。具体版本在实施时按 Python 3.12 和现有锁文件解析、锁定，不在计划中猜版本。TestClient 用法见 [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)；安装失败保留事实并交接，不循环更换不明镜像源。

### 小步实施与教学停点

| 小步 | 产物与完成条件 | 教学重点 |
|---|---|---|
| SD1 应用与 HTTP 契约 | 依赖/锁文件、应用工厂、health、请求模型与 OpenAPI；通过无库/无模型的 health 与无效请求测试 | HTTP body、Pydantic 校验、422；health 能证明什么 |
| SD2 接到现有核心 | 一次 DB 读回、同一核心、JSON 输出与状态/安全错误映射；离线通过成功、空命中及三类失败 | HTTP 适配与业务核心的职责；同步路由；工厂注入 |
| SD3 等价验证与使用说明 | 真实 PG 五 Query 回放、实际 HTTP 启动检查、回归与运行文档；完成本包 Report | 固定输入/响应隔离接口变化；软件等价与模型质量的区别 |

Cline 按 AGENTS 每次实施、验证和讲解一个小步，等待用户确认理解/继续；若用户明确要求集中实现后统一 review，则在 Report 记录该安排。M5 不强制留白练习，用户选择亲自编码时保留该部分并记录实际贡献。完成本包后停在 ready for acceptance，不自动进入 M6。

选用 skill：已读取 [writing-for-agents](../../../.agents/skills/writing-for-agents/SKILL.md)、[handoff](../../../.agents/skills/handoff/SKILL.md)、[to-spec](../../../.agents/skills/to-spec/SKILL.md)。按 AGENTS 将 Spec / Handoff 写在同一任务包，引用现有权威规则。Cline 按需读项目内 implement / tdd / teach；Codex 验收用 code-review。无需 tracker、单独报告、并行代理或自动 commit。

### 测试接缝与验收标准

最高接缝为 HTTP：用 `TestClient(create_app(...))` 验证公开请求/响应，注入现有 `OfflineChatModel`、失败替身和测试快照加载入口，不伪造 `AnswerOutcome` 来证明链路已接通。既有核心测试继续覆盖业务细节；API 新测试只验证接口增量。

1. **HTTP 契约：** 成功/空命中为 200；模型配置 503、调用/格式/引用失败 502，并保留各自 status 与记录。验证无效 JSON、缺字段、空白 query、非字符串、错误日期、未支持时点、top_k 非正整数/小数/bool/字符串、额外字段为 422，数据库和模型调用数均为 0。默认 top_k 与原始含否定/背景的 query 原样传递。失败不归为 `no_hits`。
2. **失败与安全：** 一个数据库前提失败为 503；一个未预期异常为安全 500。模型调用错误和非法 DB URL 使用虚构凭据片段，响应、应用主动输出中没有该片段/连接串；模型失败 record 的安全说明与 status 一致。health 不调用任何依赖；同一 app 连续两次请求的 query/记录不相互覆盖。
3. **真实 PG 五 Query 回放：** 新集成测试放 `tests/storage/` 复用该目录的真实测试库/独占 schema 夹具。导入 dev-v3，临时将服务连接配置映射到测试 URL，以 `create_app(db_schema=独占schema, model_factory=离线工厂)` 发 HTTP 请求；服务实际建立自己的短连接读回，不能只注入事先构造的快照冒充真实 DB 链路。只清理本测试创建的 schema，不修改 `.env` 或开发库。
4. **对照内容：** Q001～Q005 使用保存的 v10 原文、日期和对应 `answer_text` 回放，比较 HTTP 与 `run_answer_question` 文件路线的排名（ID/顺序/分数/matched_terms）、完整上下文及来源、实际模型消息、状态、结构化回答、响应原文、引用报告和模型用量；同时与保存的 v10 ranking/context/messages 对照。query_id、数据源/schema/摘要/导入路径、源码身份和耗时按实际路线核对，不要求与历史记录逐字相同。可直接复用已建测试助手，避免复制上一包整套用例。
5. **读取边界与独立性：** 一个 HTTP 请求恰好一次快照加载；开始模型调用前连接已关闭。请求时文件/Excel 加载入口不可用仍能从 DB 完成回答（保留测试回放文件自身的读取）。不重算摘要、不运行 verify、不建表/导入/回退文件。沿用现有存储测试证明完整读回，API 无需重测全部冻结约束。
6. **可运行入口：** 实际启动 Uvicorn，检查 `/health`、`/openapi.json` 和一个无效请求的 422（均不调用模型），随后停止进程。文档给出安装、数据库准备链接、启动、JSON 请求和响应读取示例；有效请求链路由 TestClient + 真实 PG + 离线模型证据完成，不用真实模型计费请求充当验收。

集成测试缺库可为普通回归显式 skip，但真实 PG 对照未执行不能 accepted。Report 记录实际命令/结果、跳过/未跑项与真实模型调用数；不照抄上一包数字。软件回放不新增 AI 质量结论。

实施完成后执行：

```bash
uv run --locked pytest tests/api tests/answer tests/storage -q
uv run --locked pytest -q
uv run --locked ruff check
uv lock --check
git diff --check
```

预计本机运行命令（**本包准备时尚不可用**）：

```bash
uv sync --locked --inexact
uv run --locked uvicorn casetrace.api:app --host 127.0.0.1 --port 8000
curl --fail-with-body http://127.0.0.1:8000/health
```

有效请求示例（**实施后需已导入 DB 与模型凭据，正常路径会调用真实模型**）：

```bash
curl --fail-with-body http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  --data '{"query":"焊线脱落，已排除运输碰伤","known_at":"2026-09-15","top_k":4}'
```

## Handoff Baseline

- 起始 HEAD：`bb6ff09e490eb77cf7562396d401dcfeaa6ec1d8`。该提交本身不含全部已验收 M5-02 实现；**以下工作区内容是本包起点**，不得清理或归因于 M5-03。
- 准备前已有 tracked 修改：`README.md`、`docs/development/postgresql.md`、`docs/project/current-plan.md`、`src/casetrace/__init__.py`、`src/casetrace/answer/cli.py`、`src/casetrace/answer/context.py`。已有 untracked：`docs/project/tasks/m5-02-database-answer-core.md`、`tests/answer/test_data_source.py`、`tests/storage/test_answer_integration.py`；staged 为空。
- 实施前快照：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-03-hx6172yp/`。`before/` 保存 49 个相关文件，包含上述既有未跟踪文件、回答/存储代码与测试、pyproject/lock、输入/主数据、五条 v10 回放及计划/说明；`sha256.json`、`head.txt`、`status.txt`、`working-tree.patch`、`staged.patch` 供核对。未保存 `.env` 或凭据。
- `absent.txt` 记录本包、API 模块、`tests/api`、API 集成测试与 API 运行说明起点不存在。本轮准备只新增本包、更新 Current Plan；这些规划改动不归因于 Cline。Cline 编辑前核对 HEAD、工作区与快照，记录期间变化；涉及额外文件时先补快照。保留至验收，无需制造提交。
- 前包记录的证据：M5-02 accepted，回答/存储 220 passed / 0 skipped，全套 672 passed、169 subtests passed / 0 skipped，ruff/lock/diff 通过，真实模型调用 0。本轮准备仅检查源码/记录与任务文档，未重跑这些测试、未连接 DB、未调用模型或安装依赖。
- Codex 修复基线（2026-10-06，用户授权直接修复并保持学习展示范围）：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-03-fix-am6klf2t/before/` 保存 API、核心快照检查、接口测试、运行/学习说明、任务包与 Current Plan 的修复前内容，包含已有未跟踪文件。未保存 `.env` 或凭据。

## Cline Report

状态：**ready for acceptance（2026-10-05）**。SD1～SD3 已按 AGENTS 就地实施（不新建分支／PR／worktree）；用户要求先完成 SD1／SD2、复审后再做 SD3，故本轮未插入教学停点。真实 PostgreSQL 五 Query 对照已执行；真实模型调用 0。

完成后在本节记录 SD1～SD3 实际改动、命令与观察结果（含未跑/skip）、基线期间变化、偏差/剩余问题、已教/待教内容、用户实际贡献、真实模型调用数，以及下一验收入口。结论为 ready for acceptance 或 blocked；自测不替代 Codex 验收。

### SD1 应用与 HTTP 契约

- 基线核对：实施前 HEAD 仍为 `bb6ff09e490eb77cf7562396d401dcfeaa6ec1d8`，工作区 tracked/untracked 与 Handoff Baseline 一致；SD1 未改动基线中既有文件，只新增 `src/casetrace/api.py`、`tests/api/test_answer_api.py` 并更新 `pyproject.toml` / `uv.lock`。
- 依赖：运行时新增 `fastapi>=0.142,<1`、`uvicorn>=0.54,<1`、`pydantic>=2.13,<3`；dev 新增 `httpx>=0.28,<1`（供 TestClient）。`uv.lock` 只新增 fastapi／starlette／uvicorn／opentelemetry-api，解析为 fastapi 0.142.2、starlette 1.7.0、uvicorn 0.54.0、pydantic 2.13.5、httpx 0.28.1；既有模型／检索依赖未升级。
- 新增 `src/casetrace/api.py`：`create_app(*, db_schema=DEFAULT_SCHEMA, model_factory=None)` 与默认 `app`；配置挂 `app.state`，默认工厂复用 `build_model(DEFAULT_MODEL)`，模型仅在核心确需生成时构造；应用创建、模块导入与 `/health` 均不连接数据库、不构造模型。
- `GET /health` 返回 200 `{"status":"ok"}`；`POST /answer` 请求模型 `AnswerRequest`：`query` 非空且保留原文、`known_at` 仅接受 `YYYY-MM-DD` 文本且须等于 `DEV_V3_SNAPSHOT.known_at`（拒绝 datetime、时间戳与其它日期）、`top_k` 严格正整数默认 4（拒绝 bool／小数／数字字符串）、额外字段拒绝；保留 `/docs` 与 `/openapi.json`，上述形状与 200/422/502/503/500 在 OpenAPI 可见。
- `POST /answer` 的有效请求路径（一次 DB 读回 → 同一核心 → 状态与安全错误映射）留待 SD2；当前在 `answer()` 内以明确占位说明，无效请求在任何数据库／模型调用前由框架返回 422。
- 新增 `tests/api/test_answer_api.py`（21 项）：health、默认 schema／工厂、`/docs`＋OpenAPI 契约、16 类无效请求 422；用替身使「连接数据库」和「构造模型」一旦发生即失败，从而证明调用数为 0；另有请求模型默认 `top_k=4` 与原文保留检查。
- 执行与观察：`uv run --locked pytest tests/api -q` → 21 passed；`uv run --locked pytest -q` → 693 passed、169 subtests passed、0 skipped；`uv run --locked ruff check` → All checks passed；`uv lock --check`、`git diff --check` 通过。额外冒烟：实际启动 `uvicorn casetrace.api:app --host 127.0.0.1 --port 8011`，`/health`=200、`/openapi.json` 含 `/answer`、带额外字段的无效请求=422，之后停止进程；均未构造模型。真实模型调用 0。
- 下一入口：SD2「接到现有核心」（`load_database_snapshot` + `run_answer_question` 接线、JSON 输出与状态／安全错误映射，离线通过成功、空命中及三类失败）。

### SD2 接到现有核心

- `src/casetrace/api.py`：`POST /answer` 接线——`load_database_snapshot(db_schema)` 一次短连接读回（连接在检索／生成前关闭），把同一 `LoadedSnapshot`、schema、原始 `query`、`known_at`、`top_k`、`query_id=None` 交给 `run_answer_question`；核心实现不变，API 只做适配。
- 响应：顶层 `status`／`message`／`record`，`record` 沿用完整运行记录；状态映射 `ok`／`no_hits`→200，`ModelConfigError` 的 `model_failed`→503，其余 `model_failed`／`format_failed`／`citation_failed`→502，DB 前提失败→503 `service_unavailable`（`record=null`），未预期异常→500 `internal_error`。`service_unavailable`／`internal_error` 只作 HTTP 边界状态，不进 `AnswerOutcome` 或 CLI 退出码。
- 错误文本边界：`_redacted_record` 返回记录副本并替换 `error.message`，顶层 `message` 用固定安全说明，保留 `error.type`、`response.called_model` 及其余证据；不修改核心对象或既有 CLI 行为。
- 测试：新增 `tests/api/conftest.py`（合成 `LoadedSnapshot`）与 `tests/api/test_answer_api.py` 的 9 项 SD2 用例（成功、空命中、模型配置 503、调用／格式／引用 502、DB 前提 503、未预期 500、两次请求独立且各读一次）；离线用 `OfflineChatModel` 子类与失败替身，注入测试快照读回入口，不伪造 `AnswerOutcome`。
- 执行与观察：`uv run --locked pytest tests/api -q` → 30 passed；`uv run --locked pytest -q` → 702 passed、169 subtests passed、0 skipped；`ruff check`／`uv lock --check`／`git diff --check` 通过；真实模型调用 0。
- 复审修复（用户要求复审后）：`known_at` 校验器改为同时接受真正的 `date`（明确拒绝 `datetime`）；消除只写不读的第二配置源——路由统一改为从 `app.state` 读 schema 与模型工厂；同步修正 `docs/learning/fastapi-cheatsheet.md` 的过期说明与测试清单。新增 2 项接口测试（date/datetime、`app.state` schema 生效）。
### SD3 等价验证与使用说明

- 新增 `tests/storage/test_api_integration.py`（4 项，真实 PostgreSQL，复用该目录 `storage_connection`／`scratch_schema` 独占 schema 夹具）：在独占 schema 导入 dev-v3，并把 `CASETRACE_DATABASE_URL` 临时映射到测试 URL，再以 `create_app(db_schema=独占schema, model_factory=离线工厂)` 发 HTTP 请求；服务实际建立自己的短连接读回，不下发预造快照。
- Q001～Q005 用 v10 原文、日期与对应 `answer_text` 回放：HTTP 与文件路线的排名（ID／顺序／分数／matched_terms）、完整上下文、实际模型消息、状态、结构化回答、响应原文、引用报告、模型用量逐项一致；排名／上下文／实际消息同时与保存的 v10 记录一致。`query_id`、来源/schema/摘要/导入路径、源码身份按实际路线核对；耗时与真实模型用量不回比历史。
- 读取边界：一个请求恰好一次快照加载，并观察到连接在模型构造前已关闭（`spy_connect` 读 `connection.closed`）；文件/Excel 加载入口与 `verify_snapshot` 换成失败替身时仍能仅凭 DB 完成回答；摘要复用读回值，不另行重算。非法 DB URL 只回 503 安全说明（无连接串／虚构凭据片段）；无效请求 422 不读库。
- 实际 Uvicorn 启动检查：`uvicorn casetrace.api:app --host 127.0.0.1 --port 8021` → `/health`=200 `{"status":"ok"}`、`/openapi.json` 含 `/answer`＋`/health` 且响应码 200/422/500/502/503、无效请求=422，随后停止进程；服务日志为空，均未构造模型。
- 文档：新增 `docs/development/api.md`（安装、数据库准备链接、启动、请求／响应与状态映射、边界与代码位置）；README 增加「回答 API」入口链接与启动示例。
- 执行与观察：`uv run --locked pytest tests/api tests/answer tests/storage -q` → 256 passed、0 skipped（含 4 项真实 PG API 对照）；`uv run --locked pytest -q` → 708 passed、169 subtests passed；`ruff check`／`uv lock --check`／`git diff --check` 通过；真实模型调用 0。
- 偏差与剩余：未新增真实模型调用；核心前提失败与其它 `ValueError` 共用 503 映射是复审记录的折中（未加异常类型）。用户贡献：指定先做 SD1、SD2 后统一 review，并要求复审修复与 SD3。真实模型调用数：0。
- 下一入口：交回 Codex 验收；不自动进入 M6。

## Codex Acceptance

状态：**accepted（2026-10-06，用户授权 Codex 直接最小修复后复验）**。

以下保留首次 needs changes 的观察与证据；最终修复及结论见本节末尾。

### 审查范围与基线

- 核对 Handoff Baseline 的真实快照与 HEAD，49 个既有文件中只有 README、Current Plan、pyproject 与 lock 有变化；此前已验收的回答/存储实现与测试均与快照一致。审查本包新增 API、接口/真实 PG 测试、运行说明及学习速查文档，并核对必要的核心接缝。
- 锁文件仅新增 fastapi、starlette、uvicorn、opentelemetry-api；既有包未升级或移除。未修改实现、测试、输入数据或旧产物；本次只记录验收与刷新活动包状态。

### Spec

1. **[P2] 非数据库异常被误报为数据库不可用**（`src/casetrace/api.py:238–250`）。`except (ValueError, OSError)` 覆盖快照加载、完整核心和响应序列化，不能证明异常来自数据库前提。实际复现：服务使用真实测试库的已导入快照，设置虚构模型 key 与 `HTTPS_PROXY=invalidscheme://127.0.0.1:1`；默认模型构造抛 `ValueError`，HTTP 却返回 503 / `service_unavailable` / 数据库检查说明 / `record=null`。没有真实模型调用。这违反未预期异常须为安全 500、失败状态分开的契约；Report 中记录“折中”不能代替该契约。修复应收窄数据库/快照前提错误的识别范围，并覆盖模型构造及响应输出阶段的非数据库异常；不要求建立通用错误框架或重做核心。
2. **[P2] 响应读取示例未区分成功、空命中与失败**（`docs/development/api.md:57–61`）。示例无条件切片 `record.answer_text`；真实 DB + 离线 HTTP 复现中，200 / `no_hits` 因 `answer_text=null` 抛 `TypeError: 'NoneType' object is not subscriptable`，502 / `format_failed` 则以退出码 0 输出失败模型文本。`curl --fail-with-body` 仍会把错误 body 交给管道下游，不能替代状态判断。示例应先检查 status，成功时读取回答，空命中读取具体不足，失败读取安全说明并明确失败；兼容 422 `detail` 与 `record=null`。
3. **[P3] OpenAPI 缺少请求/响应示例**（`src/casetrace/api.py:78–136`、路由声明）。实际读取 `/openapi.json`：请求 body、请求模型和所有响应均无 example/examples。补最小有效请求与代表性成功/失败响应示例，满足“示例在 OpenAPI 中可见”的任务要求；不复制完整业务模型。

### Standards

未发现独立的阻塞性规范问题：本包复用既有核心、保持同步短连接与惰性模型工厂，未引入范围外组件。上述错误捕获范围及使用示例问题按 Spec 记录，不重复计数。

### 实际验证证据

- `uv run --locked pytest tests/api tests/answer tests/storage -q`：**256 passed / 0 skipped**，真实 PostgreSQL API 对照执行，包含 Q001～Q005 的排名、完整上下文、消息、回答及引用回放。
- `uv run --locked pytest -q`：**708 passed、169 subtests passed / 0 skipped**。现有测试通过，但未覆盖上述复现的错误类别与文档读取分支。
- `uv run --locked ruff check`、`uv lock --check`、`git diff --check` 通过。
- 实际以 Uvicorn 绑定本机临时端口：`/health` 200、`/openapi.json` 200 且列出 200/422/500/502/503、空白 query 422；检查后进程已停止。
- 独立复现使用测试库读回与离线模型/客户端构造；未修改 `.env` 或开发库，未产生真实模型调用。真实模型调用总数 **0**。软件等价证据不产生新的 AI 质量或 Ground Truth 结论。

### Codex 最小修复与复验

- **授权与范围：** 用户要求 Codex 直接修复，保持学习展示项目逻辑清晰、避免过重。按上方修复前快照比较，只改 API、核心三处快照异常标记、接口回归、运行/学习说明与验收状态；未新增依赖或改动业务检查、检索/模型策略。
- **错误分类修复：** `ValueError/OSError` 只在 `load_database_snapshot` 调用处映射数据库 503；核心已知身份/时点前提用单个 `SnapshotError(ValueError)` 标记并映射 503。模型构造、检索、响应输出等其它未预期异常走安全 500。只新增一个轻量异常类，复用原有三处检查，不复制校验或建设错误框架；CLI 原有 `ValueError` 捕获继续有效。
- **示例修复：** 文档读取器按 `ok/no_hits/其它失败` 分支，兼容 422 `detail` 与 `record=null`，失败返回非零退出码且不展示失败模型文本。OpenAPI 增加有效请求、成功/空命中与模型配置失败的简写示例，注明省略记录字段；502/503/500 复用已有响应外壳。同步学习速查说明。
- **新增回归：** 7 项 HTTP 用例覆盖工厂 `ValueError/OSError`、默认 SDK 无效代理、核心调用后 JSON 序列化错误、快照身份/时点失败仍为 503，以及 OpenAPI 示例。修复前新增检查为 **5 failed / 2 passed**；初修有 1 项 OpenAPI 检查失败（框架生成示例时省略 null 字段），改用含记录的模型配置失败示例，无自定义 OpenAPI 生成逻辑，最终全部通过。
- **最终 Spec：** 三项发现均已关闭。以真实测试库复现的默认模型无效代理现为 **500 / internal_error**；直接执行文档中同一读取器，200 成功/空命中为退出码 0，502 格式失败、503 前提失败、500 未预期错误、422 校验失败均为退出码 1，无 traceback 或失败模型文本展示。
- **最终 Standards：** 无独立阻塞问题。HTTP 适配仍复用同一回答核心、一次短连接和惰性模型；必要核心接缝只加异常标记，新增复杂度与已复现问题相称。
- **最终验证：** `uv run --locked pytest tests/api tests/answer tests/storage -q` → **263 passed / 0 skipped**（包含真实 PostgreSQL 五 Query 回放）；`uv run --locked pytest -q` → **715 passed、169 subtests passed / 0 skipped**；ruff、lock、diff 检查通过。实际 Uvicorn `/health` 200、含请求/响应示例的 `/openapi.json` 200、无效请求 422，随后停止进程。真实模型调用 **0**；未修改 `.env`、开发库或旧 AI 产物。
- **下一入口与教学：** M5-03 accepted，M5 工程交付完成；下一入口为按 Current Plan 准备 M6 Docker / 简单 Web Demo，本轮未实施 M6。已解释“按异常来源区分 HTTP 状态”及保持 CLI 兼容的原因；用户理解确认与后续代码教学仍单独记录。软件等价验证不产生新 AI 质量或 Ground Truth 结论。
