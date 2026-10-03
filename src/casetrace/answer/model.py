"""M4-02 窄模型调用接口：DeepSeek 适配、明确错误与离线替身。

这一层只负责「把 messages 发出去、把文本／模型身份／用量收回来」：
提示词组装在 prompt.py，回答解析在 generation.py，完整引用守卫在 M4-03。
凭据只在运行时从环境变量读取，不写入源码、日志或运行产物；
调用不做无界重试（SDK 重试显式关掉），失败原样暴露，不悄悄换模型。

DeepSeek 官方依据（2026-10-02 核对）：
- Chat Completions：https://api-docs.deepseek.com/api/create-chat-completion/
- 思考模式（默认开启，需显式关闭）：https://api-docs.deepseek.com/zh-cn/guides/thinking_mode
- JSON Output（要求 prompt 含 json 字样）：https://api-docs.deepseek.com/zh-cn/guides/json_mode
"""

from collections.abc import Sequence
from dataclasses import dataclass
import os
from typing import Any, Protocol

from casetrace.env import load_local_env

# DeepSeek 官方 OpenAI 兼容入口与首版固定模型；别名会随官方更新，实际身份以返回的 model 为准。
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
API_KEY_ENV = "DEEPSEEK_API_KEY"

# 首版固定非思考模式：thinking 默认开启，必须显式关闭；关闭后 temperature 才生效。
# 通过 OpenAI SDK 传 thinking 需要放进 extra_body（官方「思考模式」说明）。
NON_THINKING_EXTRA_BODY = {"thinking": {"type": "disabled"}}
# 限制输出长度，避免 JSON 被截断或非预期膨胀；本阶段不做多轮自动重试。
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT_SECONDS = 120.0


class ModelError(RuntimeError):
    """模型相关错误的基类，便于调用方统一区分「环境问题」与「调用失败」。"""


class ModelConfigError(ModelError):
    """凭据或客户端配置缺失：属环境问题，不重试、不换模型。"""


class ModelCallError(ModelError):
    """调用失败或返回不可用（空内容、被截断）：原样暴露，不伪装成成功。"""


@dataclass(frozen=True)
class ChatMessage:
    """一条对话消息；只支持本阶段用到的 system / user 两种角色。"""

    role: str
    content: str


@dataclass(frozen=True)
class TokenUsage:
    """一次调用的 token 用量；供应商未返回时为 None，不用 0 冒充实测值。"""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class ModelResponse:
    """一次模型调用的结果：文本 + 实际模型身份与用量，供运行记录复现。"""

    text: str
    model: str
    usage: TokenUsage
    finish_reason: str | None = None


class ChatModel(Protocol):
    """生成流程只依赖这一层：给定 messages，取回文本、模型身份与用量。"""

    model_id: str

    def complete(
        self, messages: Sequence[ChatMessage], *,
        max_tokens: int | None = None, temperature: float | None = None,
    ) -> ModelResponse: ...


def _to_model_response(response: Any) -> ModelResponse:
    """把 OpenAI 兼容返回转成本项目的窄响应；不可用时明确失败。"""

    choices = getattr(response, "choices", None)
    if not choices:
        raise ModelCallError("DeepSeek 返回没有 choices，无法得到回答文本")
    choice = choices[0]
    message = getattr(choice, "message", None)
    text = (getattr(message, "content", None) or "").strip()
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason == "length":
        raise ModelCallError(
            f"输出被 max_tokens 截断（finish_reason=length），JSON 可能不完整：{text[:80]!r}"
        )
    if not text:
        # 官方说明 JSON Output 有概率返回空 content；这是失败，不是「没有内容可说」。
        raise ModelCallError("DeepSeek 返回空内容（JSON Output 存在偶发空 content），本次不算成功")
    usage = getattr(response, "usage", None)
    return ModelResponse(
        text=text,
        model=getattr(response, "model", None) or "unknown",
        usage=TokenUsage(
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        ),
        finish_reason=finish_reason,
    )


def _build_client(api_key: str, base_url: str, timeout: float):
    """构造 OpenAI 兼容客户端；SDK 缺失时给出可操作的配置错误。"""

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - 依赖缺失属环境问题
        raise ModelConfigError(
            "缺少 openai SDK：请用 uv sync 安装项目依赖（DeepSeek 官方要求使用 OpenAI 兼容 SDK）"
        ) from exc
    # max_retries=0：本阶段不做无界重试，失败要如实暴露。
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)


class DeepSeekChatModel:
    """DeepSeek 官方 OpenAI 兼容 Chat 接口：固定非思考模式 + JSON Output。"""

    def __init__(
        self, *, model: str = DEFAULT_MODEL, api_key: str | None = None,
        base_url: str = DEEPSEEK_BASE_URL, client: Any = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self.model_id = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        if client is None:
            if api_key is None:
                # 环境变量优先，项目根 .env 兜底；.env 由 .gitignore 忽略，凭据不入库。
                load_local_env()
            key = api_key or os.environ.get(API_KEY_ENV)
            if not key or not key.strip():
                raise ModelConfigError(
                    f"缺少 DeepSeek 凭据：请在本机设置环境变量 {API_KEY_ENV}；"
                    "凭据不写入源码、日志或运行产物"
                )
            client = _build_client(key, base_url, timeout)
        self._client = client

    def complete(
        self, messages: Sequence[ChatMessage], *,
        max_tokens: int | None = None, temperature: float | None = None,
    ) -> ModelResponse:
        request = {
            "model": self.model_id,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            # JSON Output：官方要求 prompt 含 json 字样并给出结构样例，模板已满足。
            "response_format": {"type": "json_object"},
            "extra_body": dict(NON_THINKING_EXTRA_BODY),
        }
        try:
            response = self._client.chat.completions.create(**request)
        except Exception as exc:  # 供应商 SDK 异常类型多，统一转成本项目错误并保留原因
            raise ModelCallError(f"DeepSeek 调用失败：{type(exc).__name__}: {exc}") from exc
        return _to_model_response(response)


class OfflineChatModel:
    """离线替身：回放固定文本并记录收到的 messages；不联网、不需要凭据。

    用于软件测试与离线演练，`calls` 记录实际发送内容以便断言；
    它不能替代真实模型运行证据，也不能用来宣称生成链路已经跑通。
    """

    def __init__(
        self, response_text: str, *, model_id: str = "offline-stub",
        usage: TokenUsage | None = None,
    ) -> None:
        self.response_text = response_text
        self.model_id = model_id
        self.usage = usage or TokenUsage()
        self.calls: list[dict] = []

    def complete(
        self, messages: Sequence[ChatMessage], *,
        max_tokens: int | None = None, temperature: float | None = None,
    ) -> ModelResponse:
        self.calls.append({
            "messages": [ChatMessage(item.role, item.content) for item in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return ModelResponse(
            text=self.response_text, model=self.model_id, usage=self.usage,
            finish_reason="stop",
        )

    def sent_text(self) -> str:
        """累计发给模型的全部文本；测试据此检查输入内容，而不是精确匹配整篇回答。"""

        return "\n".join(item.content for call in self.calls for item in call["messages"])
