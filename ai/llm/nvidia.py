from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from ai.llm.base import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MODEL_MAX_OUTPUT_TOKENS = {
    "nvidia/nemotron-3.5-lightning-30b-a3b": 32768,
    "nvidia/nemotron-3.5-bolt-e4b": 65536,
}


class NvidiaProvider(LLMProvider):
    """
    Production NVIDIA NIM provider using the OpenAI-compatible API.

    Structured output prefers native JSON schema enforcement where the endpoint supports it and
    falls back to schema-in-prompt validation for models whose API schema does not expose
    ``response_format``.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or settings.nvidia_api_key_str).strip()
        self.primary_model = model or settings.nvidia_model
        self.fallback_model = settings.nvidia_fallback_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "NVIDIA_API_KEY is not configured in settings or environment."
                )
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=settings.nvidia_base_url,
                timeout=settings.nvidia_timeout_seconds,
                max_retries=0,
            )
        return self._client

    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        client = self._get_client()
        schema_json = schema.model_json_schema()
        last_error: Exception | None = None

        for model_name in self._models_to_try():
            max_tokens = self._max_tokens_for(model_name)

            # 1. Preferred path: native JSON schema enforcement.
            try:
                response = self._create_chat(
                    client,
                    model=model_name,
                    messages=self._messages(system_prompt, user_prompt),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=self._json_schema_format(schema),
                    enable_thinking=False,
                )
                content = self._content(response)
                if not content.strip():
                    raise ValueError("Empty response content")
                return self._parse_content(content, schema)
            except Exception as exc:
                last_error = exc
                self._raise_if_auth_error(exc)
                logger.warning(
                    "NVIDIA model '%s' native structured output failed: %s. "
                    "Trying schema-in-prompt fallback.",
                    model_name,
                    exc,
                )

            # 2. Fallback path: JSON schema in the prompt + Pydantic validation.
            try:
                response = self._create_chat(
                    client,
                    model=model_name,
                    messages=self._messages(
                        system_prompt,
                        user_prompt + self._json_instruction(schema_json),
                    ),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    enable_thinking=False,
                )
                content = self._content(response)
                if not content.strip():
                    raise ValueError("Empty response content")
                return self._parse_content(content, schema)
            except Exception as exc:
                last_error = exc
                self._raise_if_auth_error(exc)
                logger.warning(
                    "NVIDIA model '%s' schema-in-prompt output failed: %s. "
                    "Trying one repair request.",
                    model_name,
                    exc,
                )

            # 3. One repair request for invalid JSON or validation errors.
            try:
                response = self._create_chat(
                    client,
                    model=model_name,
                    messages=self._messages(
                        system_prompt,
                        self._repair_prompt(user_prompt, schema_json, last_error),
                    ),
                    temperature=0.0,
                    max_tokens=max_tokens,
                    enable_thinking=False,
                )
                content = self._content(response)
                if not content.strip():
                    raise ValueError("Empty response content")
                return self._parse_content(content, schema)
            except Exception as exc:
                last_error = exc
                self._raise_if_auth_error(exc)
                logger.warning(
                    "NVIDIA model '%s' repair request failed: %s. Trying next model.",
                    model_name,
                    exc,
                )

        raise RuntimeError(
            f"All NVIDIA models failed for structured output. Last error: {last_error}"
        )

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        client = self._get_client()
        last_error: Exception | None = None

        for model_name in self._models_to_try():
            max_tokens = self._max_tokens_for(model_name)
            for enable_thinking in self._thinking_variants():
                try:
                    response = self._create_chat(
                        client,
                        model=model_name,
                        messages=self._messages(system_prompt, user_prompt),
                        temperature=temperature,
                        max_tokens=max_tokens,
                        enable_thinking=enable_thinking,
                    )
                    content = self._content(response)
                    if content.strip():
                        return content
                    raise ValueError("Empty response content")
                except Exception as exc:
                    last_error = exc
                    self._raise_if_auth_error(exc)
                    logger.warning(
                        "NVIDIA model '%s' text generation failed "
                        "(thinking=%s): %s",
                        model_name,
                        enable_thinking,
                        exc,
                    )

        raise RuntimeError(
            f"All NVIDIA models failed for text generation: {last_error}"
        )

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        if not texts:
            return []

        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": settings.nvidia_embedding_model,
            "input": texts,
            "encoding_format": "float",
            "extra_body": {"input_type": input_type, "truncate": "END"},
        }
        if settings.nvidia_embedding_dimensions:
            kwargs["dimensions"] = settings.nvidia_embedding_dimensions

        response = client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]

    def _create_chat(self, client, **kwargs):
        """Create a chat completion, dropping optional NVIDIA extras if rejected."""
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            if self._is_unsupported_param_error(exc) and "extra_body" in kwargs:
                retry_kwargs = dict(kwargs)
                retry_kwargs.pop("extra_body", None)
                return client.chat.completions.create(**retry_kwargs)
            raise

    def _models_to_try(self) -> list[str]:
        models = []
        for model in (self.primary_model, self.fallback_model):
            if model and model not in models:
                models.append(model)
        return models

    def _thinking_variants(self) -> list[bool]:
        if settings.nvidia_enable_thinking:
            return [True, False]
        return [False]

    def _max_tokens_for(self, model_name: str) -> int:
        limit = MODEL_MAX_OUTPUT_TOKENS.get(model_name)
        configured = max(1, settings.nvidia_max_output_tokens)
        return min(configured, limit) if limit else configured

    @staticmethod
    def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _json_schema_format(schema: type[BaseModel]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": schema.model_json_schema(),
            },
        }

    @staticmethod
    def _json_instruction(schema_json: dict[str, Any]) -> str:
        return (
            "\n\nReturn only valid JSON matching this JSON schema. "
            "Do not include Markdown fences or commentary.\n"
            f"{json.dumps(schema_json)}"
        )

    @staticmethod
    def _repair_prompt(
        user_prompt: str,
        schema_json: dict[str, Any],
        error: Exception | None,
    ) -> str:
        return (
            f"{user_prompt}\n\n"
            "Your previous response was invalid for the required schema.\n"
            f"Validation error: {error}\n\n"
            "Return only corrected JSON that conforms to this JSON schema. "
            "Do not include Markdown fences or commentary.\n"
            f"{json.dumps(schema_json)}"
        )

    @classmethod
    def _parse_content(cls, content: str, schema: type[T]) -> T:
        return schema.model_validate_json(cls._extract_json(content))

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return text

    @staticmethod
    def _content(response) -> str:
        if not response.choices:
            return ""
        message = response.choices[0].message
        content = getattr(message, "content", None)
        if isinstance(content, list):
            parts = []
            for part in content:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts)
        return content or ""

    @staticmethod
    def _is_unsupported_param_error(exc: Exception) -> bool:
        return getattr(exc, "status_code", None) in (400, 422)

    @staticmethod
    def _raise_if_auth_error(exc: Exception) -> None:
        if getattr(exc, "status_code", None) in (401, 403):
            raise exc
