"""Regression tests for the NVIDIA NIM provider.

The provider previously forwarded ``enable_thinking`` as a direct keyword argument to
``client.chat.completions.create()``, which the OpenAI SDK rejects with
``TypeError: Completions.create() got an unexpected keyword argument 'enable_thinking'``.
These tests assert that the flag only ever travels inside ``extra_body`` and only for models
that declare thinking support.
"""

from __future__ import annotations

from types import SimpleNamespace

from pydantic import BaseModel

from ai.llm.nvidia import NvidiaProvider
from app.settings import settings

PRIMARY = "nvidia/nemotron-3.5-lightning-30b-a3b"
UNSUPPORTED = "nvidia/some-non-reasoning-model"


class Sample(BaseModel):
    answer: str


class ApiError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


class FakeCompletions:
    def __init__(self, responses):
        self.calls: list[dict] = []
        self._responses = list(responses)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self._responses.pop(0) if self._responses else _completion('{"answer": "ok"}')
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, responses):
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _provider(model: str = PRIMARY, fallback: str = "nvidia/fallback-model") -> NvidiaProvider:
    provider = NvidiaProvider(api_key="test-key", model=model)
    provider.fallback_model = fallback
    return provider


def _sdk_kwargs(client: FakeClient) -> list[dict]:
    return client.completions.calls


def test_no_call_passes_enable_thinking_to_sdk():
    client = FakeClient([])
    provider = _provider()
    provider._client = client

    provider.generate_text("system", "user")
    provider.generate_structured(Sample, "system", "user")

    for kwargs in _sdk_kwargs(client):
        assert "enable_thinking" not in kwargs


def test_text_generation_sends_thinking_via_extra_body():
    client = FakeClient([])
    provider = _provider()
    provider._client = client

    assert provider.generate_text("system", "user") == '{"answer": "ok"}'

    kwargs = _sdk_kwargs(client)[0]
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert "enable_thinking" not in kwargs


def test_text_generation_retries_with_thinking_disabled_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_enable_thinking", True)
    client = FakeClient([_completion(""), _completion("final answer")])
    provider = _provider()
    provider._client = client

    assert provider.generate_text("system", "user") == "final answer"

    first, second = _sdk_kwargs(client)
    assert first["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True
    assert second["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
    for kwargs in (first, second):
        assert "enable_thinking" not in kwargs


def test_structured_output_sends_thinking_disabled_via_extra_body():
    client = FakeClient([_completion('{"answer": "42"}')])
    provider = _provider()
    provider._client = client

    result = provider.generate_structured(Sample, "system", "user")

    assert result == Sample(answer="42")
    kwargs = _sdk_kwargs(client)[0]
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert "enable_thinking" not in kwargs


def test_structured_output_falls_back_to_schema_in_prompt_without_thinking_kwarg():
    client = FakeClient(
        [
            ApiError("response_format is not supported", status_code=400),
            ApiError("response_format is not supported", status_code=400),
            _completion('{"answer": "fallback"}'),
        ]
    )
    provider = _provider()
    provider._client = client

    result = provider.generate_structured(Sample, "system", "user")

    assert result == Sample(answer="fallback")
    calls = _sdk_kwargs(client)
    assert "response_format" not in calls[-1]
    assert "enable_thinking" not in calls[-1]
    assert calls[-1]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_structured_output_repairs_invalid_json_without_thinking_kwarg():
    client = FakeClient(
        [
            _completion("not json"),
            _completion("still not json"),
            _completion('{"answer": "repaired"}'),
        ]
    )
    provider = _provider()
    provider._client = client

    assert provider.generate_structured(Sample, "system", "user") == Sample(answer="repaired")

    repair_call = _sdk_kwargs(client)[-1]
    assert repair_call["temperature"] == 0.0
    assert "enable_thinking" not in repair_call
    assert repair_call["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_model_fallback_preserves_thinking_handling():
    failing = _completion("")  # empty content on primary for every attempt
    client = FakeClient([failing] * 3 + [_completion('{"answer": "from fallback"}')])
    provider = _provider(fallback="nvidia/nemotron-3.5-bolt-e4b")
    provider._client = client

    assert provider.generate_structured(Sample, "system", "user") == Sample(
        answer="from fallback"
    )
    assert _sdk_kwargs(client)[-1]["model"] == "nvidia/nemotron-3.5-bolt-e4b"
    for kwargs in _sdk_kwargs(client):
        assert "enable_thinking" not in kwargs
        assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_non_thinking_model_never_receives_chat_template_kwargs():
    client = FakeClient([])
    provider = _provider(model=UNSUPPORTED, fallback=UNSUPPORTED)
    provider._client = client

    provider.generate_text("system", "user")
    provider.generate_structured(Sample, "system", "user")

    assert provider.supports_thinking(UNSUPPORTED) is False
    for kwargs in _sdk_kwargs(client):
        assert "enable_thinking" not in kwargs
        assert "extra_body" not in kwargs


def test_unsupported_extra_body_is_retried_without_it():
    client = FakeClient(
        [
            ApiError("unknown field chat_template_kwargs", status_code=400),
            _completion("recovered"),
        ]
    )
    provider = _provider()
    provider._client = client

    assert provider.generate_text("system", "user") == "recovered"

    first, second = _sdk_kwargs(client)
    assert "extra_body" in first
    assert "extra_body" not in second
    assert "enable_thinking" not in second


def test_sdk_boundary_consumes_enable_thinking_kwarg():
    """Even a stray ``enable_thinking`` keyword is consumed before reaching the SDK."""
    client = FakeClient([])
    provider = _provider()
    provider._client = client

    provider._create_chat(
        client, model=PRIMARY, messages=[], enable_thinking=False, temperature=0.0
    )

    kwargs = _sdk_kwargs(client)[0]
    assert "enable_thinking" not in kwargs
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
