"""M5-03 FastAPI：把已验收的回答核心接到本机 HTTP 边界。

本模块只做 HTTP 适配：请求字段校验、服务端连接配置、JSON 输出与状态映射。
检索、证据上下文、生成与引用守卫仍在 `answer` 核心（`run_answer_question`）里，
API 不复制业务流程，也不改数据、qrels 或既有 CLI 行为。

任务包约定的边界（docs/project/tasks/m5-03-fastapi.md）：

- 服务固定走 PostgreSQL：连接沿用 `CASETRACE_DATABASE_URL` / 项目根 `.env`，
  schema 由应用工厂配置；客户端只提交问题，不提交连接、凭据、路径、schema、
  模型选择或数据源。
- 应用创建、模块导入与 `GET /health` 都不连接数据库、不构造模型；模型只在核心
  确需生成时才由注入的工厂构造。
- `POST /answer` 的请求体只有 `query`、`known_at`、`top_k` 三个字段，额外字段拒绝。

接口与真实 PostgreSQL 五 Query 回放的验收记录见任务包。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
import re

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from casetrace.answer.cli import (
    STATUS_CITATION_FAILED,
    STATUS_FORMAT_FAILED,
    STATUS_MODEL_FAILED,
    STATUS_NO_HITS,
    STATUS_OK,
    AnswerOutcome,
    build_model,
    load_database_snapshot,
    run_answer_question,
)
from casetrace.answer.context import DEFAULT_TOP_K, DEV_V3_SNAPSHOT, SnapshotError
from casetrace.answer.model import DEFAULT_MODEL, ChatModel, ModelConfigError
from casetrace.storage.schema import DEFAULT_SCHEMA

# 模型工厂：核心在确需生成时才调用它；应用创建、health 与无效请求都不构造模型。
ModelFactory = Callable[[], ChatModel]

# `known_at` 只接受严格的 YYYY-MM-DD 文本；Pydantic 的 date 类型本身也会接受
# datetime 字符串与 Unix 时间戳，这里显式收窄到约定格式，避免把时间戳当日期。
_DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")

API_TITLE = "CaseTrace Answer API"
API_DESCRIPTION = (
    "把当前问题交给固定 R3 检索 + Grounded Answer 核心，返回可复查的完整运行记录。"
    "本机学习展示用；回答是历史参考，不判断当前 Incident 的最终 Root Cause。"
)


class HealthResponse(BaseModel):
    """`GET /health` 的响应；只证明 HTTP 进程能响应，不代表数据库或模型可用。"""

    status: str = "ok"


class AnswerResponse(BaseModel):
    """`POST /answer` 的响应外壳。

    顶层 `status` 与 `record["status"]` 一致；`record` 沿用核心的完整运行记录，
    不在这里逐层复制 dataclass 或业务模型。数据库前提失败时 `record` 为 null。
    """

    status: str
    message: str
    record: dict | None = None


class AnswerRequest(BaseModel):
    """`POST /answer` 的请求体：只有三个字段，额外字段一律拒绝（422）。

    `query` 保留原始文本，不改写、截断或从历史反填；`known_at` 引用现有快照常量，
    当前仅支持 `DEV_V3_SNAPSHOT.known_at`；`top_k` 是严格正整数，默认 4。
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{
            "query": "焊线脱落，已排除运输碰伤",
            "known_at": DEV_V3_SNAPSHOT.known_at.isoformat(), "top_k": DEFAULT_TOP_K,
        }]},
    )

    query: str = Field(
        min_length=1,
        description="当前问题原文；原样传给核心，不改写、不截断",
    )
    known_at: date = Field(
        description="语料可用时点 YYYY-MM-DD；当前仅支持 "
                    f"{DEV_V3_SNAPSHOT.known_at.isoformat()}",
    )
    top_k: StrictInt = Field(
        default=DEFAULT_TOP_K,
        gt=0,
        description=f"阅读前 k 条候选；默认 {DEFAULT_TOP_K}，必须为正整数",
    )

    @field_validator("query")
    @classmethod
    def _reject_blank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query 不能是空白字符串")
        return value

    @field_validator("known_at", mode="before")
    @classmethod
    def _require_date_value(cls, value: object) -> object:
        # 只接受 YYYY-MM-DD 文本或真正的 date；datetime 与时间戳在这里拒绝。
        if isinstance(value, datetime):
            raise ValueError("known_at 只接受日期，不接受 datetime")
        if isinstance(value, date):
            return value
        if isinstance(value, str) and _DATE_TEXT.fullmatch(value):
            return value
        raise ValueError("known_at 必须是 YYYY-MM-DD 日期字符串")

    @field_validator("known_at")
    @classmethod
    def _reject_unsupported_known_at(cls, value: date) -> date:
        if value != DEV_V3_SNAPSHOT.known_at:
            raise ValueError(f"当前仅支持 known_at={DEV_V3_SNAPSHOT.known_at.isoformat()}")
        return value


