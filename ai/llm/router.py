from __future__ import annotations

import logging
import time
from typing import TypeVar

from pydantic import BaseModel

from ai.llm.base import LLMProvider
from ai.llm.telemetry import LLMCallRecord, LLMTelemetryTracker

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ResilientLLMRouter(LLMProvider):
    """
    Composite LLM router providing runtime failover across ordered providers
    (e.g., NVIDIA NIM -> Google Gemini fallback) with per-call latency & token telemetry.
    """

    def __init__(
        self,
        providers: list[tuple[str, LLMProvider]],
        telemetry: LLMTelemetryTracker | None = None,
    ):
        if not providers:
            raise ValueError("ResilientLLMRouter requires at least one provider.")
        self.providers = providers
        self.telemetry = telemetry or LLMTelemetryTracker()

    @staticmethod
    def _extract_meta(provider: LLMProvider, default_name: str) -> tuple[str, dict[str, int]]:
        model_used = str(
            getattr(provider, "last_model_used", "")
            or getattr(provider, "model", "")
            or getattr(provider, "primary_model", "")
            or default_name
        )
        raw_usage = getattr(provider, "last_usage", {}) or {}
        usage = {
            "prompt_tokens": int(raw_usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(raw_usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(raw_usage.get("total_tokens", 0) or 0),
        }
        return model_used, usage

    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        last_error: Exception | None = None
        first_provider_name = self.providers[0][0]

        for idx, (name, provider) in enumerate(self.providers):
            start = time.perf_counter()
            try:
                result = provider.generate_structured(
                    schema, system_prompt, user_prompt, temperature=temperature
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                model_used, usage = self._extract_meta(provider, name)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=model_used,
                        operation="structured",
                        schema_name=schema.__name__,
                        latency_ms=elapsed_ms,
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                        total_tokens=usage["total_tokens"],
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=True,
                    )
                )
                return result
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=getattr(provider, "model", name),
                        operation="structured",
                        schema_name=schema.__name__,
                        latency_ms=elapsed_ms,
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=False,
                        error=str(exc)[:300],
                    )
                )
                logger.warning(
                    "Provider '%s' failed for schema %s: %s",
                    name,
                    schema.__name__,
                    exc,
                )
                last_error = exc

        raise RuntimeError(f"All configured LLM providers failed: {last_error}")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        last_error: Exception | None = None
        first_provider_name = self.providers[0][0]

        for idx, (name, provider) in enumerate(self.providers):
            start = time.perf_counter()
            try:
                result = provider.generate_text(
                    system_prompt, user_prompt, temperature=temperature
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                model_used, usage = self._extract_meta(provider, name)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=model_used,
                        operation="text",
                        latency_ms=elapsed_ms,
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                        total_tokens=usage["total_tokens"],
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=True,
                    )
                )
                return result
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=getattr(provider, "model", name),
                        operation="text",
                        latency_ms=elapsed_ms,
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=False,
                        error=str(exc)[:300],
                    )
                )
                logger.warning("Provider '%s' text generation failed: %s", name, exc)
                last_error = exc

        raise RuntimeError(f"All configured LLM providers failed: {last_error}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        first_provider_name = self.providers[0][0]

        for idx, (name, provider) in enumerate(self.providers):
            start = time.perf_counter()
            try:
                vectors = provider.embed(texts)
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                model_used, usage = self._extract_meta(provider, name)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=model_used,
                        operation="embed",
                        latency_ms=elapsed_ms,
                        prompt_tokens=usage["prompt_tokens"],
                        total_tokens=usage["total_tokens"],
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=True,
                    )
                )
                return vectors
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
                self.telemetry.record(
                    LLMCallRecord(
                        provider=name,
                        model=getattr(provider, "model", name),
                        operation="embed",
                        latency_ms=elapsed_ms,
                        fallback_used=idx > 0,
                        fallback_from=first_provider_name if idx > 0 else "",
                        success=False,
                        error=str(exc)[:300],
                    )
                )
                logger.warning("Provider '%s' embedding failed: %s", name, exc)
                last_error = exc

        raise RuntimeError(f"All configured LLM providers failed for embeddings: {last_error}")
