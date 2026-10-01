from __future__ import annotations

from evals.retrieval_uncertainty import (
    UncertaintyRow,
    _classification_metrics,
    analyze_uncertainty,
    extract_uncertainty_row,
)


def test_extract_uncertainty_row_labels_only_rank1_recoverable_miss() -> None:
    case = {
        "id": "dev-pos-001",
        "question": "发布日期是什么？",
        "answerability": "full",
        "answerable": True,
        "first_relevant_rank": None,
        "first_supplemental_rank": 1,
        "primary_evidence_decision": "full",
        "top_chunks": [
            {"vector_score": 0.8},
            {"vector_score": 0.7},
            {"vector_score": 0.6},
        ],
        "retrieval_stages": {
            "vector_candidate_ids": ["v1", "v2"],
            "heading_candidate_ids": ["h1", "v1"],
        },
        "supplemental_chunks": [
            {
                "heading_rank": 1,
                "heading_score": 2.5,
                "heading_path": ["版本发布日期"],
            }
        ],
    }

    row = extract_uncertainty_row(case)

    assert row.recoverable_miss is True
    assert row.vector_margin_1_2 == 0.1
    assert row.top_heading_outside_vector is True
    assert row.heading_vector_overlap_ratio == 0.5
    assert row.demand_heading_overlap > 0


def test_analyze_uncertainty_reports_feature_separation_without_accepting_rule() -> None:
    rows = [
        _row("positive", True, 0.1),
        _row("negative-1", False, 0.8),
        _row("negative-2", False, 0.9),
    ]

    result = analyze_uncertainty(rows)

    assert result["recoverable_miss_count"] == 1
    rule = result["features"]["vector_top1_score"]["best_exploratory_rule"]
    assert rule["direction"] == "low"
    assert rule["precision"] == 1.0
    assert rule["recall"] == 1.0
    assert result["two_feature_exploration"]["and"]["f1"] == 1.0
    assert _classification_metrics([True, False], [True, False])["f1"] == 1.0


def _row(case_id: str, target: bool, score: float) -> UncertaintyRow:
    return UncertaintyRow(
        case_id=case_id,
        recoverable_miss=target,
        answerability="full",
        vector_top1_score=score,
        vector_margin_1_2=score,
        vector_span_1_6=score,
        heading_vector_overlap_ratio=score,
        top_heading_outside_vector=target,
        supplemental_heading_rank=1,
        supplemental_heading_score=1 - score,
        demand_heading_overlap=1 - score,
        primary_gate_reject=False,
    )