# HTTP 边界状态：`service_unavailable`/`internal_error` 只用于网络边界，
# 不加入 `AnswerOutcome` 或 CLI 退出码，核心业务状态保持原样。
SERVICE_UNAVAILABLE = "service_unavailable"
INTERNAL_ERROR = "internal_error"

# 数据库前提失败（配置／连接／未导入／内容或快照不符）统一给安全、可操作的说明，
# 不回显连接串或原始异常。
DB_PREREQUISITE_MESSAGE = (
    "数据库路线暂不可用：请确认 CASETRACE_DATABASE_URL、数据库连接与初始化／导入状态后重试。"
)
UNEXPECTED_MESSAGE = "服务端发生未预期错误，本次请求未完成；请稍后重试。"
MODEL_CONFIG_MESSAGE = "服务端模型凭据或客户端配置不可用，本次没有发生模型调用。"
MODEL_FAILURE_MESSAGE = "模型调用失败（超时／权限／网络或返回不可用）；原始异常文本未在此返回。"
FORMAT_FAILURE_MESSAGE = "模型返回内容不符合回答契约；原始异常文本未在此返回。"
CITATION_FAILURE_MESSAGE = "回答里的引用无法在本次上下文中定位；原始异常文本未在此返回。"

# 示例只展示响应外壳与部分记录字段；运行时仍返回完整核心记录。
ANSWER_RESPONSES = {
    200: {
        "description": "成功或空命中；示例中的 record 省略其余运行记录字段",
        "content": {"application/json": {"examples": {
            "ok": {"summary": "成功（记录简写）", "value": {
                "status": STATUS_OK, "message": "引用校验通过；回答仅供历史参考",
                "record": {"status": STATUS_OK},
            }},
            "no_hits": {"summary": "空命中，不调用模型（记录简写）", "value": {
                "status": STATUS_NO_HITS, "message": "没有候选历史案例，未调用模型",
                "record": {
                    "status": STATUS_NO_HITS, "ranking": [], "answer_text": None,
                    "answer": {"case_answers": [], "insufficiency": "缺少可用历史案例证据"},
                },
            }},
        }}},
    },
    422: {"description": "请求校验失败：不读数据库、不构造模型"},
    502: {"model": AnswerResponse,
          "description": "模型调用、返回格式或引用校验失败：保留核心状态与失败证据"},
    503: {
        "model": AnswerResponse,
        "description": "模型配置不可用（model_failed），或数据库/快照前提失败"
                       "（service_unavailable、record=null）；示例中的 record 省略其余字段",
        "content": {"application/json": {"example": {
            "status": STATUS_MODEL_FAILED, "message": MODEL_CONFIG_MESSAGE,
            "record": {
                "status": STATUS_MODEL_FAILED,
                "error": {"type": "ModelConfigError", "message": MODEL_CONFIG_MESSAGE},
                "response": {"called_model": False},
            },
        }}},
    },
    500: {"model": AnswerResponse,
          "description": "未预期异常：通用安全说明，不暴露 traceback 或原始异常文本"},
}

# 核心失败状态 → HTTP 状态与固定安全说明；说明与状态保持一致。
FAILURE_HTTP_STATUS = {
    STATUS_MODEL_FAILED: 502,
    STATUS_FORMAT_FAILED: 502,
    STATUS_CITATION_FAILED: 502,
}
FAILURE_SAFE_MESSAGE = {
    STATUS_MODEL_FAILED: MODEL_FAILURE_MESSAGE,
    STATUS_FORMAT_FAILED: FORMAT_FAILURE_MESSAGE,
    STATUS_CITATION_FAILED: CITATION_FAILURE_MESSAGE,
}


