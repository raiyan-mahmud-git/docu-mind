import json
from dataclasses import replace
from pathlib import Path

import pytest

from documind.config import Settings
from documind.evaluation import EvaluationQuestion, evaluate
from documind.hybrid import HybridRetriever
from documind.models import Chunk, SearchResult
from documind.reranking import CrossEncoderReranker
from documind.retrieval import Retriever
from documind.runtime import create_runtime
from documind.vectorstore import ChromaVectorStore


class FixedEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def test_recall_and_mrr_use_expected_filename_and_page() -> None:
    question = EvaluationQuestion("query", "right.txt", 2)
    results = [
        SearchResult(Chunk("wrong", "d1", "wrong.txt", 1, 0, "wrong"), 0.8, 1),
        SearchResult(Chunk("right", "d2", "right.txt", 2, 0, "right"), 0.7, 2),
    ]

    metrics = evaluate([question], lambda _query, _k: results, (1, 2, 5))

    assert metrics.recall_at == {1: 0.0, 2: 1.0, 5: 1.0}
    assert metrics.mean_reciprocal_rank == 0.5


def test_evaluation_rejects_empty_questions() -> None:
    with pytest.raises(ValueError, match="at least one question"):
        evaluate([], lambda _query, _k: [])


def test_hybrid_search_can_promote_an_exact_keyword_match(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma")
    chunks = [
        Chunk("dense", "d1", "dense.txt", 1, 0, "A general note about plants."),
        Chunk("keyword", "d2", "keyword.txt", 4, 0, "The rareword catalyst speeds the reaction."),
    ]
    store.add(chunks, [[1.0, 0.0], [0.7, 0.7]])
    dense = Retriever(store, FixedEmbedder(), score_threshold=0.0)
    hybrid = HybridRetriever(dense, store)

    results = hybrid.search("rareword catalyst", top_k=2)

    assert results[0].chunk.filename == "keyword.txt"
    assert results[0].chunk.page_number == 4
    assert [result.rank for result in results] == [1, 2]
    store.close()


def test_hybrid_index_refreshes_after_document_changes(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma")
    dense = Retriever(store, FixedEmbedder(), score_threshold=0.0)
    hybrid = HybridRetriever(dense, store)
    store.add(
        [Chunk("new", "d1", "new.txt", 1, 0, "freshterm is indexed")],
        [[1.0, 0.0]],
    )

    results = hybrid.search("freshterm", top_k=1)

    assert results[0].chunk.filename == "new.txt"
    store.close()


def test_cross_encoder_reranks_without_changing_sources() -> None:
    results = [
        SearchResult(Chunk("first", "d1", "first.txt", 1, 0, "first passage"), 0.02, 1),
        SearchResult(Chunk("second", "d2", "second.txt", 3, 0, "second passage"), 0.01, 2),
    ]
    reranker = CrossEncoderReranker("unused")

    class FakeCrossEncoder:
        def predict(self, pairs, show_progress_bar=False):
            assert show_progress_bar is False
            assert pairs == [["query", "first passage"], ["query", "second passage"]]
            return [0.1, 0.9]

    reranker._model = FakeCrossEncoder()
    reranked = reranker.rerank("query", results)

    assert [result.chunk.filename for result in reranked] == ["second.txt", "first.txt"]
    assert [result.rank for result in reranked] == [1, 2]


def test_bundled_evaluation_questions_have_expected_size() -> None:
    questions_path = Path(__file__).parents[1] / "eval" / "questions.jsonl"
    questions = [
        json.loads(line)
        for line in questions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(questions) == 18
    assert {question["expected_filename"] for question in questions} == {
        "earth_science.pdf",
        "energy_systems.pdf",
        "plant_biology.pdf",
    }


def test_runtime_can_select_hybrid_retrieval(tmp_path: Path) -> None:
    settings = replace(
        Settings.from_env(),
        data_dir=tmp_path / "data",
        upload_dir=tmp_path / "uploads",
        chroma_dir=tmp_path / "chroma",
        sqlite_path=tmp_path / "registry.sqlite3",
        search_mode="hybrid",
    )

    runtime = create_runtime(settings)

    assert isinstance(runtime.retriever, HybridRetriever)
    runtime.close()
