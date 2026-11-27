from __future__ import annotations

from ai.llm.base import LLMProvider
from app.settings import settings


def build_llm_provider(use_mock: bool = False) -> LLMProvider:
    """Select the mock provider for offline mode, otherwise the NVIDIA NIM provider."""
    if use_mock or not settings.nvidia_api_key_str:
        from ai.llm.mock import MockProvider

        return MockProvider()

    from ai.llm.nvidia import NvidiaProvider

    return NvidiaProvider()
