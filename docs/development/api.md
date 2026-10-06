# 回答 HTTP 接口（FastAPI）

M5-03 提供本机学习展示用的 HTTP 接口：把当前问题交给同一套回答核心（R3 检索 → 证据上下文 → 生成 → 引用守卫），返回可复查的完整运行记录。

范围与简化原则以 [Current Plan](../project/current-plan.md) 与 [M5-03 任务包](../project/tasks/m5-03-fastapi.md)为准：

- 只做 HTTP 适配，不改数据、qrels、检索、提示词或既有 CLI 行为；
- 固定走 PostgreSQL（连接沿用 `CASETRACE_DATABASE_URL` / 项目根 `.env`），schema 由服务端工厂配置；
- 客户端只提交问题，不提交连接、凭据、路径、schema、模型选择或数据源；
- 不含 CRUD、连接池、缓存、异步改造、流式响应、后台任务、认证或前端页面；默认只绑定 `127.0.0.1`。

## 安装与准备

```bash
uv sync --locked --inexact
```

数据库连接、初始化与导入见 [PostgreSQL 环境说明](postgresql.md)。回答路线要求目标 schema 已初始化并导入 dev-v3 快照：

```bash
uv run --locked python -m casetrace.storage init
uv run --locked python -m casetrace.storage import
```

## 启动与检查

```bash
uv run --locked uvicorn casetrace.api:app --host 127.0.0.1 --port 8000
curl --fail-with-body http://127.0.0.1:8000/health          # {"status":"ok"}
```

- `/health` 只证明 HTTP 进程能响应，不代表数据库或模型可用；
- `/docs` 交互文档、`/openapi.json` 契约（请求模型与 200/422/502/503/500 可见）。

## 请求

`POST /answer` 的 JSON 对象只有三个字段，额外字段拒绝（422）：

| 字段 | 约定 |
|---|---|
| `query` | 必填字符串，拒绝空白；原样传给核心，不改写、截断或反填 |
| `known_at` | 必填 `YYYY-MM-DD`；当前仅支持记录时点 `2026-09-15`，不接受时间戳或 datetime |
| `top_k` | 可省略，默认 4；严格正整数（拒绝 bool、小数、数字字符串） |

```bash
curl --fail-with-body http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  --data '{"query":"焊线脱落，已排除运输碰伤","known_at":"2026-09-15","top_k":4}'
```

正常路径会调用真实模型（需 `DEEPSEEK_API_KEY`，会计费）。

## 响应

顶层为 `status`、`message`、`record`；`record` 沿用完整的运行记录（排名、上下文、实际模型消息、回答、引用报告、来源身份与用量），可与 CLI `--json` 记录同样复查。读取示例：

```bash
curl --fail-with-body -sS http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  --data '{"query":"焊线脱落，已排除运输碰伤","known_at":"2026-09-15"}' \
  | python -c '
import json, sys
response = json.load(sys.stdin)
status = response.get("status")
print(status or "invalid_request")
if status == "ok":
    print(response["record"]["ranking"])
    print(response["record"]["answer_text"])
elif status == "no_hits":
    print(response["record"]["answer"]["insufficiency"])
else:
    print(response.get("message", response.get("detail", "请求失败")), file=sys.stderr)
    sys.exit(1)
'
```

`curl --fail-with-body` 会保留 HTTP 错误的 JSON；读取器先判断状态，只展示成功回答或空命中的具体不足，失败时打印说明并以非零退出码结束。422 使用 `detail`，数据库/未预期错误不读取空的 `record`。

HTTP 与 `status` 的映射：

| 情况 | HTTP | 响应 |
|---|---|---|
| `ok` | 200 | 成功记录与回答 |
| `no_hits` | 200 | 保留具体不足与空候选；不构造模型 |
| `model_failed`（`ModelConfigError`） | 503 | 服务端模型配置不可用 |
| 其它 `model_failed` / `format_failed` / `citation_failed` | 502 | 保留核心状态与失败证据 |
| 请求校验失败 | 422 | 框架 `detail`；不读数据库、不构造模型 |
| DB 配置／连接／未导入／快照前提失败 | 503 | `status=service_unavailable`、`record=null` |
| 未预期异常 | 500 | 通用安全说明，不暴露 traceback |

数据库读取错误在读库入口处理；核心中的快照身份/时点错误用 `SnapshotError` 标记并返回 503。模型构造、检索或响应输出阶段的其它未预期异常返回 500，不误报为数据库故障。

客户端以 HTTP 与 `status` 判断成功：格式／引用失败即使记录里带模型文本，也不能当成成功展示。模型失败记录里的 SDK 异常原文会在 HTTP 返回的副本中换成固定安全说明（保留错误类型、调用标记及其余证据）；`service_unavailable` 只是网络边界状态，不是核心业务状态。

## 边界与限制

- 回答是**历史参考**，不判断当前 Incident 的最终 Root Cause；引用可定位不等于引用支持原句，语义支持仍需人工审阅。
- 运行记录不产生新的 Ground Truth，也不升级 draft Case。
- 有效请求链路的验收证据用 `TestClient` + 真实 PostgreSQL + 离线模型完成（见 `tests/storage/test_api_integration.py`），不需要真实模型计费请求。

## 代码位置

| 位置 | 内容 |
|---|---|
| `src/casetrace/api.py` | `create_app`、默认 `app`、请求／响应模型与 `/health`、`/answer` |
| `tests/api/` | 无库、无模型的 HTTP 契约与离线状态映射 |
| `tests/storage/test_api_integration.py` | 真实 PostgreSQL 五 Query 回放与读取边界 |
