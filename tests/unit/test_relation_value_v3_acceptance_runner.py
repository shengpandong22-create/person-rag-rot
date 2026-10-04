import sys
from pathlib import Path
from typing import Any

import pytest

from evals.relation_value_binding_v3 import (
    EvidenceProvenance,
    TypedBoundValue,
    TypedRelationDemand,
)
from evals.relation_value_v3_acceptance_qualification import qualify
from evals.relation_value_v3_acceptance_runner import evaluate_rows, main


def _row(*, expected: bool, answerability: str, pair_id: str) -> dict[str, Any]:
    return {
        "id": f"case-{answerability}",
        "answerability": answerability,
        "confusion_type": None if expected else "relation_role",
        "pair_id": pair_id,
        "primary_span_type": "sentence_span",
        "demands": [
            {
                "demand_id": "d1",
                "requested_relation": "内存限制",
                "relation_role": "exact",
                "value_semantic": "generic",
                "canonical_unit": "GB",
                "accepted_value_sets": [["16"]] if expected else [],
                "modality": "fact",
                "expected_binding": expected,
                "evidence_ids": ["e1"] if expected else [],
            }
        ],
        "evidence": [
            {
                "evidence_id": "e1",
                "chunk_id": "chunk-1",
                "document_logical_name": "document",
                "heading_path": ["heading"],
                "span_type": "sentence_span",
                "span_text": "内存限制为 16GB。",
            }
        ],
    }


def _binding(
    demand: TypedRelationDemand,
    *,
    provenance: EvidenceProvenance,
    content: str,
) -> tuple[TypedBoundValue, ...]:
    if "不应绑定" in content:
        return ()
    return (
        TypedBoundValue(
            provenance=provenance,
            values=("16",),
            canonical_unit=demand.canonical_unit,
            role=demand.role,
            value_semantic=demand.value_semantic,
            span_type="sentence_span",
            span=content,
            relation_terms=("内存",),
        ),
    )


def test_runner_scores_positive_and_negative_without_formal_dataset() -> None:
    positive = _row(expected=True, answerability="full", pair_id="pair-1")
    negative = _row(expected=False, answerability="none", pair_id="pair-1")
    negative["evidence"][0]["span_text"] = "不应绑定"

    report = evaluate_rows([positive, negative], binder=_binding)

    assert report["metrics"]["demand_accuracy"] == 1.0
    assert report["metrics"]["binding_precision"] == 1.0
    assert report["metrics"]["paired_discrimination"] == 1.0
    assert report["metrics"]["negative_category_rejection"] == {
        "relation_role": 1.0
    }


def test_runner_marks_wrong_value_as_spurious() -> None:
    row = _row(expected=True, answerability="full", pair_id="pair-1")
    row["demands"][0]["accepted_value_sets"] = [["32"]]

    report = evaluate_rows([row], binder=_binding)
    demand = report["cases"][0]["demands"][0]

    assert demand["passed"] is False
    assert demand["failure_category"] == "binding_mismatch"
    assert demand["spurious_binding_count"] == 1
    assert report["metrics"]["binding_precision"] == 0.0


def test_machine_qualification_requires_every_check() -> None:
    thresholds = {
        "candidate": "candidate",
        "hard_gates": {
            "demand_accuracy_min": 1.0,
            "positive_demand_recall_min": 1.0,
            "positive_row_all_demands_accuracy_min": 1.0,
            "negative_demand_rejection_required": 1.0,
            "negative_row_rejection_required": 1.0,
            "binding_precision_min": 1.0,
            "average_bindings_per_demand_max": 1.0,
            "max_bindings_per_demand_max": 1,
            "paired_discrimination_min": 1.0,
            "span_success_count_min": {"sentence_span": 1},
            "role_success_count_min": {"exact": 1},
            "semantic_success_count_min": {"generic": 1},
            "negative_category_rejection_required": {"relation_role": 1.0},
            "evaluated_rows_required": 2,
            "evaluated_demands_required": 2,
            "unresolved_labels_required": 0,
            "case_errors_required": 0,
            "candidate_p95_ms_max": 50.0,
            "production_imports_candidate_required": False,
        },
    }
    positive = _row(expected=True, answerability="full", pair_id="pair-1")
    negative = _row(expected=False, answerability="none", pair_id="pair-1")
    negative["evidence"][0]["span_text"] = "不应绑定"
    report = evaluate_rows([positive, negative], binder=_binding)

    result = qualify(
        thresholds,
        report,
        candidate_freeze_before=True,
        candidate_freeze_after=True,
        acceptance_freeze_before=True,
        acceptance_freeze_after=True,
        production_imports_candidate=False,
        report_integrity=True,
        execution_freeze_before=True,
        execution_freeze_after=True,
    )

    assert result["accepted_for_production_integration_design"] is True
    result = qualify(
        thresholds,
        report,
        candidate_freeze_before=True,
        candidate_freeze_after=False,
        acceptance_freeze_before=True,
        acceptance_freeze_after=True,
        production_imports_candidate=False,
        report_integrity=True,
        execution_freeze_before=True,
        execution_freeze_after=True,
    )
    assert result["accepted_for_production_integration_design"] is False

    result = qualify(
        thresholds,
        report,
        candidate_freeze_before=True,
        candidate_freeze_after=True,
        acceptance_freeze_before=True,
        acceptance_freeze_after=True,
        production_imports_candidate=False,
        report_integrity=False,
        execution_freeze_before=True,
        execution_freeze_after=True,
    )
    assert result["checks"]["report_integrity"] is False
    assert result["accepted_for_production_integration_design"] is False

    result = qualify(
        thresholds,
        report,
        candidate_freeze_before=True,
        candidate_freeze_after=True,
        acceptance_freeze_before=True,
        acceptance_freeze_after=True,
        production_imports_candidate=False,
        report_integrity=True,
        execution_freeze_before=True,
        execution_freeze_after=False,
    )
    assert result["checks"]["execution_freeze_before_and_after"] is False
    assert result["accepted_for_production_integration_design"] is False


def test_cli_rejects_wrong_confirmation_without_creating_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "formal-output"
    monkeypatch.setattr(
        "evals.relation_value_v3_acceptance_runner.FINAL_OUTPUT_DIR", output
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner",
            "--confirm",
            "wrong",
        ],
    )

    with pytest.raises(SystemExit, match="confirmation token mismatch"):
        main()

    assert not output.exists()
