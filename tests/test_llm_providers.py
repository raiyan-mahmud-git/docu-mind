import json

import httpx

from documind.llm.anthropic_provider import AnthropicProvider
from documind.llm.ollama_provider import OllamaProvider


def test_ollama_provider_sends_grounded_non_streaming_chat() -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["body"] = json.loads(request.read())
        return httpx.Response(200, json={"message": {"content": "Answer [1]"}})

    provider = OllamaProvider(
        "test-model",
        "http://localhost:11434/",
        max_tokens=64,
        transport=httpx.MockTransport(handler),
    )
    answer = provider.generate("system prompt", "question and sources")

    assert answer == "Answer [1]"
    assert received["url"] == "http://localhost:11434/api/chat"
    assert received["body"]["stream"] is False
    assert received["body"]["options"]["num_predict"] == 64
    provider.close()


def test_anthropic_provider_sends_messages_api_request_without_real_network() -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["api_key"] = request.headers["x-api-key"]
        received["version"] = request.headers["anthropic-version"]
        received["body"] = json.loads(request.read())
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Answer [1]"}]})

    provider = AnthropicProvider(
        "test-model",
        "secret-test-key",
        api_version="test-version",
        max_tokens=71,
        transport=httpx.MockTransport(handler),
    )
    answer = provider.generate("system prompt", "question and sources")

    assert answer == "Answer [1]"
    assert received["url"] == "https://api.anthropic.com/v1/messages"
    assert received["api_key"] == "secret-test-key"
    assert received["version"] == "test-version"
    assert received["body"]["max_tokens"] == 71
    provider.close()


def test_anthropic_provider_requires_key_without_network() -> None:
    provider = AnthropicProvider("test-model", None)
    try:
        provider.generate("system", "user")
    except RuntimeError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)
    else:
        raise AssertionError("missing API key should raise a clear error")
    finally:
        provider.close()
