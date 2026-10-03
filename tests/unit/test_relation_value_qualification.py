from evals.relation_value_qualification import score_qualification


def test_qualification_separates_candidate_miss_and_false_acceptance() -> None:
    rows = [
        {"id": "p1", "expected_binding": True, "evidence_span_type": "sentence_span"},
        {"id": "p2", "expected_binding": True, "evidence_span_type": "table_row"},
        {"id": "n1", "expected_binding": False, "evidence_span_type": "code_statement"},
    ]
    retrieval = [
        {"id": "p1", "top_chunks": [{"matched_ground_truth": True}]},
        {"id": "p2", "top_chunks": [{"matched_ground_truth": False}]},
        {"id": "n1", "top_chunks": []},
    ]
    binding = {
        "cases": [
            {"id": "p1", "predicted_binding": True, "correct_labeled_binding": True},
            {"id": "p2", "predicted_binding": False, "correct_labeled_binding": False},
            {"id": "n1", "predicted_binding": True, "correct_labeled_binding": False},
        ]
    }

    result = score_qualification(rows, retrieval, binding)

    assert not result["qualified"]
    assert result["failures"] == {
        "candidate_recall_miss": ["p2"],
        "available_but_unbound": [],
        "wrong_provenance_only_acceptance": [],
        "false_acceptance": ["n1"],
    }
