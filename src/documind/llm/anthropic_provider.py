"""Anthropic Messages API provider."""

from __future__ import annotations

from typing import Any, cast

import httpx

from documind.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Generate answers with Anthropic's Messages API."""

    def __init__(
        self,
        model_name: str,
        api_key: str | None,
        api_version: str = "2026-10-21",
        timeout_seconds: float = 120.0,
        max_tokens: int = 1024,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.api_version = api_version
        self.max_tokens = max_tokens
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a single-message, non-streaming request to Anthropic."""
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when DOCUMIND_LLM_PROVIDER=anthropic"
            )
        try:
            response = self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.api_version,
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": self.max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Anthropic returned invalid JSON") from exc

        content = payload.get("content")
        if not isinstance(content, list):
            raise RuntimeError("Anthropic returned an unexpected response")
        text_parts = [
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]
        answer = "\n".join(cast(list[str], text_parts)).strip()
        if not answer:
            raise RuntimeError("Anthropic returned an empty response")
        return answer

    def close(self) -> None:
        """Close the HTTP connection pool."""
        self._client.close()
