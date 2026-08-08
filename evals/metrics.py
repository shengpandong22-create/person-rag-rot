from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievalCaseResult:
    case_id: str
    answerable: bool
    first_relevant_rank: int | None
    evidence_sufficient: bool


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    total: int
    recall_at_1: float
    recall_at_3: float
    recall_at_6: float
    mrr: float
    evidence_sufficient_accuracy: float
    negative_rejection_accuracy: float


def compute_retrieval_metrics(results: list[RetrievalCaseResult]) -> RetrievalMetrics:
    total = len(results)
    if total == 0:
        raise ValueError("results must not be empty.")

    answerable = [item for item in results if item.answerable]
    negatives = [item for item in results if not item.answerable]

    return RetrievalMetrics(
        total=total,
        recall_at_1=_recall_at(answerable, 1),
        recall_at_3=_recall_at(answerable, 3),
        recall_at_6=_recall_at(answerable, 6),
        mrr=_mrr(answerable),
        evidence_sufficient_accuracy=_accuracy(
            item.evidence_sufficient == item.answerable for item in results
        ),
        negative_rejection_accuracy=_accuracy(
            not item.evidence_sufficient for item in negatives
        ),
    )


def _recall_at(results: list[RetrievalCaseResult], k: int) -> float:
    if not results:
        return 0.0
    hits = sum(
        item.first_relevant_rank is not None and item.first_relevant_rank <= k
        for item in results
    )
    return round(hits / len(results), 4)


def _mrr(results: list[RetrievalCaseResult]) -> float:
    if not results:
        return 0.0
    score = sum(
        1 / item.first_relevant_rank
        for item in results
        if item.first_relevant_rank is not None
    )
    return round(score / len(results), 4)


def _accuracy(values: Iterable[object]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(bool(item) for item in items) / len(items), 4)
