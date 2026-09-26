from __future__ import annotations

import pytest

from evals.metrics import (
    RetrievalCaseResult,
    ScoringCaseResult,
    compute_retrieval_metrics,
    compute_scoring_metrics,
)


def test_compute_retrieval_metrics_reports_recall_mrr_and_rejection_accuracy() -> None:
    metrics = compute_retrieval_metrics(
        [
            RetrievalCaseResult("a", True, 1, True),
            RetrievalCaseResult("b", True, 4, True),
            RetrievalCaseResult("c", True, None, False),
            RetrievalCaseResult("d", False, None, False),
        ]
    )

    assert metrics.total == 4
    assert metrics.recall_at_1 == 0.3333
    assert metrics.recall_at_3 == 0.3333
    assert metrics.recall_at_6 == 0.6667
    assert metrics.mrr == 0.4167
    assert metrics.evidence_sufficient_accuracy == 0.75
    assert metrics.negative_rejection_accuracy == 1.0
    assert metrics.full_answerability_accuracy == 0.0
    assert metrics.partial_answerability_accuracy == 0.0
    assert metrics.average_candidate_count == 0.0


def test_compute_retrieval_metrics_rejects_empty_results() -> None:
    with pytest.raises(ValueError):
        compute_retrieval_metrics([])


def test_retrieval_stage_metrics_use_raw_and_post_filter_ranks() -> None:
    metrics = compute_retrieval_metrics(
        [
            RetrievalCaseResult(
                "hit",
                True,
                2,
                True,
                first_raw_candidate_rank=4,
                first_post_filter_rank=2,
                raw_candidate_count=20,
            ),
            RetrievalCaseResult(
                "cutoff",
                True,
                None,
                False,
                first_raw_candidate_rank=8,
                first_post_filter_rank=7,
                raw_candidate_count=20,
                diversity_filtered_count=3,
                failure_category="ranking_cutoff_miss",
            ),
        ]
    )

    assert metrics.candidate_recall_at_20 == 1.0
    assert metrics.pre_filter_recall_at_6 == 0.5
    assert metrics.post_filter_recall_at_6 == 0.5
    assert metrics.diversity_filter_drop_rate == 0.075
    assert metrics.failure_category_counts == {"ranking_cutoff_miss": 1}


def test_compute_scoring_metrics_reports_error_and_review_accuracy() -> None:
    metrics = compute_scoring_metrics(
        [
            ScoringCaseResult("a", 10, 8, False, False),
            ScoringCaseResult("b", 6, 8, True, False),
        ]
    )
    assert metrics.total == 2
    assert metrics.mean_absolute_error == 2.0
    assert metrics.reviewer_routing_accuracy == 0.5
    assert metrics.band_order_accuracy == 0.0


def test_compute_scoring_metrics_reports_band_discrimination() -> None:
    metrics = compute_scoring_metrics(
        [
            ScoringCaseResult("low-1", 5, 4, True, True, "low"),
            ScoringCaseResult("mid-1", 12, 12, False, False, "mid"),
            ScoringCaseResult("high-1", 18, 18, False, False, "high"),
        ]
    )

    assert metrics.band_order_accuracy == 1.0
    assert metrics.predicted_average_by_band == {"high": 18.0, "low": 5.0, "mid": 12.0}
    assert metrics.human_average_by_band == {"high": 18.0, "low": 4.0, "mid": 12.0}
