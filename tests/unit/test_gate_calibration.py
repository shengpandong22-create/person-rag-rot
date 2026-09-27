from __future__ import annotations

from evals.gate_calibration import eligible_candidates, replay_report


def _row(
    case_id: str,
    answerability: str,
    *,
    sufficient: bool,
    coverage: float,
    covered: tuple[str, ...] = (),
    requested_numbers: tuple[str, ...] = (),
    covered_numbers: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "id": case_id,
        "answerability": answerability,
        "negative_reason": "false_premise" if answerability == "none" else None,
        "evidence_assessment": {
            "production_sufficient": sufficient,
            "coverage_ratio": coverage,
            "specific_query_terms": ["a", "b", "c", "d"],
            "covered_terms": list(covered),
            "numeric_tokens_requested": list(requested_numbers),
            "numeric_tokens_covered": list(covered_numbers),
            "clause_assessments": [],
            "demand_assessments": [],
            "claim_decision": "full" if sufficient else "none",
            "claim_assessments": [],
        },
    }


def test_replay_preserves_binary_baseline_and_exposes_partial_as_full() -> None:
    report = {
        "cases": [
            _row("full", "full", sufficient=True, coverage=0.5),
            _row("partial", "partial", sufficient=True, coverage=0.2),
            _row("none", "none", sufficient=True, coverage=0.1),
        ]
    }

    baseline = replay_report(report)[0]

    assert baseline.policy == "current_binary_v1"
    assert baseline.full_acceptance_rate == 1.0
    assert baseline.partial_boundary_detection_rate == 0.0
    assert baseline.none_rejection_rate == 0.0
    assert baseline.confusion_matrix["partial"]["full"] == 1


def test_coverage_replay_can_detect_partial_and_reject_none_safely() -> None:
    report = {
        "cases": [
            _row("full", "full", sufficient=True, coverage=0.5),
            _row("partial", "partial", sufficient=True, coverage=0.2),
            _row("none", "none", sufficient=True, coverage=0.1),
        ]
    }

    result = next(
        item
        for item in replay_report(report)
        if item.policy == "specific_coverage_ratio" and item.parameters == {"minimum": 0.3}
    )

    assert result.full_acceptance_rate == 1.0
    assert result.partial_boundary_detection_rate == 1.0
    assert result.none_rejection_rate == 1.0
    assert result.false_rejection_case_ids == ()


def test_eligible_candidates_enforce_full_acceptance_floor() -> None:
    report = {
        "cases": [
            *[
                _row(f"full-{index}", "full", sufficient=True, coverage=0.5)
                for index in range(9)
            ],
            _row("full-low", "full", sufficient=True, coverage=0.1),
            _row("none", "none", sufficient=True, coverage=0.1),
        ]
    }

    candidates = eligible_candidates(replay_report(report))

    assert candidates
    assert all(item.full_acceptance_rate >= 0.9 for item in candidates)


def test_clause_demand_policy_marks_uncovered_demand_as_partial() -> None:
    row = _row("partial", "partial", sufficient=True, coverage=0.5)
    assessment = row["evidence_assessment"]
    assert isinstance(assessment, dict)
    assessment["clause_assessments"] = [
        {"text": "checkpoint 如何恢复", "lexical_support": True}
    ]
    assessment["demand_assessments"] = [
        {"demand_type": "exact_value", "matched": False}
    ]

    result = next(
        item
        for item in replay_report({"cases": [row]})
        if item.policy == "clause_demand_v1"
    )

    assert result.partial_boundary_detection_rate == 1.0


def test_claim_gate_policy_replays_recorded_claim_decision() -> None:
    row = _row("partial", "partial", sufficient=True, coverage=0.5)
    assessment = row["evidence_assessment"]
    assert isinstance(assessment, dict)
    assessment["claim_decision"] = "partial"

    result = next(
        item
        for item in replay_report({"cases": [row]})
        if item.policy == "claim_gate_v1"
    )

    assert result.partial_boundary_detection_rate == 1.0


def test_single_demand_ablation_changes_only_targeted_claim_type() -> None:
    row = _row("partial", "partial", sufficient=True, coverage=0.5)
    assessment = row["evidence_assessment"]
    assert isinstance(assessment, dict)
    assessment["claim_assessments"] = [
        {
            "requirement_types": ["date"],
            "status": "unsupported",
        }
    ]

    results = replay_report({"cases": [row]})
    date = next(
        item
        for item in results
        if item.policy == "claim_demand_only"
        and item.parameters == {"demand_type": "date"}
    )
    exact_value = next(
        item
        for item in results
        if item.policy == "claim_demand_only"
        and item.parameters == {"demand_type": "exact_value"}
    )

    assert date.partial_boundary_detection_rate == 1.0
    assert exact_value.partial_boundary_detection_rate == 0.0
