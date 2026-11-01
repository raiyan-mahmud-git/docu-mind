"""File-to-vector ingestion pipeline."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Protocol

from documind.chunking import chunk_pages
from documind.db import DocumentRegistry
from documind.embeddings import SentenceTransformerEmbedder
from documind.loaders import load_image, load_markdown, load_pdf, load_text
from documind.models import Document, Page
from documind.vectorstore.base import VectorStore

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Small interface needed by ingestion and retrieval."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input string."""


class IngestionPipeline:
    """Load files, create chunks and vectors, then register each document."""

    def __init__(
        self,
        registry: DocumentRegistry,
        vector_store: VectorStore,
        embedder: Embedder | SentenceTransformerEmbedder,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        ocr_enabled: bool = True,
        ocr_language: str = "eng",
        ocr_tessdata: Path | None = None,
    ) -> None:
        self.registry = registry
        self.vector_store = vector_store
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.ocr_enabled = ocr_enabled
        self.ocr_language = ocr_language
        self.ocr_tessdata = ocr_tessdata

    @staticmethod
    def _sha256(path: Path) -> str:
        """Hash file contents in blocks so large files need little extra memory."""
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _load(self, path: Path) -> list[Page]:
        """Choose a loader based on the supported file extension."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return load_pdf(
                path,
                ocr_enabled=self.ocr_enabled,
                ocr_language=self.ocr_language,
                ocr_tessdata=self.ocr_tessdata,
            )
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return load_image(
                path,
                ocr_enabled=self.ocr_enabled,
                ocr_language=self.ocr_language,
                ocr_tessdata=self.ocr_tessdata,
            )
        if suffix == ".md":
            return load_markdown(path)
        if suffix == ".txt":
            return load_text(path)
        raise ValueError(
            f"Unsupported file type {suffix or '(no extension)'!r}; "
            "use PDF, PNG, JPG, JPEG, BMP, TIFF, MD, or TXT"
        )

    def ingest_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> Document:
        """Index one file and deduplicate it by SHA-256 content hash."""
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"File does not exist: {source}")

        document_filename = filename or source.name
        started = time.monotonic()
        content_hash = self._sha256(source)
        existing = self.registry.find_by_hash(content_hash)
        if existing is not None:
            logger.info(
                "Skipping already indexed file %s (sha256=%s)", source.name, content_hash
            )
            return existing
        pages = self._load(source)
        doc_id = content_hash
        chunks = chunk_pages(
            pages,
            doc_hash=doc_id,
            filename=document_filename,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        vectors = self.embedder.embed_texts([chunk.text for chunk in chunks])
        self.vector_store.add(chunks, vectors)
        document = self.registry.register(
            doc_id=doc_id,
            filename=document_filename,
            sha256=content_hash,
            pages=len(pages),
            chunk_count=len(chunks),
        )
        elapsed = time.monotonic() - started
        logger.info(
            "Ingested %s: %d pages -> %d chunks in %.2f seconds",
            source.name,
            len(pages),
            len(chunks),
            elapsed,
        )
        return document


def delete_document(
    doc_id: str,
    registry: DocumentRegistry,
    vector_store: VectorStore,
) -> bool:
    """Remove a document's stored chunks and metadata row."""
    document = registry.get(doc_id)
    if document is None:
        return False
    vector_store.delete_by_doc(doc_id)
    return registry.delete(doc_id)


