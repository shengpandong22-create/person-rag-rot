import json
from pathlib import Path

import evals.retrieval_expansion_regression as regression_module
from evals.retrieval_expansion_regression import judge_regression

THRESHOLDS = Path("evals/datasets/RETRIEVAL_EXPANSION_REGRESSION_THRESHOLDS.json")


def test_regression_protocol_freezes_candidate_only_safety_boundaries() -> None:
    payload = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    assert payload["candidate"] == "primary-context-dedupe-v1"
    assert payload["configuration"]["primary_top_k"] == 6
    assert payload["configuration"]["supplemental_chunks_max"] == 7
    assert payload["hard_gates"]["primary_top6_identity_rate_min"] == 1.0
    assert payload["hard_gates"]["negative_decision_mutation_count_max"] == 0
    assert payload["hard_gates"]["gate_invocation_count_max"] == 0
    assert payload["hard_gates"]["generation_invocation_count_max"] == 0


def test_regression_judge_passes_only_when_every_hard_gate_passes() -> None:
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    metrics = _passing_metrics()
    assert judge_regression(metrics, thresholds)["qualified"] is True

    metrics["primary_top6_identity_rate"] = 0.9667
    result = judge_regression(metrics, thresholds)
    assert result["qualified"] is False
    assert result["checks"]["primary_top6_identity"] is False


def test_regression_judge_rejects_gate_or_generation_invocation() -> None:
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    for field in ("gate_invocation_count", "generation_invocation_count"):
        metrics = _passing_metrics()
        metrics[field] = 1
        assert judge_regression(metrics, thresholds)["qualified"] is False


def test_regression_runner_does_not_import_gate_answer_service_or_llm() -> None:
    source = Path(regression_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("AnswerService", "EvidenceGate", "LLMGateway"):
        assert forbidden not in source


def _passing_metrics() -> dict[str, float | int]:
    return {
        "source_label_resolution_rate": 1.0,
        "primary_top6_identity_rate": 1.0,
        "baseline_primary_recall": 0.8,
        "primary_recall_delta": 0.0,
        "combined_recall": 0.9,
        "negative_decision_mutation_count": 0,
        "gate_invocation_count": 0,
        "generation_invocation_count": 0,
        "duplicate_free_combined_rate": 1.0,
        "budget_compliance_rate": 1.0,
        "average_consumed_supplemental_count": 6.0,
        "max_supplemental_content_chars": 6000,
        "max_combined_content_chars": 17000,
        "supplemental_latency_p95_ms": 100.0,
    }
