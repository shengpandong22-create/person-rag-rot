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


@dataclass(frozen=True, slots=True)
class ScoringCaseResult:
    case_id: str
    predicted_total: int
    human_total: int
    predicted_review: bool
    expected_review: bool
    expected_band: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringMetrics:
    total: int
    mean_absolute_error: float
    pearson_correlation: float
    reviewer_routing_accuracy: float
    band_order_accuracy: float
    predicted_average_by_band: dict[str, float]
    human_average_by_band: dict[str, float]


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


def compute_scoring_metrics(results: list[ScoringCaseResult]) -> ScoringMetrics:
    total = len(results)
    if total == 0:
        raise ValueError("results must not be empty.")
    absolute_errors = [
        abs(item.predicted_total - item.human_total) for item in results
    ]
    return ScoringMetrics(
        total=total,
        mean_absolute_error=round(sum(absolute_errors) / total, 4),
        pearson_correlation=_pearson(
            [item.predicted_total for item in results],
            [item.human_total for item in results],
        ),
        reviewer_routing_accuracy=_accuracy(
            item.predicted_review == item.expected_review for item in results
        ),
        band_order_accuracy=_band_order_accuracy(results),
        predicted_average_by_band=_average_by_band(results, "predicted_total"),
        human_average_by_band=_average_by_band(results, "human_total"),
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


def _pearson(left: list[int], right: list[int]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (left_item - left_mean) * (right_item - right_mean)
        for left_item, right_item in zip(left, right, strict=True)
    )
    left_denominator = sum((item - left_mean) ** 2 for item in left) ** 0.5
    right_denominator = sum((item - right_mean) ** 2 for item in right) ** 0.5
    if left_denominator == 0 or right_denominator == 0:
        return 0.0
    return round(numerator / (left_denominator * right_denominator), 4)


def _average_by_band(results: list[ScoringCaseResult], field: str) -> dict[str, float]:
    grouped: dict[str, list[int]] = {}
    for item in results:
        if item.expected_band is None:
            continue
        grouped.setdefault(item.expected_band, []).append(getattr(item, field))
    return {
        band: round(sum(values) / len(values), 4)
        for band, values in sorted(grouped.items())
        if values
    }


def _band_order_accuracy(results: list[ScoringCaseResult]) -> float:
    averages = _average_by_band(results, "predicted_total")
    required = ("low", "mid", "high")
    if any(band not in averages for band in required):
        return 0.0
    checks = [
        averages["low"] < averages["mid"],
        averages["mid"] < averages["high"],
        averages["high"] - averages["low"] >= 6,
    ]
    return _accuracy(checks)
