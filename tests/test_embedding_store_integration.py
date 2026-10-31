from pathlib import Path

import numpy as np

from documind.embeddings import SentenceTransformerEmbedder
from documind.models import Chunk
from documind.vectorstore import ChromaVectorStore


class KeywordEncoder:
    """Deterministic stand-in for a model in an integration test."""

    def encode(self, texts, **kwargs):
        return np.asarray([[1.0, 0.0] if "cat" in text else [0.0, 1.0] for text in texts])


def test_embed_store_and_retrieve_pipeline(tmp_path: Path) -> None:
    embedder = SentenceTransformerEmbedder("fake")
    embedder._model = KeywordEncoder()
    store = ChromaVectorStore(tmp_path / "chroma")
    chunks = [
        Chunk("doc:0", "doc", "pets.txt", 1, 0, "A cat is a small pet."),
        Chunk("doc:1", "doc", "pets.txt", 2, 1, "A dog is a friendly pet."),
    ]
    vectors = embedder.embed_texts([chunk.text for chunk in chunks])
    query_vector = embedder.embed_texts(["Tell me about cats."])[0]

    store.add(chunks, vectors)
    results = store.query(query_vector, top_k=2)

    assert results[0].chunk.id == "doc:0"
    assert results[0].score > results[1].score
    store.close()


