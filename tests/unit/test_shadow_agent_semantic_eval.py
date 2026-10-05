from pathlib import Path

from evals.shadow_agent_semantic_eval import load_cases


def test_semantic_development_fixture_has_objectives_and_expectations() -> None:
    cases = load_cases(Path("evals/datasets/shadow_agent_semantic_development_v1.jsonl"))

    assert len(cases) == 12
    assert len({case["case_id"] for case in cases}) == 12
    assert {
        case["objective"] for case in cases
    } == {
        "balanced",
        "strengthen_weaknesses",
        "close_coverage_gaps",
        "continue_review",
    }
    assert all("expected_action" in case or "acceptable_actions" in case for case in cases)
