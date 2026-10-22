import pytest

from evals.scoring_stability import compute_stability_metrics


def test_compute_stability_metrics_reports_score_and_routing_changes() -> None:
    metrics = compute_stability_metrics(
        [
            {
                "correctness": 4,
                "completeness": 4,
                "reasoning": 4,
                "communication": 4,
                "total": 16,
                "needs_review": False,
                "status": "final",
                "review_decision": "not_needed",
            },
            {
                "correctness": 4,
                "completeness": 3,
                "reasoning": 4,
                "communication": 4,
                "total": 15,
                "needs_review": True,
                "status": "pending",
                "review_decision": "pending",
            },
        ]
    )

    assert metrics["total_score"] == {"min": 15, "max": 16, "mean": 15.5, "population_stddev": 0.5}
    assert metrics["exact_score_shape_stable"] is False
    assert metrics["review_routing_stable"] is False


def test_compute_stability_metrics_requires_two_runs() -> None:
    with pytest.raises(ValueError, match="at least two"):
        compute_stability_metrics(
            [
                {
                    "correctness": 4,
                    "completeness": 4,
                    "reasoning": 4,
                    "communication": 4,
                    "total": 16,
                    "needs_review": False,
                    "status": "final",
                    "review_decision": "not_needed",
                }
            ]
        )
