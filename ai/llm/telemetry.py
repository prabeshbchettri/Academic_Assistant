from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class LLMCallRecord(BaseModel):
    provider: str
    model: str
    operation: str  # structured, text, embed
    schema_name: str = ""
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    fallback_used: bool = False
    fallback_from: str = ""
    success: bool = True
    error: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class LLMTelemetryTracker:
    """Thread-safe collector for LLM latency, token usage, and fallback telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[LLMCallRecord] = []

    def record(self, entry: LLMCallRecord) -> None:
        with self._lock:
            self._records.append(entry)

    def records(self) -> list[LLMCallRecord]:
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total_calls = len(self._records)
            succeeded = sum(1 for r in self._records if r.success)
            fallbacks = sum(1 for r in self._records if r.fallback_used)
            prompt_tokens = sum(r.prompt_tokens for r in self._records)
            completion_tokens = sum(r.completion_tokens for r in self._records)
            total_tokens = sum(r.total_tokens for r in self._records)
            total_latency_ms = round(sum(r.latency_ms for r in self._records), 1)
            models = list(dict.fromkeys(r.model for r in self._records if r.model))
            providers = list(dict.fromkeys(r.provider for r in self._records if r.provider))
            return {
                "total_calls": total_calls,
                "successful_calls": succeeded,
                "failed_calls": total_calls - succeeded,
                "fallback_activations": fallbacks,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "total_latency_ms": total_latency_ms,
                "providers_used": providers,
                "models_used": models,
            }
