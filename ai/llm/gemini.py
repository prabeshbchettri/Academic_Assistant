from __future__ import annotations

import logging
from typing import TypeVar

from pydantic import BaseModel

from ai.llm.base import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    Production Gemini provider using google-genai SDK with automatic model fallbacks,
    structured output schema enforcement, and retry logic.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key.strip() if api_key else settings.gemini_api_key_str
        self.primary_model = model or settings.gemini_model
        self.fallback_model = settings.gemini_fallback_model
        self._client = None

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

        models_to_try = [self.primary_model, self.fallback_model, "gemini-2.5-flash", "gemini-2.5-flash-lite"]
        last_error = None

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config,
                )
                if response.parsed:
                    return response.parsed  # type: ignore

                # Fallback to json loads if parsed is not directly populated
                raw_json = response.text or "{}"
                return schema.model_validate_json(raw_json)
            except Exception as exc:
                logger.warning("Gemini model '%s' failed: %s. Trying fallback...", model_name, exc)
                last_error = exc

        raise RuntimeError(f"All Gemini models failed for structured output. Last error: {last_error}")

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

        models_to_try = [self.primary_model, self.fallback_model, "gemini-2.5-flash", "gemini-2.5-flash-lite"]
        last_error = None

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as exc:
                logger.warning("Gemini model '%s' text generation failed: %s", model_name, exc)
                last_error = exc

        raise RuntimeError(f"All Gemini models failed for text generation: {last_error}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        embeddings = []
        for text in texts:
            response = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
            )
            embeddings.append(response.embedding.values)
        return embeddings
