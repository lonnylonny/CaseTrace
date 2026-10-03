"""M4-02 生成契约与回答解析：结构化回答的数据类型、JSON 解析与真实生成入口。

分工：
- 契约、解析与错误类型是脚手架；`generate_grounded_answer` 是用户核心实践 B
  的主流程，函数主体待用户实现；
- 完整引用守卫（引用 ID 是否真实存在、字段归属）属于 M4-03，本包只做结构与类型校验；
- 解析失败与调用失败是不同状态：分别抛 AnswerFormatError 与 ModelCallError，
  都不伪装成成功，也不自动换模型重试。
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import json
import time
from typing import Any

from casetrace.answer.context import EvidenceContext, context_to_payload
from casetrace.answer.model import ChatModel, TokenUsage, ChatMessage
from casetrace.answer.prompt import PROMPT_VERSION, render_system_prompt





class AnswerFormatError(ValueError):
    """模型返回的内容不是约定的回答结构；不猜测、不修补，明确失败。

    模型在解析失败前已经返回的原始文本、模型身份、耗时与 token 用量是可复查的
    失败证据。这些信息随异常携带，供调用方写进失败记录，而不是在异常冒泡时丢失。
    直接调用 `parse_grounded_answer` 触发的结构错误没有这些元数据，属性为 None。
    """

    def __init__(
        self, message: str, *, raw_response: str | None = None,
        model_id: str | None = None, usage: TokenUsage | None = None,
        elapsed_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.model_id = model_id
        self.usage = usage
        self.elapsed_seconds = elapsed_seconds


@dataclass(frozen=True)
class HistoricalEvidence:
    """一条历史检查结果：必须带所属 Case 的 checkpoint_id 与结果原文。"""

    checkpoint_id: str
    result: str


@dataclass(frozen=True)
class SourceRef:
    """一条来源引用：case_id + 字段名（Detail 用 detail:<id>，检查用 checkpoint:<id>）。"""

    case_id: str
    field: str


@dataclass(frozen=True)
class CaseAnswer:
    """一条历史 Case 的回答：相关理由、历史原因、历史检查与来源。"""

    case_id: str
    relevance_reason: str
    # 相关理由必须同时指向 Query 已知事实与历史原文；解析时要求两者都非空。
    query_facts: tuple[str, ...]
    case_facts: tuple[str, ...]
    # 历史原因原文；没有记录时为 None，不得用当前未知原因填充。
    historical_root_cause: str | None
    historical_evidences: tuple[HistoricalEvidence, ...]
    sources: tuple[SourceRef, ...]
    # 缺失时为 None，以便回放 v1 记录；v2 提示词要求显式输出。
    historical_corrective_action: str | None = None


@dataclass(frozen=True)
class SkippedCandidate:
    """证据不足、未给出相关理由的候选；记录原因，避免静默丢弃。"""

    case_id: str
    reason: str


@dataclass(frozen=True)
class GroundedAnswer:
    """结构化回答：逐条历史 Case 的回答、跳过的候选、当前缺口与不足说明。"""

    case_answers: tuple[CaseAnswer, ...]
    skipped_candidates: tuple[SkippedCandidate, ...] = ()
    current_gaps: tuple[str, ...] = ()
    insufficiency: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    """一次生成的可检查结果：回答结构 + 可核对的运行身份。

    空上下文走不足结果时：called_model=False、model_id=None、raw_response=None、
    usage 为空值、elapsed_seconds=0.0，表示本次没有发生任何模型调用。

    `model_id` 记录供应商实际返回的模型身份（响应的 model 字段），不是请求里写的别名：
    别名会随官方更新指向其它版本，不能当作本次运行的版本证据。
    """

    answer: GroundedAnswer
    prompt_version: str
    called_model: bool
    model_id: str | None
    usage: TokenUsage
    elapsed_seconds: float
    raw_response: str | None


def _require_object(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        raise AnswerFormatError(f"{path} 必须是 JSON 对象，实际 {type(value).__name__}")
    return value


def _require_list(value: Any, path: str) -> list:
    if not isinstance(value, list):
        raise AnswerFormatError(f"{path} 必须是 JSON 数组，实际 {type(value).__name__}")
    return value


def _require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnswerFormatError(f"{path} 必须是非空字符串，实际 {value!r}")
    return value.strip()


def _optional_text(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, path)


def _require_text_list(value: Any, path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = [_require_text(item, f"{path}[{index}]")
             for index, item in enumerate(_require_list(value, path))]
    if not items and not allow_empty:
        raise AnswerFormatError(f"{path} 不能为空数组：相关理由必须同时给出 Query 与历史依据")
    return tuple(items)


def _parse_case_answer(value: Any, path: str, *, require_corrective_action: bool) -> CaseAnswer:
    item = _require_object(value, path)
    if require_corrective_action and "historical_corrective_action" not in item:
        raise AnswerFormatError(f"{path} 缺少必需键 historical_corrective_action")
    evidences = tuple(
        HistoricalEvidence(
            checkpoint_id=_require_text(
                _require_object(raw, f"{path}.historical_evidences[{index}]").get("checkpoint_id"),
                f"{path}.historical_evidences[{index}].checkpoint_id",
            ),
            result=_require_text(
                _require_object(raw, f"{path}.historical_evidences[{index}]").get("result"),
                f"{path}.historical_evidences[{index}].result",
            ),
        )
        for index, raw in enumerate(
            _require_list(item.get("historical_evidences", []), f"{path}.historical_evidences")
        )
    )
    sources = tuple(
        SourceRef(
            case_id=_require_text(
                _require_object(raw, f"{path}.sources[{index}]").get("case_id"),
                f"{path}.sources[{index}].case_id",
            ),
            field=_require_text(
                _require_object(raw, f"{path}.sources[{index}]").get("field"),
                f"{path}.sources[{index}].field",
            ),
        )
        for index, raw in enumerate(_require_list(item.get("sources"), f"{path}.sources"))
    )
    if not sources:
        raise AnswerFormatError(f"{path}.sources 不能为空数组：关键历史事实必须带来源引用")
    return CaseAnswer(
        case_id=_require_text(item.get("case_id"), f"{path}.case_id"),
        relevance_reason=_require_text(item.get("relevance_reason"), f"{path}.relevance_reason"),
        query_facts=_require_text_list(item.get("query_facts"), f"{path}.query_facts",
                                       allow_empty=False),
        case_facts=_require_text_list(item.get("case_facts"), f"{path}.case_facts",
                                      allow_empty=False),
        historical_root_cause=_optional_text(
            item.get("historical_root_cause"), f"{path}.historical_root_cause"
        ),
        historical_evidences=evidences,
        sources=sources,
        historical_corrective_action=_optional_text(
            item.get("historical_corrective_action"), f"{path}.historical_corrective_action"
        ),
    )


def _parse_skipped_candidate(value: Any, path: str) -> SkippedCandidate:
    item = _require_object(value, path)
    return SkippedCandidate(
        case_id=_require_text(item.get("case_id"), f"{path}.case_id"),
        reason=_require_text(item.get("reason"), f"{path}.reason"),
    )


def parse_grounded_answer(text: str, *, require_corrective_action: bool = False) -> GroundedAnswer:
    """解析模型返回的 JSON 到回答结构；不合法就抛 AnswerFormatError。

    必需键：`case_answers`（可为空数组）；`skipped_candidates`、`current_gaps`
    缺失时取空值，`insufficiency` 缺失时取 None。未知键按契约外内容忽略，
    真正的引用与字段存在性由 M4-03 的引用守卫检查。默认兼容 v1 回放；
    v2 生成必须显式给出 historical_corrective_action（允许 null）。
    """

    if not isinstance(text, str) or not text.strip():
        raise AnswerFormatError("回答文本为空，无法解析")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnswerFormatError(f"回答不是合法 JSON：{exc}") from exc
    root = _require_object(payload, "回答 JSON 顶层")
    if "case_answers" not in root:
        raise AnswerFormatError("回答 JSON 缺少必需键 case_answers")
    return GroundedAnswer(
        case_answers=tuple(
            _parse_case_answer(item, f"case_answers[{index}]",
                               require_corrective_action=require_corrective_action)
            for index, item in enumerate(_require_list(root["case_answers"], "case_answers"))
        ),
        skipped_candidates=tuple(
            _parse_skipped_candidate(item, f"skipped_candidates[{index}]")
            for index, item in enumerate(
                _require_list(root.get("skipped_candidates", []), "skipped_candidates")
            )
        ),
        current_gaps=_require_text_list(root.get("current_gaps", []), "current_gaps"),
        insufficiency=_optional_text(root.get("insufficiency"), "insufficiency"),
    )


def generate_grounded_answer(
    query: str, context: EvidenceContext, model: ChatModel,
    *, on_messages: Callable[[Sequence[ChatMessage]], None] | None = None,
) -> GenerationResult:
    """用户核心实践 B：把 Query 与证据组装成消息、调用模型并解析成回答结构。

    实现要求（测试按这些行为检查，不绑定内部写法）：

    1. 真实调用路径发送的是**原始 Query 全文**（含否定条件、批号等被检索删掉的词）
       与 `context` 内允许的证据；不重新检索、不按 qrels 筛选、不补其它 Case；
    2. 证据只作数据；发送内容里不得出现生成／审阅元数据
       （如来源的 generation_note、rationale、review_status）或标注理由；
    3. `context.cases` 为空时**不调用模型**，直接返回明确的不足结果：
       `called_model=False`、`raw_response=None`、`model_id=None`、
       `answer.case_answers == ()`，且 `answer.insufficiency` 说明具体缺口；
    4. 结构不合法抛 `AnswerFormatError`；调用失败让 `ModelCallError` 继续向上传播：
       模型错误与无证据是不同状态，都不伪装成成功、也不悄悄换模型。

    可用积木：`prompt.render_system_prompt()`（渲染版本化系统提示）、
    `context.context_to_payload()`（上下文 JSON）、`parse_grounded_answer()`（解析）。
    消息形态示例（顺序与包装方式由你决定）：

        [system] render_system_prompt()
        [user]   当前 Query 原文 + 证据 JSON
    """
    if context.cases == []:
        return GenerationResult(
            answer=GroundedAnswer(
                case_answers=(),
                insufficiency="缺少可用历史 Case 证据，无法生成相关理由与历史原因",
            ),
            prompt_version=PROMPT_VERSION,
            called_model=False,
            model_id=None,
            usage=TokenUsage(),
            elapsed_seconds=0.0,
            raw_response=None,
        )
    else:
        system_prompt = render_system_prompt()
        user_payload = context_to_payload(context)
        # 字典直接塞进 f-string 会变成 Python repr（单引号、True），不是合法 JSON。
        user_message = f"{query}\n\n{json.dumps(user_payload, ensure_ascii=False)}"
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        # 在真实调用前保存同一份消息；调用或解析失败也不会丢失请求证据。
        if on_messages is not None:
            on_messages(messages)
        # 计时只包住模型调用本身：解析耗时不算「问模型花了多久」。
        start = time.perf_counter()
        response = model.complete(messages)
        elapsed = time.perf_counter() - start
        try:
            answer = parse_grounded_answer(response.text, require_corrective_action=True)
        except AnswerFormatError as error:
            # 解析失败前模型已经返回了文本与身份/用量/耗时：保留这些失败证据再抛出。
            error.raw_response = response.text
            error.model_id = response.model
            error.usage = response.usage
            error.elapsed_seconds = elapsed
            raise

        return GenerationResult(
            answer=answer,
            prompt_version=PROMPT_VERSION,
            called_model=True,
            # 运行身份取供应商实际返回的模型身份，不记请求别名。
            model_id=response.model,
            usage=response.usage,
            elapsed_seconds=elapsed,
            raw_response=response.text,
        )
