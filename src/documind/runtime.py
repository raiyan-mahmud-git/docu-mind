"""Application service bundle shared by the CLI and HTTP API."""

from __future__ import annotations

from dataclasses import dataclass

from documind.config import Settings
from documind.db import DocumentRegistry
from documind.embeddings import get_embedder
from documind.ingest import IngestionPipeline
from documind.retrieval import Retriever
from documind.vectorstore import ChromaVectorStore


@dataclass
class Runtime:
    """Resources shared by one command or application process."""

    registry: DocumentRegistry
    vector_store: ChromaVectorStore
    ingestor: IngestionPipeline
    retriever: Retriever

    def close(self) -> None:
        """Release the persistent vector database connection."""
        self.vector_store.close()


def create_runtime(settings: Settings | None = None) -> Runtime:
    """Create services configured for local persistent storage."""
    active_settings = settings or Settings.from_env()
    registry = DocumentRegistry(active_settings.sqlite_path)
    vector_store = ChromaVectorStore(active_settings.chroma_dir)
    embedder = get_embedder(active_settings.embedding_model)
    return Runtime(
        registry=registry,
        vector_store=vector_store,
        ingestor=IngestionPipeline(
            registry,
            vector_store,
            embedder,
            chunk_size=active_settings.chunk_size,
            chunk_overlap=active_settings.chunk_overlap,
        ),
        retriever=Retriever(vector_store, embedder, active_settings.score_threshold),
    )
