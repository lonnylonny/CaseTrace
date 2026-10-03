"""M4-02 模型接口：请求参数、返回解析、明确错误与离线替身。

这里不访问网络、不需要凭据：用注入的假客户端与真实 SDK 返回对象检查调用边界。
真实 DeepSeek 调用证据在子交付 3 单独记录，不能用本文件替代。
"""

from types import SimpleNamespace

import pytest
from openai.types.chat import ChatCompletion

from casetrace.answer.model import (
    API_KEY_ENV,
    DEFAULT_MODEL,
    ChatMessage,
    DeepSeekChatModel,
    ModelCallError,
    ModelConfigError,
    OfflineChatModel,
    TokenUsage,
)

MESSAGES = [ChatMessage("system", "系统提示"), ChatMessage("user", "用户消息")]


def completion(content="{}", *, finish_reason="stop", model="deepseek-flash"):
    """构造真实的 OpenAI SDK 返回对象，避免只测自造的鸭子类型。"""

    return ChatCompletion.model_validate({
        "id": "chatcmpl-test", "object": "chat.completion", "created": 1, "model": model,
        "choices": [{
            "index": 0, "finish_reason": finish_reason,
            "message": {"role": "assistant", "content": content},
        }],
        "usage": {
            "prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33,
            "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 11,
        },
    })


class FakeCompletions:
    """记录请求参数并返回预设响应（或抛预设异常）的替身；不联网。"""

    def __init__(self, *, response=None, error=None):
        self.requests = []
        self._response = response
        self._error = error

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def fake_model(*, response=None, error=None, **kwargs):
    """返回（注入了假客户端的模型, 请求记录）；凭据与网络都不参与。"""

    completions = FakeCompletions(response=response, error=error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return DeepSeekChatModel(client=client, **kwargs), completions


def test_requires_credentials_from_environment(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(ModelConfigError, match=API_KEY_ENV):
        DeepSeekChatModel()


def test_reads_credentials_from_environment(monkeypatch):
    """凭据只从环境变量读取；构造客户端不发请求，所以不需要真实 Key。"""

    monkeypatch.setenv(API_KEY_ENV, "test-key-not-used")
    model = DeepSeekChatModel()
    assert model.model_id == DEFAULT_MODEL
    assert model.max_tokens > 0


def test_sends_non_thinking_json_request():
    model, completions = fake_model(response=completion('{"ok": true}'))
    response = model.complete(MESSAGES)

    assert len(completions.requests) == 1
    request = completions.requests[0]
    assert request["model"] == DEFAULT_MODEL
    assert request["messages"] == [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "用户消息"},
    ]
    assert request["response_format"] == {"type": "json_object"}
    # 非思考模式必须显式关闭；否则 temperature 不生效，行为也会变。
    assert request["extra_body"] == {"thinking": {"type": "disabled"}}
    assert request["max_tokens"] == model.max_tokens
    assert request["temperature"] == model.temperature

    assert response.text == '{"ok": true}'
    assert response.model == "deepseek-flash"
    assert response.usage == TokenUsage(prompt_tokens=11, completion_tokens=22, total_tokens=33)
    assert response.finish_reason == "stop"


def test_reports_truncated_output():
    model, _ = fake_model(response=completion("{", finish_reason="length"))
    with pytest.raises(ModelCallError, match="截断"):
        model.complete(MESSAGES)


def test_reports_empty_content():
    model, _ = fake_model(response=completion("   "))
    with pytest.raises(ModelCallError, match="空内容"):
        model.complete(MESSAGES)


def test_wraps_provider_failure_and_keeps_cause():
    model, _ = fake_model(error=RuntimeError("boom"))
    with pytest.raises(ModelCallError, match="调用失败") as excinfo:
        model.complete(MESSAGES)
    assert isinstance(excinfo.value.__cause__, RuntimeError)


def test_offline_stub_records_sent_text_without_network():
    stub = OfflineChatModel('{"case_answers": []}', model_id="stub-v1")
    response = stub.complete(MESSAGES)

    assert stub.sent_text() == "系统提示\n用户消息"
    assert stub.calls == [{"messages": MESSAGES, "max_tokens": None, "temperature": None}]
    assert response.text == '{"case_answers": []}'
    assert response.model == "stub-v1"
    assert response.usage == TokenUsage()
