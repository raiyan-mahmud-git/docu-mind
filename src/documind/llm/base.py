"""Provider-agnostic text generation interfaces and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider interface for grounded answer generation."""

    model_name: str

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a plain-text response for one grounded question."""

    def close(self) -> None:
        """Release provider resources when the runtime shuts down."""
        return None
