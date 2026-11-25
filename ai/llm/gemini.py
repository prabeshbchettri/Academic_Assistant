from __future__ import annotations

import logging
from typing import Any, TypeVar

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


def _is_transient_gemini_error(exc: BaseException) -> bool:
    """Retry transient network/5xx errors, but fail fast on 429 daily quota exhaustion."""
    msg = str(exc).lower()
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg:
        return False
    return any(
        marker in msg
        for marker in (
            "500",
            "502",
            "503",
            "504",
            "timeout",
            "timed out",
            "connection",
            "temporarily",
        )
    )


class GeminiProvider(LLMProvider):
    """
    Production Gemini provider using google-genai SDK with deduplicated model fallbacks,
    structured output schema enforcement, transient retries, and usage tracking.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key.strip() if api_key else settings.gemini_api_key_str
        self.primary_model = model or settings.gemini_model
        self.fallback_model = settings.gemini_fallback_model
        self._client: Any = None
        self.last_usage: dict[str, int] = {}
        self.last_model_used: str = self.primary_model

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured in settings or environment.")
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version="v1beta", timeout=60000),
            )
        return self._client

    def _candidate_models(self) -> list[str]:
        candidates = (
            self.primary_model,
            self.fallback_model,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        )
        return list(dict.fromkeys(m for m in candidates if m))

    def _capture_usage(self, response: Any, model_name: str) -> None:
        self.last_model_used = model_name
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            self.last_usage = {
                "prompt_tokens": int(getattr(meta, "prompt_token_count", 0) or 0),
                "completion_tokens": int(getattr(meta, "candidates_token_count", 0) or 0),
                "total_tokens": int(getattr(meta, "total_token_count", 0) or 0),
            }
        else:
            self.last_usage = {}

    @retry(
        retry=retry_if_exception(_is_transient_gemini_error),
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=0.8, max=3.0),
        reraise=True,
    )
    def _call_generate(self, client: Any, model_name: str, user_prompt: str, config: Any) -> Any:
        return client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=config,
        )

    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )

        last_error: Exception | None = None
        for model_name in self._candidate_models():
            try:
                response = self._call_generate(client, model_name, user_prompt, config)
                self._capture_usage(response, model_name)
                if response.parsed:
                    return response.parsed  # type: ignore[return-value]

                raw_json = response.text or "{}"
                return schema.model_validate_json(raw_json)
            except Exception as exc:
                logger.warning(
                    "Gemini model '%s' failed: %s. Trying next fallback...",
                    model_name,
                    exc,
                )
                last_error = exc

        raise RuntimeError(
            f"All Gemini models failed for structured output. Last error: {last_error}"
        )

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
        )

        last_error: Exception | None = None
        for model_name in self._candidate_models():
            try:
                response = self._call_generate(client, model_name, user_prompt, config)
                self._capture_usage(response, model_name)
                return response.text or ""
            except Exception as exc:
                logger.warning("Gemini model '%s' text generation failed: %s", model_name, exc)
                last_error = exc

        raise RuntimeError(f"All Gemini models failed for text generation: {last_error}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        embeddings: list[list[float]] = []
        for text in texts:
            response = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
            )
            embeddings.append(response.embedding.values)
        self.last_model_used = settings.gemini_embedding_model
        return embeddings
