from evals.relation_value_v3_review_compare import compare


def _row(unit: str | None) -> dict:
    return {
        "id": "rva3-001",
        "answerability": "full",
        "confusion_type": None,
        "primary_relation_role": "exact",
        "primary_span_type": "sentence_span",
        "demands": [
            {
                "relation_role": "exact",
                "value_semantic": "count",
                "canonical_unit": unit,
                "expected_binding": True,
                "accepted_value_sets": [["16"]],
                "modality": "fact",
            }
        ],
    }


def test_compare_reports_hard_label_difference() -> None:
    author = _row("GB")
    reviewer = {
        "id": "rva3-001",
        "reviewer_annotation": _row("MB"),
    }

    result = compare([author], [reviewer])

    assert result["disagreement_rows"] == 1
    assert result["differences"]["rva3-001"][0]["field"] == "demands[1].canonical_unit"
