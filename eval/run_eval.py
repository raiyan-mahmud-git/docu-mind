"""Build an isolated sample index and compare vector, hybrid, and reranked search."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from documind.config import Settings
from documind.evaluation import EvaluationMetrics, EvaluationQuestion, evaluate
from documind.hybrid import HybridRetriever
from documind.reranking import CrossEncoderReranker
from documind.runtime import create_runtime

QUESTIONS_PATH = Path(__file__).with_name("questions.jsonl")
SAMPLE_DOCS_PATH = Path(__file__).with_name("sample_docs")
CUTOFFS = (1, 3, 5)


def load_questions(path: Path = QUESTIONS_PATH) -> list[EvaluationQuestion]:
    """Load and validate expected source labels from JSONL."""
    questions: list[EvaluationQuestion] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value: Any = json.loads(line)
            query = value["query"]
            filename = value["expected_filename"]
            page = value["expected_page"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"Invalid evaluation question on line {line_number}: {exc}") from exc
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Question on line {line_number} has an empty query")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(f"Question on line {line_number} has an empty expected filename")
        if not isinstance(page, int) or page < 1:
            raise ValueError(f"Question on line {line_number} has an invalid expected page")
        questions.append(EvaluationQuestion(query, filename, page))
    if not questions:
        raise ValueError(f"No evaluation questions found in {path}")
    return questions


def print_metrics(rows: list[tuple[str, EvaluationMetrics]], question_count: int) -> None:
    """Print a compact aligned metrics table."""
    print(f"Evaluation: {question_count} questions, source match = filename + page")
    print(f"{'Method':<25} {'Recall@1':>9} {'Recall@3':>9} {'Recall@5':>9} {'MRR':>8}")
    for name, metrics in rows:
        print(
            f"{name:<25} {metrics.recall_at[1]:>9.3f} "
            f"{metrics.recall_at[3]:>9.3f} {metrics.recall_at[5]:>9.3f} "
            f"{metrics.mean_reciprocal_rank:>8.3f}"
        )


def run(*, include_reranker: bool, reranker_model: str) -> None:
    """Index bundled evaluation docs in a temporary store and score each method."""
    questions = load_questions()
    docs = sorted(SAMPLE_DOCS_PATH.glob("*.pdf"))
    if not docs:
        raise RuntimeError(f"No sample documents found in {SAMPLE_DOCS_PATH}")

    with TemporaryDirectory(prefix="documind-eval-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        settings = replace(
            Settings.from_env(),
            data_dir=temporary_root / "data",
            upload_dir=temporary_root / "uploads",
            chroma_dir=temporary_root / "chroma",
            sqlite_path=temporary_root / "documind.sqlite3",
            score_threshold=0.0,
            search_mode="vector",
        )
        runtime = create_runtime(settings)
        try:
            for document_path in docs:
                runtime.ingestor.ingest_file(document_path)
            hybrid = HybridRetriever(runtime.retriever, runtime.vector_store)

            vector_metrics = evaluate(
                questions,
                lambda query, top_k: runtime.retriever.search(query, top_k),
                CUTOFFS,
            )
            hybrid_metrics = evaluate(questions, hybrid.search, CUTOFFS)
            rows = [("Vector baseline", vector_metrics), ("Hybrid (BM25 + RRF)", hybrid_metrics)]

            if include_reranker:
                reranker = CrossEncoderReranker(reranker_model)

                def reranked_search(query: str, top_k: int):
                    candidates = hybrid.search(query, max(top_k * 3, top_k))
                    return reranker.rerank(query, candidates)[:top_k]

                reranked_metrics = evaluate(questions, reranked_search, CUTOFFS)
                rows.append(("Hybrid + reranker", reranked_metrics))
            print_metrics(rows, len(questions))
        finally:
            runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="also run the optional cross-encoder reranker (may download its model)",
    )
    parser.add_argument(
        "--reranker-model",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        help="sentence-transformers cross-encoder model name or local path",
    )
    args = parser.parse_args()
    run(include_reranker=args.rerank, reranker_model=args.reranker_model)


if __name__ == "__main__":
    main()
