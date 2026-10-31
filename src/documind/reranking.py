"""Optional cross-encoder reranking for a short candidate list."""

from __future__ import annotations

from typing import Any

from documind.models import SearchResult


class CrossEncoderReranker:
    """Load a sentence-transformers CrossEncoder only when reranking is requested."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not load reranker model {self.model_name!r}: {exc}"
                ) from exc
        return self._model

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """Sort candidates by pairwise query-passage relevance scores."""
        if not results:
            return []
        pairs = [[query, result.chunk.text] for result in results]
        try:
            scores = self._get_model().predict(pairs, show_progress_bar=False)
        except Exception as exc:
            message = f"Could not rerank passages with {self.model_name!r}: {exc}"
            raise RuntimeError(message) from exc
        ordered = sorted(
            zip(results, scores, strict=True),
            key=lambda pair: -float(pair[1]),
        )
        return [
            SearchResult(result.chunk, result.score, rank)
            for rank, (result, _) in enumerate(ordered, start=1)
        ]
