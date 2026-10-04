from evals.relation_value_v3_blind_review import create_worksheet


def test_worksheet_excludes_author_labels() -> None:
    rows = [
        {
            "id": "rva3-001",
            "question": "q",
            "answerability": "full",
            "confusion_type": None,
            "primary_relation_role": "exact",
            "primary_span_type": "sentence_span",
            "demands": [{"accepted_value_sets": [["16"]]}],
            "pair_id": "pair",
            "annotation": {"author": "a"},
            "tags": ["positive"],
            "evidence": [
                {
                    "evidence_id": "e1",
                    "chunk_id": "chunk",
                    "document_logical_name": "doc",
                    "heading_path": ["doc", "section"],
                    "span_text": "text 16",
                    "span_sha256": "span",
                    "source_content_hash": "source",
                    "supports_demand_ids": ["d1"],
                }
            ],
        }
    ]

    worksheet = create_worksheet(rows)

    assert worksheet[0]["reviewer_annotation"]["demands"] == []
    serialized = repr(worksheet)
    for hidden in (
        "accepted_value_sets",
        "supports_demand_ids",
        "pair_id",
        "author",
        "positive",
        "sentence_span",
    ):
        assert hidden not in serialized
