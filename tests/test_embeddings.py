import numpy as np
import pytest

from documind.embeddings import SentenceTransformerEmbedder, get_embedder


class FakeEncoder:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts, **kwargs):
        self.calls += 1
        assert kwargs["batch_size"] == 2
        assert kwargs["show_progress_bar"] is False
        return np.asarray([[3.0, 4.0] for _ in texts])


def test_embedder_loads_lazily_and_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = SentenceTransformerEmbedder("fake-model", batch_size=2)
    fake = FakeEncoder()
    monkeypatch.setattr(embedder, "_model", fake)

    vectors = embedder.embed_texts(["first", "second"])

    assert vectors == [[0.6, 0.8], [0.6, 0.8]]
    assert fake.calls == 1


def test_empty_batch_does_not_load_model() -> None:
    embedder = SentenceTransformerEmbedder("model-that-is-not-loaded")

    assert embedder.embed_texts([]) == []
    assert embedder._model is None


def test_embedder_cache_reuses_instances() -> None:
    get_embedder.cache_clear()

    assert get_embedder("same-model") is get_embedder("same-model")
    assert get_embedder("same-model") is not get_embedder("other-model")
    get_embedder.cache_clear()


def test_zero_vector_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class ZeroEncoder:
        def encode(self, texts, **kwargs):
            return np.asarray([[0.0, 0.0]])

    embedder = SentenceTransformerEmbedder("fake")
    monkeypatch.setattr(embedder, "_model", ZeroEncoder())

    with pytest.raises(ValueError, match="zero-length"):
        embedder.embed_texts(["text"])
