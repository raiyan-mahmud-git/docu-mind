"""Application service bundle shared by the CLI and HTTP API."""

from __future__ import annotations

from dataclasses import dataclass

from documind.config import Settings
from documind.db import DocumentRegistry
from documind.embeddings import get_embedder
from documind.hybrid import HybridRetriever
from documind.ingest import IngestionPipeline
from documind.llm import create_llm_provider
from documind.qa import QAService
from documind.reranking import CrossEncoderReranker
from documind.retrieval import Retriever
from documind.vectorstore import ChromaVectorStore


@dataclass
class Runtime:
    """Resources shared by one command or application process."""

    registry: DocumentRegistry
    vector_store: ChromaVectorStore
    ingestor: IngestionPipeline
    retriever: Retriever
    qa: QAService

    def close(self) -> None:
        """Release persistent vector and language-model connections."""
        self.qa.close()
        self.vector_store.close()


def create_runtime(settings: Settings | None = None) -> Runtime:
    """Create services configured for local persistent storage."""
    active_settings = settings or Settings.from_env()
    registry = DocumentRegistry(active_settings.sqlite_path)
    vector_store = ChromaVectorStore(active_settings.chroma_dir)
    embedder = get_embedder(active_settings.embedding_model)
    if active_settings.search_mode == "vector":
        retriever: Retriever = Retriever(
            vector_store, embedder, active_settings.score_threshold
        )
    elif active_settings.search_mode == "hybrid":
        vector_retriever = Retriever(vector_store, embedder, score_threshold=0.0)
        reranker = (
            CrossEncoderReranker(active_settings.reranker_model)
            if active_settings.reranker_model is not None
            else None
        )
        retriever = HybridRetriever(vector_retriever, vector_store, reranker=reranker)
    else:
        raise ValueError("DOCUMIND_SEARCH_MODE must be 'vector' or 'hybrid'")
    return Runtime(
        registry=registry,
        vector_store=vector_store,
        ingestor=IngestionPipeline(
            registry,
            vector_store,
            embedder,
            chunk_size=active_settings.chunk_size,
            chunk_overlap=active_settings.chunk_overlap,
            ocr_enabled=active_settings.ocr_enabled,
            ocr_language=active_settings.ocr_language,
            ocr_tessdata=active_settings.ocr_tessdata,
        ),
        retriever=retriever,
        qa=QAService(retriever, create_llm_provider(active_settings)),
    )
