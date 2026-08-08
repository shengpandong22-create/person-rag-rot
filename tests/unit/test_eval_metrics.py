from __future__ import annotations

import pytest

from evals.metrics import RetrievalCaseResult, compute_retrieval_metrics


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


def test_compute_retrieval_metrics_rejects_empty_results() -> None:
    with pytest.raises(ValueError):
        compute_retrieval_metrics([])
