from evals.runtime_baseline import RuntimeMeasurement, build_runtime_report, summarize_measurements


def test_summarize_measurements_uses_successes_for_latency_and_all_rows_for_failure_rate() -> None:
    metrics = summarize_measurements(
        [
            RuntimeMeasurement("fallback", "retrieval", "a", 1, 10.0, True, 200),
            RuntimeMeasurement("fallback", "retrieval", "b", 1, 30.0, True, 200),
            RuntimeMeasurement("fallback", "retrieval", "c", 1, 100.0, False, 500),
        ]
    )

    assert metrics == {
        "sample_count": 3,
        "success_count": 2,
        "failure_count": 1,
        "failure_rate": 0.3333,
        "latency_p50_ms": 10.0,
        "latency_p95_ms": 30.0,
    }


def test_build_runtime_report_separates_mode_and_phase() -> None:
    report = build_runtime_report(
        metadata={"knowledge_base_id": "fixture"},
        measurements=[
            RuntimeMeasurement("fallback", "retrieval", "a", 1, 10.0, True, 200),
            RuntimeMeasurement("llm", "end_to_end", "a", 1, 30.0, True, 200),
        ],
    )

    assert set(report["metrics"].keys()) == {"fallback:retrieval", "llm:end_to_end"}
