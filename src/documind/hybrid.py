"""BM25 keyword retrieval fused with semantic search using reciprocal rank fusion."""

from __future__ import annotations

import re
from typing import Protocol

from rank_bm25 import BM25Plus  # type: ignore[import-untyped]

from documind.models import Chunk, SearchResult
from documind.retrieval import Retriever
from documind.vectorstore.base import VectorStore

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class Reranker(Protocol):
    """Pairwise scorer that reorders retrieved results for one query."""

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """Return the results reordered by model relevance."""


def tokenize(text: str) -> list[str]:
    """Normalize text into lowercase word and number tokens for BM25."""
    return _TOKEN_PATTERN.findall(text.casefold())


class HybridRetriever(Retriever):
    """Combine dense and lexical search rankings with reciprocal rank fusion."""

    def __init__(
        self,
        vector_retriever: Retriever,
        vector_store: VectorStore,
        rrf_constant: int = 60,
        reranker: Reranker | None = None,
    ) -> None:
        if rrf_constant < 1:
            raise ValueError("rrf_constant must be positive")
        super().__init__(
            vector_retriever.vector_store,
            vector_retriever.embedder,
            score_threshold=0.0,
        )
        self.vector_retriever = vector_retriever
        self.vector_store = vector_store
        self.rrf_constant = rrf_constant
        self.reranker = reranker
        self._chunks: list[Chunk] = []
        self._bm25: BM25Plus | None = None
        self._tokens: list[list[str]] = []
        self._chunk_ids: tuple[str, ...] = ()
        self._refresh_index()

    def _refresh_index(self) -> None:
        self._chunks = self.vector_store.all_chunks()
        self._chunk_ids = tuple(chunk.id for chunk in self._chunks)
        self._tokens = [tokenize(chunk.text) for chunk in self._chunks]
        self._bm25 = BM25Plus(self._tokens) if self._tokens else None

    def _ensure_fresh_index(self) -> None:
        current_ids = tuple(chunk.id for chunk in self.vector_store.all_chunks())
        if current_ids != self._chunk_ids:
            self._refresh_index()

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Return the top fused results, with one-based ranks and RRF scores."""
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        self._ensure_fresh_index()
        if not self._chunks:
            return []

        candidate_count = max(top_k * 3, top_k)
        dense_results = self.vector_retriever.search(cleaned_query, candidate_count)
        fused: dict[str, float] = {}
        chunk_by_id = {chunk.id: chunk for chunk in self._chunks}
        for rank, result in enumerate(dense_results, start=1):
            fused[result.chunk.id] = fused.get(result.chunk.id, 0.0) + 1 / (
                self.rrf_constant + rank
            )

        if self._bm25 is not None:
            query_tokens = set(tokenize(cleaned_query))
            scores = self._bm25.get_scores(list(query_tokens))
            lexical_order = sorted(
                range(len(self._chunks)), key=lambda index: (-float(scores[index]), index)
            )
            lexical_rank = 0
            for index in lexical_order:
                if query_tokens.isdisjoint(self._tokens[index]):
                    continue
                lexical_rank += 1
                chunk_id = self._chunks[index].id
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (
                    self.rrf_constant + lexical_rank
                )

        ordered = sorted(fused.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        results = [
            SearchResult(chunk_by_id[chunk_id], score, rank)
            for rank, (chunk_id, score) in enumerate(ordered, start=1)
        ]
        if self.reranker is not None:
            results = self.reranker.rerank(cleaned_query, results)
        return results[:top_k]
