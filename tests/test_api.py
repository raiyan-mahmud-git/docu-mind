from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from documind.api.main import create_app
from documind.config import Settings
from documind.db import DocumentRegistry
from documind.ingest import IngestionPipeline
from documind.retrieval import Retriever
from documind.runtime import Runtime
from documind.vectorstore import ChromaVectorStore


class FixedEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _settings(tmp_path: Path) -> Settings:
    base = Settings.from_env()
    return replace(
        base,
        data_dir=tmp_path,
        upload_dir=tmp_path / "uploads",
        chroma_dir=tmp_path / "chroma",
        sqlite_path=tmp_path / "registry.sqlite3",
        score_threshold=0.2,
        max_upload_mb=1,
    )


def _runtime(settings: Settings) -> Runtime:
    registry = DocumentRegistry(settings.sqlite_path)
    store = ChromaVectorStore(settings.chroma_dir)
    embedder = FixedEmbedder()
    return Runtime(
        registry=registry,
        vector_store=store,
        ingestor=IngestionPipeline(registry, store, embedder),
        retriever=Retriever(store, embedder, settings.score_threshold),
    )


def test_api_upload_search_list_delete_flow(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, runtime_factory=lambda: _runtime(settings))

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        upload = client.post(
            "/documents",
            files={"file": ("notes.txt", b"A river runs through a valley.", "text/plain")},
        )
        assert upload.status_code == 201
        document = upload.json()
        assert document["filename"] == "notes.txt"
        assert document["pages"] == 1
        assert document["chunk_count"] == 1

        documents = client.get("/documents")
        assert documents.status_code == 200
        assert documents.json()[0]["id"] == document["id"]

        search = client.post("/search", json={"query": "Tell me about rivers", "top_k": 3})
        assert search.status_code == 200
        result = search.json()["results"][0]
        assert result["filename"] == "notes.txt"
        assert result["page_number"] == 1
        assert result["score"] == 1.0

        deleted = client.delete(f"/documents/{document['id']}")
        assert deleted.status_code == 204
        assert client.get("/documents").json() == []
        assert client.post("/search", json={"query": "river"}).json()["no_relevant_passage"]


def test_api_rejects_bad_uploads_and_queries(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, runtime_factory=lambda: _runtime(settings))

    with TestClient(app) as client:
        unsupported = client.post(
            "/documents", files={"file": ("bad.exe", b"data", "application/octet-stream")}
        )
        assert unsupported.status_code == 400

        empty = client.post("/documents", files={"file": ("empty.txt", b"", "text/plain")})
        assert empty.status_code == 400

        oversized = client.post(
            "/documents",
            files={"file": ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
        )
        assert oversized.status_code == 413

        assert client.post("/search", json={"query": "  "}).status_code == 422
        assert client.delete("/documents/missing").status_code == 404

