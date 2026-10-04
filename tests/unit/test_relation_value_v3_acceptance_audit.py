import hashlib
from pathlib import Path

from evals.relation_value_v3_acceptance_audit import (
    audit,
    normalized_question,
    normalized_span_hash,
)


def test_normalization_ignores_case_and_punctuation() -> None:
    assert normalized_question("RRF 的 K=60？") == normalized_question("rrf 的 k 60")


def test_span_hash_normalizes_line_endings() -> None:
    assert normalized_span_hash("a\r\nb") == normalized_span_hash("a\nb")


def test_audit_rejects_overlap_bad_hash_and_same_reviewer(tmp_path: Path) -> None:
    source_root = tmp_path / "docs"
    source_root.mkdir()
    source = source_root / "示例.md"
    source.write_text("值为 5 条。\n", encoding="utf-8")
    row = {
        "id": "rva3-001",
        "split": "acceptance",
        "label_origin": "human",
        "question": "最终返回多少条？",
        "answerability": "full",
        "confusion_type": None,
        "primary_relation_role": "exact",
        "primary_span_type": "sentence_span",
        "pair_id": None,
        "demands": [
            {
                "demand_id": "d1",
                "requested_relation": "最终返回数量",
                "relation_role": "exact",
                "value_semantic": "count",
                "canonical_unit": "条",
                "expected_binding": True,
                "accepted_value_sets": [["5"]],
                "evidence_ids": ["e1"],
                "required_relation_terms": ["返回"],
                "modality": "fact",
                "rationale": "source",
            }
        ],
        "evidence": [
            {
                "evidence_id": "e1",
                "chunk_id": "chunk",
                "document_logical_name": "示例",
                "heading_path": ["示例"],
                "span_type": "sentence_span",
                "span_text": "值为 5 条。",
                "span_sha256": "bad",
                "source_content_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                "supports_demand_ids": ["d1"],
            }
        ],
        "relevant_sources": [],
        "negative_reason": None,
        "annotation": {"author": "a", "reviewer": "a", "review_state": "agreed"},
        "tags": [],
    }
    plan = {
        "schema_version": "test",
        "total_rows": 1,
        "positive_rows": 1,
        "hard_negative_rows": 0,
        "multi_demand_rows": 0,
        "positive_span_distribution": {"sentence_span": 1},
        "positive_role_distribution": {"exact": 1},
        "hard_negative_distribution": {},
        "minimums": {
            "documents_represented": 1,
            "explicit_unit_positives": 1,
            "unitless_positives": 0,
            "unit_alias_or_conversion_positives": 0,
            "multi_value_positives": 0,
            "numeric_distractor_negatives": 0,
            "paired_hard_negatives": 0,
        },
        "maximums": {"positive_rows_per_document": 1},
        "required_review_state": "agreed",
    }

    result = audit([row], plan, source_root=source_root)

    assert not result["audit_passed"]
    assert "row 1: evidence span hash mismatch" in result["errors"]
    assert "row 1: author and reviewer must differ" in result["errors"]
