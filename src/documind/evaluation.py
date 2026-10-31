"""Small, dependency-light information-retrieval evaluation metrics."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from documind.models import SearchResult


@dataclass(frozen=True)
class EvaluationQuestion:
    """A query with its expected source filename and page number."""

    query: str
    expected_filename: str
    expected_page: int


@dataclass(frozen=True)
class EvaluationMetrics:
    """Mean retrieval scores across a set of questions."""

    recall_at: dict[int, float]
    mean_reciprocal_rank: float


SearchFunction = Callable[[str, int], list[SearchResult]]


def evaluate(
    questions: Iterable[EvaluationQuestion],
    search: SearchFunction,
    cutoffs: tuple[int, ...] = (1, 3, 5),
) -> EvaluationMetrics:
    """Compute Recall@k and MRR using the expected filename and page as relevance."""
    question_list = list(questions)
    if not question_list:
        raise ValueError("evaluation requires at least one question")
    if not cutoffs or any(cutoff < 1 for cutoff in cutoffs):
        raise ValueError("cutoffs must contain positive integers")

    recall_hits = dict.fromkeys(cutoffs, 0)
    reciprocal_rank_sum = 0.0
    for question in question_list:
        results = search(question.query, max(cutoffs))
        relevant_ranks = [
            rank
            for rank, result in enumerate(results, start=1)
            if result.chunk.filename == question.expected_filename
            and result.chunk.page_number == question.expected_page
        ]
        if relevant_ranks:
            first_relevant = relevant_ranks[0]
            reciprocal_rank_sum += 1 / first_relevant
            for cutoff in cutoffs:
                recall_hits[cutoff] += int(first_relevant <= cutoff)

    total = len(question_list)
    return EvaluationMetrics(
        recall_at={cutoff: count / total for cutoff, count in recall_hits.items()},
        mean_reciprocal_rank=reciprocal_rank_sum / total,
    )
