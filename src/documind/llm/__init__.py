"""Create configured language-model providers."""

from documind.config import Settings
from documind.llm.anthropic_provider import AnthropicProvider
from documind.llm.base import LLMProvider
from documind.llm.ollama_provider import OllamaProvider


def create_llm_provider(settings: Settings) -> LLMProvider | None:
    """Build a provider from settings, leaving LLM use disabled by default."""
    if settings.llm_provider == "none":
        return None
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            model_name=settings.ollama_model,
            base_url=settings.ollama_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            model_name=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            api_version=settings.anthropic_api_version,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
    raise ValueError("DOCUMIND_LLM_PROVIDER must be one of: none, ollama, anthropic")


__all__ = ["LLMProvider", "create_llm_provider"]
