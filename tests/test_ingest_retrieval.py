import hashlib
from pathlib import Path

from documind.db import DocumentRegistry
from documind.ingest import IngestionPipeline, delete_document
from documind.models import Chunk
from documind.retrieval import Retriever
from documind.vectorstore import ChromaVectorStore


class TextEmbedder:
    """Small deterministic encoder used to test the complete local pipeline."""

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += len(texts)
        return [[1.0, 0.0] if "river" in text.lower() else [0.0, 1.0] for text in texts]


def test_ingest_retrieval_deduplication_and_delete(tmp_path: Path) -> None:
    source = tmp_path / "geography.txt"
    source.write_text("A river flows through the valley.", encoding="utf-8")
    registry = DocumentRegistry(tmp_path / "registry.sqlite3")
    store = ChromaVectorStore(tmp_path / "chroma")
    embedder = TextEmbedder()
    ingestion = IngestionPipeline(registry, store, embedder, chunk_size=40, chunk_overlap=5)

    document = ingestion.ingest_file(source)
    calls_after_first_ingestion = embedder.calls
    duplicate = ingestion.ingest_file(source)
    assert calls_after_first_ingestion == embedder.calls
    results = Retriever(store, embedder, score_threshold=0.2).search("Where does the river flow?")

    assert document.id == hashlib.sha256(source.read_bytes()).hexdigest()
    assert duplicate == document
    assert store.count() == 1
    assert len(registry.list_documents()) == 1
    assert results[0].chunk.filename == "geography.txt"
    assert results[0].chunk.page_number == 1
    assert results[0].score > 0.9

    assert delete_document(document.id, registry, store) is True
    assert store.count() == 0
    assert registry.list_documents() == []
    store.close()


def test_ingestion_rejects_unsupported_and_missing_files(tmp_path: Path) -> None:
    registry = DocumentRegistry(tmp_path / "registry.sqlite3")
    store = ChromaVectorStore(tmp_path / "chroma")
    ingestion = IngestionPipeline(registry, store, TextEmbedder())

    unsupported = tmp_path / "data.docx"
    unsupported.write_text("not supported", encoding="utf-8")
    try:
        ingestion.ingest_file(unsupported)
        raise AssertionError("expected unsupported file type to fail")
    except ValueError as exc:
        assert "Unsupported file type" in str(exc)

    try:
        ingestion.ingest_file(tmp_path / "missing.txt")
        raise AssertionError("expected missing file to fail")
    except FileNotFoundError as exc:
        assert "does not exist" in str(exc)
    store.close()


def test_retriever_returns_no_results_below_threshold(tmp_path: Path) -> None:
    class OrthogonalEmbedder:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.0, 1.0] for _ in texts]

    store = ChromaVectorStore(tmp_path / "chroma")
    store.add(
        [Chunk("doc:0", "doc", "note.txt", 1, 0, "River passage")],
        [[1.0, 0.0]],
    )
    retriever = Retriever(store, OrthogonalEmbedder(), score_threshold=0.5)

    assert retriever.search("question") == []
    store.close()
