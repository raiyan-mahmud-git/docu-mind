"""Semantic search over stored document chunks."""

from __future__ import annotations

from documind.embeddings import SentenceTransformerEmbedder
from documind.ingest import Embedder
from documind.models import SearchResult
from documind.vectorstore.base import VectorStore


class Retriever:
    """Embed questions and return passages that meet the relevance threshold."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder | SentenceTransformerEmbedder,
        score_threshold: float = 0.25,
    ) -> None:
        if not 0.0 <= score_threshold <= 1.0:
            raise ValueError("score_threshold must be between 0 and 1")
        self.vector_store = vector_store
        self.embedder = embedder
        self.score_threshold = score_threshold

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Return ranked relevant passages, or no results when below threshold."""
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        query_vector = self.embedder.embed_texts([cleaned_query])[0]
        results = self.vector_store.query(query_vector, top_k)
        if not results or results[0].score < self.score_threshold:
            return []
        return [result for result in results if result.score >= self.score_threshold]
