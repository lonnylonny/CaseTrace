# FastAPI 识图卡（CaseTrace M5-03 学习辅助）

本文件用于**认出** `src/casetrace/api.py` 的写法，不替代代码与官方文档。示例行号随代码演进会失效，以源码为准；口径与范围以 [Current Plan](../project/current-plan.md) 与 [M5-03 任务包](../project/tasks/m5-03-fastapi.md)为准。

用法：看不懂某一行时，先问两件事 —— **它是"定义"还是"使用"？它属于"门口(HTTP)"还是"车间(业务核心)"？**

## 1. 一次请求的生命周期（背这一段就够）

```
HTTP 请求 → 按路径匹配函数 → Pydantic 校验/解析请求体 → 调用你的函数 → 按 response_model 转成 JSON → HTTP 响应
```

校验不通过 → 422，**函数根本不执行**。

## 2. `api.py` 结构速查

| 看到 | 读成 | 位置 |
|---|---|---|
| `class AnswerRequest(BaseModel)` | 请求体"模板"：定义字段与规则 | `api.py` 请求模型 |
| `class AnswerResponse(BaseModel)` | 响应"外壳"：`status` / `message` / `record` | `api.py` 响应模型 |
| `def create_app(...) -> FastAPI` | 造应用的**函数**（不是应用本身） | `api.py` 工厂 |
| `app = create_app()` | 模块级默认应用，供 uvicorn 使用 | `api.py` 末尾 |
| `app.state.xxx = ...` | 挂在应用上的**配置储物柜** | 工厂内 |
| `@app.get("/health")` / `@app.post("/answer")` | 路由：URL+方法 → 函数 | 工厂内 |
| `def health() -> HealthResponse` | 普通函数，返回固定对象 | `api.py` |
| `def answer(request: AnswerRequest)` | 请求实例由**框架运行时**构造，不是你建的 | `api.py` |
| `response_model=...` | 返回对象 → JSON 的转换规则 | 路由装饰器 |

**关键区分**：类是你写的（规则），实例是 FastAPI 每次收请求时造的（数据）。

## 3. `create_app` 的三条逻辑

| 代码 | 作用 | 为什么 |
|---|---|---|
| `create_app(*, db_schema=..., model_factory=...)` | `*` 后面只能按名字传参 | 防止位置传参传错 |
| `model_factory or (lambda: build_model(DEFAULT_MODEL))` | 工厂**惰性**：调用时才真的造模型 | 直接写 `build_model(...)` 会在导入时就造模型，违反约定 |
| `app.state.db_schema / model_factory` | 存配置，供路由读取 | 配置与使用配置的代码分离 |

约定：**应用创建、模块导入、`/health` 都不连接数据库、不构造模型。**

## 4. Pydantic 速查

| 看到 | 读成 |
|---|---|
| `model_config = ConfigDict(extra="forbid")` | 多出未声明字段 → 拒绝（422） |
| `query: str = Field(min_length=1)` | 必须是非空字符串 |
| `top_k: StrictInt = Field(default=4, gt=0)` | 严格整数、大于 0、可省略 |
| `known_at: date` | 日期类型 |

`StrictInt` 的"严格"：

| 输入 | 普通 `int` | `StrictInt` |
|---|---|---|
| `4` | ✅ | ✅ |
| `4.0` | ✅（偷偷转） | ❌ |
| `"4"` | ✅（偷偷转） | ❌ |
| `true` | ✅（当 1） | ❌ |

校验器（`@field_validator`）插入的阶段：

| 写法 | 何时跑 | 拿到什么值 | 用途 |
|---|---|---|---|
| `mode="before"` | 类型转换**前** | 原始 JSON 值 | 卡死格式（如必须 `YYYY-MM-DD` 文本） |
| 默认（无 `mode`） | 类型转换**后** | 已转换的 Python 值 | 查业务（如日期是否等于快照日期） |

