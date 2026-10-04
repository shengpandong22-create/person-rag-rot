import json
from pathlib import Path
from typing import Any

CONTRACT = Path("docs/design/two-stage-retrieval-contract-v1.json")


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_two_stage_contract_is_design_only_and_user_triggered() -> None:
    contract = _contract()

    assert contract["status"] == "design-only"
    assert contract["production_authorized"] is False
    assert contract["endpoint"]["method"] == "POST"
    assert contract["request"]["fields"]["trigger"]["allowed"] == [
        "user_requested_more_evidence"
    ]
    assert "question" in contract["request"]["client_must_not_supply"]
    assert "allow_model_knowledge" in contract["request"]["client_must_not_supply"]


def test_two_stage_contract_preserves_primary_results() -> None:
    invariants = _contract()["retrieval_invariants"]

    assert invariants["primary_top_k"] == 6
    assert invariants["primary_order_preserved"] is True
    assert invariants["primary_chunks_may_be_removed"] is False
    assert invariants["rrf_weight_change_allowed"] is False
    assert invariants["embedding_change_allowed"] is False
    assert invariants["evidence_gate_change_allowed"] is False


def test_two_stage_contract_has_bounded_context() -> None:
    budget = _contract()["context_budget"]

    assert budget["supplemental_chunks_max"] == 7
    assert budget["combined_chunks_max"] == 13
    assert budget["combined_chunks_max"] == (
        _contract()["retrieval_invariants"]["primary_top_k"]
        + budget["supplemental_chunks_max"]
    )
    assert budget["supplemental_content_chars_max"] <= 7000
    assert budget["combined_content_chars_max"] <= 18000
    assert budget["truncate_chunk_content"] is False
    assert budget["budget_overflow_policy"] == "stop_before_next_whole_chunk"


def test_two_stage_contract_requires_complete_trace() -> None:
    trace = _contract()["trace"]
    required = set(trace["required_fields"])

    assert trace["raw_question_persisted_in_trace"] is False
    assert {
        "primary_chunk_ids",
        "consumed_supplemental_chunk_ids",
        "budget_rejected_chunk_ids",
        "combined_context_chunk_ids",
        "evidence_decision_before",
        "evidence_decision_after",
        "retrieval_latency_ms",
        "generation_latency_ms",
        "total_latency_ms",
    } <= required


def test_two_stage_contract_requires_database_backed_idempotency() -> None:
    identity = _contract()["identity_and_idempotency"]

    assert identity["completed_expansions_per_parent_max"] == 1
    assert identity["same_key_replays_stored_response"] is True
    assert identity["different_key_after_completion_status"] == 409
    assert identity["concurrent_claim_requires_database_unique_constraint"] is True
