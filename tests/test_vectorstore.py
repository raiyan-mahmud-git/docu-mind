from pathlib import Path

import pytest

from documind.models import Chunk
from documind.vectorstore import ChromaVectorStore


def _chunk(chunk_id: str, doc_id: str, text: str, page_number: int = 1) -> Chunk:
    return Chunk(chunk_id, doc_id, f"{doc_id}.txt", page_number, 0, text)


def test_chroma_add_query_and_delete(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma")
    chunks = [
        _chunk("doc-a:0", "doc-a", "about cats"),
        _chunk("doc-b:0", "doc-b", "about dogs", page_number=3),
    ]
    store.add(chunks, [[1.0, 0.0], [0.0, 1.0]])

    results = store.query([0.99, 0.01], top_k=2)

    assert store.count() == 2
    assert [result.chunk.id for result in results] == ["doc-a:0", "doc-b:0"]
    assert results[0].chunk.page_number == 1
    assert results[0].rank == 1
    assert results[0].score > results[1].score

    store.delete_by_doc("doc-a")
    assert store.count() == 1
    assert [result.chunk.doc_id for result in store.query([0.0, 1.0], 2)] == ["doc-b"]
    store.close()


def test_chroma_upsert_is_idempotent_and_validates_inputs(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma")
    chunk = _chunk("doc-a:0", "doc-a", "original")
    store.add([chunk], [[1.0, 0.0]])
    store.add([_chunk("doc-a:0", "doc-a", "updated")], [[1.0, 0.0]])

    assert store.count() == 1
    assert store.query([1.0, 0.0], 1)[0].chunk.text == "updated"
    with pytest.raises(ValueError, match="exactly one embedding"):
        store.add([chunk], [])
    with pytest.raises(ValueError, match="top_k"):
        store.query([1.0, 0.0], 0)