为何 `known_at` 要在 `before` 卡格式：Pydantic 的 `date` 类型自己也会接受 `2026-09-15T00:00:00` 与时间戳，先转换就会被偷偷放行。

## 5. `POST /answer` 状态映射（SD2）

| `outcome.status` | HTTP | 响应 |
|---|---|---|
| `ok` | 200 | 完整记录 + 回答 |
| `no_hits` | 200 | 保留空候选；**没调模型** |
| `model_failed` 且 `error.type == ModelConfigError` | 503 | 服务端模型配置问题 |
| 其它 `model_failed` | 502 | 模型调用失败 |
| `format_failed` | 502 | 模型返回格式坏 |
| `citation_failed` | 502 | 引用校验失败 |
| （无 outcome）DB 读回或快照前提失败 | 503 | `status="service_unavailable"`、`record=null` |
| 请求校验失败 | 422 | 框架 `detail`（SD1 已有） |
| 未预期异常 | 500 | 通用安全说明，不暴露 traceback |

有无 `record` 的分界：

| 情况 | `record` | 原因 |
|---|---|---|
| DB / 快照前提失败 | `null` | 读库失败或核心在生成运行记录前拒绝快照 |
| 未预期异常 | `null` | 本次流程未完成，按安全 500 返回 |
| 模型/格式/引用失败 | 存在 | 核心跑过了，保留失败证据 |

脱敏：模型失败记录里 SDK 异常原文在 `error.message`，HTTP 返回**副本**时换成固定安全文案（保留 `error.type`），不改核心对象与 CLI；凭据不进产物。

异常按来源区分：读库入口的 `ValueError/OSError` 返回 503；核心明确抛出的 `SnapshotError` 也返回 503；其它未预期异常返回 500。`SnapshotError` 继承 `ValueError`，CLI 原有捕获仍有效；不按异常文本猜来源。客户端的完整状态判断示例见 [API 运行说明](../development/api.md#响应)。

## 6. 本项目命令速查

```bash
# 启动（本机学习用，默认绑定 127.0.0.1）
uv run --locked uvicorn casetrace.api:app --host 127.0.0.1 --port 8000

# 存活检查（不代表 DB / 模型可用）
curl --fail-with-body http://127.0.0.1:8000/health

# 回答请求（需已导入 DB 与模型凭据；正常路径会调用真实模型）
curl --fail-with-body http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  --data '{"query":"焊线脱落，已排除运输碰伤","known_at":"2026-09-15","top_k":4}'
```

其他入口：`/docs`（交互文档）、`/openapi.json`（契约）。

## 7. 常见错误 Top 5

1. **以为 `request` 是自己造的**：它是 FastAPI 运行时按类构造的实例。
2. **`known_at` 用时间戳/datetime**：会在 `before` 阶段被拒，别指望 `date` 帮你兜。
3. **`top_k` 传 `"4"` 或 `4.0`**：`StrictInt` 拒绝，不带自动转换。
4. **给请求多塞字段**：`extra="forbid"` 直接 422。
5. **把校验通过当成业务成功**：校验通过只是进了函数；真正的失败用 `status`／HTTP 状态表达，不会伪装成 `ok`。

## 8. 位置速查

| 位置 | 内容 |
|---|---|
| `src/casetrace/api.py` | `create_app`、`app`、`AnswerRequest`、`AnswerResponse`、`/health`、`/answer` |
| `tests/api/test_answer_api.py` | health、OpenAPI 契约、16 类无效请求 422；SD2 的 200/502/503/500 映射、脱敏与两次请求独立 |
| `tests/api/conftest.py` | 合成 `LoadedSnapshot`，模拟一次数据库读回（离线，不连库） |
| `src/casetrace/answer/cli.py` | 业务核心 `run_answer_question`、`load_database_snapshot`、`build_model`、`AnswerOutcome` |
| `docs/project/tasks/m5-03-fastapi.md` | 接口契约、SD1～SD3 范围与验收 |
| `docs/development/postgresql.md` | 连接、初始化与导入 |
