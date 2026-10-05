from pathlib import Path

from evals.retrieval_expansion_development import _metrics, _qualify, audit_fixture

DATASET = Path("evals/datasets/retrieval_expansion_development_v1.jsonl")
THRESHOLDS = Path("evals/datasets/RETRIEVAL_EXPANSION_DEVELOPMENT_THRESHOLDS.json")


def test_expansion_development_fixture_contract_is_balanced() -> None:
    audit = audit_fixture(DATASET)
    assert audit.case_count == 12
    assert audit.scenario_counts == {
        "deep_heading_target": 4,
        "primary_coverage_control": 4,
        "semantic_paraphrase_target": 4,
    }


def test_metrics_measure_incremental_recovery_precision_budget_and_latency() -> None:
    rows = [
        _row(primary_hit=False, candidate_hit=True, combined_hit=True, relevant=1, latency=10),
        _row(primary_hit=False, candidate_hit=True, combined_hit=False, relevant=0, latency=20),
        _row(primary_hit=True, candidate_hit=False, combined_hit=True, relevant=0, latency=30),
        _row(primary_hit=True, candidate_hit=False, combined_hit=True, relevant=1, latency=40),
    ]
    metrics = _metrics(rows)
    assert metrics["primary_recall"] == 0.5
    assert metrics["combined_recall"] == 0.75
    assert metrics["combined_recall_gain"] == 0.25
    assert metrics["primary_miss_incremental_recovery_rate"] == 0.5
    assert metrics["supplemental_candidate_recall_on_primary_miss"] == 1.0
    assert metrics["supplemental_consumption_precision"] == 0.125
    assert metrics["supplemental_latency_p50_ms"] == 30.0
    assert metrics["supplemental_latency_p95_ms"] == 40.0


def test_qualification_is_machine_decided_from_predeclared_thresholds() -> None:
    import json

    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    metrics = _metrics(
        [
            _row(primary_hit=False, candidate_hit=True, combined_hit=True, relevant=1, latency=10),
            _row(primary_hit=False, candidate_hit=True, combined_hit=True, relevant=1, latency=20),
            _row(primary_hit=True, candidate_hit=False, combined_hit=True, relevant=0, latency=30),
            _row(primary_hit=True, candidate_hit=False, combined_hit=True, relevant=0, latency=40),
        ]
    )
    qualification = _qualify(metrics, thresholds)
    assert qualification["qualified"] is True
    assert all(qualification["checks"].values())


def _row(
    *,
    primary_hit: bool,
    candidate_hit: bool,
    combined_hit: bool,
    relevant: int,
    latency: float,
) -> dict[str, object]:
    return {
        "ground_truth_resolution": "resolved",
        "primary_hit": primary_hit,
        "supplemental_candidate_hit": candidate_hit,
        "combined_hit": combined_hit,
        "consumed_relevant_chunk_ids": [str(index) for index in range(relevant)],
        "consumed_supplemental_count": 4,
        "primary_order_preserved": True,
        "duplicate_free_combined": True,
        "budget_compliant": True,
        "supplemental_candidate_count": 7,
        "supplemental_content_chars": 1000,
        "supplemental_latency_ms": latency,
    }
