"""Ollama chat API provider for local text generation."""

from __future__ import annotations

from typing import Any, cast

import httpx

from documind.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Generate answers through Ollama's local /api/chat endpoint."""

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
        max_tokens: int = 1024,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a non-streaming chat request to the local Ollama server."""
        try:
            response = self._client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"num_predict": self.max_tokens},
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Ollama returned invalid JSON") from exc

        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty response")
        return cast(str, content).strip()

    def close(self) -> None:
        """Close the HTTP connection pool."""
        self._client.close()
