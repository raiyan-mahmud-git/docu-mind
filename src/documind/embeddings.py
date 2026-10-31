"""Lazy wrapper around the sentence-transformers embedding model."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any


class SentenceTransformerEmbedder:
    """Load a sentence-transformers model once and return L2-normalized vectors."""

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: Any | None = None

    def _get_model(self) -> Any:
        """Load the heavyweight model on first use rather than at app startup."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not load embedding model {self.model_name!r}: {exc}"
                ) from exc
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings and normalize each result to unit length."""
        if not texts:
            return []

        try:
            vectors = self._get_model().encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Could not embed text with {self.model_name!r}: {exc}") from exc

        normalized: list[list[float]] = []
        for vector in vectors:
            values = [float(value) for value in vector.tolist()]
            magnitude = math.sqrt(sum(value * value for value in values))
            if magnitude == 0:
                raise ValueError("Embedding model returned a zero-length vector")
            normalized.append([value / magnitude for value in values])
        return normalized


@lru_cache(maxsize=4)
def get_embedder(model_name: str, batch_size: int = 32) -> SentenceTransformerEmbedder:
    """Return a cached embedder for the selected model and batch size."""
    return SentenceTransformerEmbedder(model_name=model_name, batch_size=batch_size)
