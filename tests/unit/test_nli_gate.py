from __future__ import annotations

from evals.nli_gate import NLIPairScore, aggregate_claim_statuses, combined_status, semantic_status


def _score(label: str, *, chunk_id: str = "chunk") -> NLIPairScore:
    values = {
        "entailment": (0.8, 0.1, 0.1),
        "neutral": (0.1, 0.8, 0.1),
        "contradiction": (0.1, 0.1, 0.8),
    }[label]
    return NLIPairScore(chunk_id, *values, label)


def test_semantic_status_prefers_any_entailed_evidence() -> None:
    status, chunk_id = semantic_status(
        [_score("neutral", chunk_id="a"), _score("entailment", chunk_id="b")]
    )

    assert status == "supported"
    assert chunk_id == "b"


def test_semantic_status_can_select_aggregated_context() -> None:
    status, chunk_id = semantic_status(
        [_score("neutral", chunk_id="a"), _score("entailment", chunk_id="top3-combined")]
    )

    assert status == "supported"
    assert chunk_id == "top3-combined"


def test_semantic_status_reports_contradiction_when_no_evidence_entails() -> None:
    status, chunk_id = semantic_status(
        [_score("neutral", chunk_id="a"), _score("contradiction", chunk_id="b")]
    )

    assert status == "contradicted"
    assert chunk_id == "b"


def test_combined_policy_keeps_deterministic_missing_value_rejection() -> None:
    assert combined_status("unsupported", "supported") == "unsupported"
    assert combined_status("supported", "contradicted") == "contradicted"
    assert combined_status("unknown", "supported") == "supported"
    assert combined_status("supported", "unknown", semantic_available=False) == "supported"


def test_claim_status_aggregation_is_three_way() -> None:
    assert aggregate_claim_statuses(["supported", "supported"]) == "full"
    assert aggregate_claim_statuses(["supported", "unknown"]) == "partial"
    assert aggregate_claim_statuses(["unknown", "contradicted"]) == "none"
