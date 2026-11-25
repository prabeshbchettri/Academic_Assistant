from __future__ import annotations

from ai.llm.base import LLMProvider
from ai.llm.gemini import GeminiProvider
from ai.llm.mock import MockProvider
from ai.llm.nvidia import NvidiaProvider
from ai.llm.router import ResilientLLMRouter
from ai.llm.telemetry import LLMTelemetryTracker
from app.settings import settings


def build_provider(
    use_mock: bool = False,
    telemetry: LLMTelemetryTracker | None = None,
) -> LLMProvider:
    tracker = telemetry or LLMTelemetryTracker()
    if use_mock:
        return ResilientLLMRouter([("mock", MockProvider())], telemetry=tracker)

    providers: list[tuple[str, LLMProvider]] = []
    preferred = settings.llm_provider.strip().lower()

    if preferred == "gemini":
        if settings.gemini_api_key_str:
            providers.append(("gemini", GeminiProvider(api_key=settings.gemini_api_key_str)))
        if settings.nvidia_api_key_str:
            providers.append(("nvidia", NvidiaProvider()))
    else:
        if settings.nvidia_api_key_str:
            providers.append(("nvidia", NvidiaProvider()))
        if settings.gemini_api_key_str:
            providers.append(("gemini", GeminiProvider(api_key=settings.gemini_api_key_str)))

    if not providers:
        return ResilientLLMRouter([("mock", MockProvider())], telemetry=tracker)

    return ResilientLLMRouter(providers, telemetry=tracker)
