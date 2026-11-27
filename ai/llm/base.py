from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        """Generates structured output conforming strictly to the Pydantic schema."""
        ...

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        """Generates plain text response."""
        ...

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """Generates embedding vectors for a list of text strings."""
        ...
