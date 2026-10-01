from evals.trigger_diagnostics import (
    analyze_heading_negative_gate,
    analyze_low_overlap_recall,
)


def test_low_overlap_diagnostic_separates_candidate_and_ranking_loss() -> None:
    cases = [
        _retrieval_case("candidate", raw=None, final=None, supplemental=None),
        _retrieval_case("ranking", raw=7, final=None, supplemental=3),
    ]

    result = analyze_low_overlap_recall(cases)

    assert result["loss_stage_counts"] == {
        "ranking_cutoff": 1,
        "vector_candidate_miss": 1,
    }
    assert result["vector_candidate_recall_at_20"] == 0.5
    assert result["heading_supplemental_recall_at_20"] == 0.5


def test_gate_diagnostic_detects_unbound_and_unenforced_numbers() -> None:
    cases = [
        _gate_case("incidental", requested=[], covered=[], matched_signals=["60"]),
        _gate_case("explicit", requested=["1%"], covered=[], matched_signals=[]),
    ]

    result = analyze_heading_negative_gate(cases)

    assert result["false_acceptance_count"] == 2
    assert result["root_cause_counts"] == {
        "explicit_number_not_enforced": 1,
        "unbound_incidental_number": 1,
    }


def _retrieval_case(
    case_id: str,
    *,
    raw: int | None,
    final: int | None,
    supplemental: int | None,
) -> dict[str, object]:
    return {
        "id": case_id,
        "tags": ["low_overlap_semantic_positive"],
        "first_raw_candidate_rank": raw,
        "first_post_filter_rank": raw,
        "first_relevant_rank": final,
        "first_supplemental_rank": supplemental,
    }


def _gate_case(
    case_id: str,
    *,
    requested: list[str],
    covered: list[str],
    matched_signals: list[str],
) -> dict[str, object]:
    return {
        "id": case_id,
        "tags": ["heading_similar_negative"],
        "evidence_assessment": {
            "decision": "full",
            "production_sufficient": True,
            "coverage_ratio": 0.3,
            "numeric_tokens_requested": requested,
            "numeric_tokens_covered": covered,
            "demand_markers": ["多少"],
            "demand_assessments": [
                {
                    "demand_type": "exact_value",
                    "matched_signals": matched_signals,
                }
            ],
        },
    }
