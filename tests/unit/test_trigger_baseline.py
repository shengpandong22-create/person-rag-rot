from evals.trigger_baseline import analyze_trigger_baseline


def test_trigger_baseline_keeps_expected_and_actual_labels_separate() -> None:
    fixture = [
        {
            "id": "expected-only",
            "trigger_scenario": "positive",
            "expected_trigger": True,
        },
        {
            "id": "actual-only",
            "trigger_scenario": "boundary",
            "expected_trigger": False,
        },
    ]
    reports = [
        _case("expected-only", first_supplemental_rank=None, overlap=0.1, score=2.0),
        _case("actual-only", first_supplemental_rank=1, overlap=0.5, score=22.0),
    ]

    result = analyze_trigger_baseline(fixture, reports)

    assert result["expected_vs_actual"] == {
        "both_true": 0,
        "expected_only": 1,
        "actual_only": 1,
        "both_false": 0,
    }
    rule = result["rule_results"]["overlap_high"]
    assert rule["against_expected_trigger"]["precision"] == 0.0
    assert rule["against_actual_recoverable"]["precision"] == 1.0


def _case(
    case_id: str, *, first_supplemental_rank: int | None, overlap: float, score: float
) -> dict[str, object]:
    # The lexical overlap helper sees one shared token when overlap is high.
    question = "shared term" if overlap >= 0.5 else "unrelated"
    heading = ["shared term"] if overlap >= 0.5 else ["different"]
    return {
        "id": case_id,
        "question": question,
        "answerability": "full",
        "answerable": True,
        "first_relevant_rank": None,
        "first_raw_candidate_rank": None,
        "first_supplemental_rank": first_supplemental_rank,
        "primary_evidence_decision": "full",
        "failure_category": "candidate_recall_miss",
        "top_chunks": [{"vector_score": 0.8}],
        "retrieval_stages": {
            "vector_candidate_ids": ["v1"],
            "heading_candidate_ids": ["h1"],
        },
        "supplemental_chunks": [
            {
                "heading_rank": 1,
                "heading_score": score,
                "heading_path": heading,
            }
        ],
    }