def _json_response(status_code: int, status: str, message: str,
                   record: dict | None) -> JSONResponse:
    """统一的响应外壳：顶层 status／message 与 record 内的状态一一对应。"""

    return JSONResponse(
        status_code=status_code,
        content={"status": status, "message": message, "record": record},
    )


def _redacted_record(record: dict, message: str) -> dict:
    """返回记录副本并把 `error.message` 换成固定安全说明。

    模型失败记录含 SDK 异常原文；这里只改副本，不修改核心对象、不改变既有 CLI 行为，
    错误类型、调用标记与其余证据（ranking／context／messages／answer_text 等）原样保留。
    """

    safe = dict(record)
    error = safe.get("error")
    if isinstance(error, dict):
        safe["error"] = {**error, "message": message}
    return safe


def _outcome_response(outcome: AnswerOutcome) -> JSONResponse:
    """把 `AnswerOutcome` 映射成 JSON 与 HTTP 状态。

    - `ok`／`no_hits`：200，返回完整记录；空命中不构造模型。
    - `ModelConfigError` 导致的 `model_failed`：503，服务端模型配置不可用。
    - 其余 `model_failed`／`format_failed`／`citation_failed`：502，保留核心状态与证据。
    - 未知状态：不伪装成业务状态，按未预期异常处理。
    """

    if outcome.status in (STATUS_OK, STATUS_NO_HITS):
        return _json_response(200, outcome.status, outcome.message, outcome.record)
    if outcome.status not in FAILURE_SAFE_MESSAGE:
        return _json_response(500, INTERNAL_ERROR, UNEXPECTED_MESSAGE, None)
    error_type = (outcome.record.get("error") or {}).get("type")
    if outcome.status == STATUS_MODEL_FAILED and error_type == ModelConfigError.__name__:
        return _json_response(503, outcome.status, MODEL_CONFIG_MESSAGE,
                              _redacted_record(outcome.record, MODEL_CONFIG_MESSAGE))
    message = FAILURE_SAFE_MESSAGE[outcome.status]
    return _json_response(FAILURE_HTTP_STATUS[outcome.status], outcome.status, message,
                          _redacted_record(outcome.record, message))


def create_app(
    *, db_schema: str = DEFAULT_SCHEMA, model_factory: ModelFactory | None = None,
) -> FastAPI:
    """构造一个 FastAPI 应用；不连接数据库、不构造模型。

    `db_schema` 由服务端配置（客户端不可提交）；`model_factory` 是可调用对象，
    核心在确需生成时才调用它，默认复用 `build_model(DEFAULT_MODEL)`。
    """

    app = FastAPI(title=API_TITLE, version="0.1.0", description=API_DESCRIPTION)
    # 配置只挂在 app.state：写到哪、路由就从哪读，避免出现第二份会漂移的来源。
    app.state.db_schema = db_schema
    app.state.model_factory = model_factory or (lambda: build_model(DEFAULT_MODEL))

    @app.get("/health", response_model=HealthResponse, summary="进程存活检查")
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/answer", response_model=AnswerResponse, responses=ANSWER_RESPONSES,
        summary="回答一个历史案例检索问题",
    )
    def answer(request: AnswerRequest) -> JSONResponse:
        # 请求已通过 Pydantic 校验；这里固定走 PostgreSQL，一次短连接读回快照，
        # 关闭连接后再把同一对象与原始 query／日期／top_k 交给回答核心。
        try:
            schema = app.state.db_schema
            try:
                loaded = load_database_snapshot(schema)
            except (ValueError, OSError):
                # 只在读库入口捕获配置、连接、未导入或内容检查失败。
                return _json_response(503, SERVICE_UNAVAILABLE, DB_PREREQUISITE_MESSAGE, None)
            outcome = run_answer_question(
                request.query, request.known_at,
                model_factory=app.state.model_factory, query_id=None, top_k=request.top_k,
                loaded_snapshot=loaded, db_schema=schema,
            )
            return _outcome_response(outcome)
        except SnapshotError:
            # 核心明确拒绝快照身份或时点；其它 ValueError/OSError 留给 500 兜底。
            return _json_response(503, SERVICE_UNAVAILABLE, DB_PREREQUISITE_MESSAGE, None)
        except Exception:
            # 兜底：不暴露 traceback 或原始异常文本，也不伪装成业务状态。
            return _json_response(500, INTERNAL_ERROR, UNEXPECTED_MESSAGE, None)

    return app


app = create_app()
