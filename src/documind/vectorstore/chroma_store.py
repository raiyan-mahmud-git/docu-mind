"""Persistent ChromaDB implementation of the vector store interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import chromadb

from documind.models import Chunk, SearchResult
from documind.vectorstore.base import VectorStore


class ChromaVectorStore(VectorStore):
    """Store vectors in a persistent cosine-distance Chroma collection."""

    def __init__(self, path: str | Path, collection_name: str = "documind") -> None:
        database_path = Path(path)
        database_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(database_path))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks by deterministic ID so retries do not duplicate data."""
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding")
        if not chunks:
            return

        self._collection.upsert(
            ids=[chunk.id for chunk in chunks],
            embeddings=cast(Any, embeddings),
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "doc_id": chunk.doc_id,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
        )

    def query(self, embedding: list[float], top_k: int) -> list[SearchResult]:
        """Query Chroma and convert cosine distance to a 0-to-1 similarity."""
        if top_k < 1:
            raise ValueError("top_k must be positive")
        count = self.count()
        if not embedding or count == 0:
            return []

        result: Any = self._collection.query(
            query_embeddings=cast(Any, [embedding]),
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        search_results: list[SearchResult] = []
        for rank, (chunk_id, text, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances, strict=True), start=1
        ):
            if text is None or metadata is None or distance is None:
                continue
            chunk = Chunk(
                id=chunk_id,
                doc_id=str(metadata["doc_id"]),
                filename=str(metadata["filename"]),
                page_number=int(metadata["page_number"]),
                chunk_index=int(metadata["chunk_index"]),
                text=text,
            )
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            search_results.append(SearchResult(chunk=chunk, score=score, rank=rank))
        return search_results

    def delete_by_doc(self, doc_id: str) -> None:
        """Remove all Chroma records with the requested document ID."""
        self._collection.delete(where={"doc_id": doc_id})

    def count(self) -> int:
        """Return the current number of records in the collection."""
        return self._collection.count()

    def close(self) -> None:
        """Release Chroma's local database connection."""
        cast(Any, self._client).close()

