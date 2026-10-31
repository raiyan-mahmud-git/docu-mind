"""Storage interface for embedded document chunks."""

from __future__ import annotations

from abc import ABC, abstractmethod

from documind.models import Chunk, SearchResult


class VectorStore(ABC):
    """Operations required by the ingestion and retrieval pipelines."""

    @abstractmethod
    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Store chunk text, metadata, and matching vectors."""

    @abstractmethod
    def query(self, embedding: list[float], top_k: int) -> list[SearchResult]:
        """Return the closest chunks ordered by similarity."""

    @abstractmethod
    def all_chunks(self) -> list[Chunk]:
        """Return every stored chunk in a stable order for lexical indexing."""

    @abstractmethod
    def delete_by_doc(self, doc_id: str) -> None:
        """Delete every chunk belonging to one document."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored chunks."""

    @abstractmethod
    def close(self) -> None:
        """Release local vector-store resources."""
