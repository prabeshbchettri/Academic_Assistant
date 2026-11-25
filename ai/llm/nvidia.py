from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ai.llm.base import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable_nvidia_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS_CODES
    return False


class NvidiaProvider(LLMProvider):
    """OpenAI-compatible NVIDIA NIM provider (Nemotron family) with retries and usage tracking."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        fallback_model: str | None = None,
    ):
        self.api_key = (api_key or settings.nvidia_api_key_str).strip()
        self.model = model or settings.nvidia_model
        self.fallback_model = fallback_model or settings.nvidia_fallback_model
        self.base_url = (base_url or settings.nvidia_base_url).rstrip("/")
        self.last_usage: dict[str, int] = {}
        self.last_model_used: str = self.model

    @retry(
        retry=retry_if_exception(_is_retryable_nvidia_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.8, max=5.0),
        reraise=True,
    )
    def _post_json(self, endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=payload,
            )
            if response.is_error:
                logger.error(
                    "NVIDIA API error %s: %s",
                    response.status_code,
                    response.text[:1000],
                )
            response.raise_for_status()
            return dict(response.json())

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        response_format: dict[str, Any] | None = None,
        thinking: bool | None = None,
        model_override: str | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set. Add it to .env.")

        target_model = model_override or self.model
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "top_p": 0.95,
            "max_tokens": settings.nvidia_max_output_tokens,
            "stream": False,
        }
        enable_thinking = settings.nvidia_enable_thinking if thinking is None else thinking
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
        if response_format is not None:
            payload["response_format"] = response_format

        data = self._post_json("/chat/completions", payload, timeout=180.0)
        usage = data.get("usage") or {}
        self.last_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        self.last_model_used = str(data.get("model") or target_model)

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"NVIDIA response did not contain choices: {data}")
        message = choices[0].get("message") or {}
        content = message.get("content") or message.get("reasoning_content") or ""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content).strip()

    def _candidate_models(self) -> list[str]:
        return list(dict.fromkeys(m for m in (self.model, self.fallback_model) if m))

    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        schema_text = json.dumps(schema.model_json_schema(), indent=2)
        system = (
            f"{system_prompt}\n\n"
            "Respond with only one valid JSON object. Do not use markdown fences "
            "and do not add commentary. The JSON object must match this schema:\n"
            f"{schema_text}"
        )
        prompt = f"{user_prompt}\n\nReturn only the JSON object."

        last_exc: Exception | None = None
        for model_name in self._candidate_models():
            try:
                try:
                    content = self._chat(
                        system,
                        prompt,
                        temperature,
                        response_format={"type": "json_object"},
                        thinking=False,
                        model_override=model_name,
                    )
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (400, 404, 422):
                        content = self._chat(
                            system,
                            prompt,
                            temperature,
                            thinking=False,
                            model_override=model_name,
                        )
                    else:
                        raise

                try:
                    return schema.model_validate_json(self._extract_json(content))
                except Exception as first_error:
                    logger.warning(
                        "NVIDIA structured response invalid on '%s' (%s); retrying correction.",
                        model_name,
                        first_error,
                    )
                    correction = (
                        "Your previous response was not valid JSON for the required schema.\n"
                        f"Error: {first_error}\n"
                        f"Previous response:\n{content[:4000]}\n\n"
                        "Return only a corrected JSON object."
                    )
                    content = self._chat(
                        system,
                        correction,
                        0.0,
                        thinking=False,
                        model_override=model_name,
                    )
                    return schema.model_validate_json(self._extract_json(content))
            except Exception as exc:
                logger.warning("NVIDIA model '%s' failed: %s", model_name, exc)
                last_exc = exc

        raise RuntimeError(f"All NVIDIA models failed for structured output: {last_exc}")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        last_exc: Exception | None = None
        for model_name in self._candidate_models():
            try:
                return self._chat(
                    system_prompt,
                    user_prompt,
                    temperature,
                    model_override=model_name,
                )
            except Exception as exc:
                logger.warning("NVIDIA text generation failed on '%s': %s", model_name, exc)
                last_exc = exc
        raise RuntimeError(f"All NVIDIA models failed for text generation: {last_exc}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set. Add it to .env.")
        if not texts:
            return []

        payload = {
            "model": settings.nvidia_embedding_model,
            "input": texts,
            "input_type": "passage",
            "encoding_format": "float",
        }
        data = self._post_json("/embeddings", payload, timeout=120.0)
        usage = data.get("usage") or {}
        self.last_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": 0,
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        self.last_model_used = settings.nvidia_embedding_model

        rows = sorted(data.get("data", []), key=lambda row: row.get("index", 0))
        return [row.get("embedding", []) for row in rows]

    @staticmethod
    def _extract_json(text: str) -> str:
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return cleaned[start : end + 1]
        return cleaned
