from pathlib import Path

from evals.shadow_agent_v2_eval import load_cases


def test_v2_development_fixture_is_independent_and_covers_all_objectives() -> None:
    cases = load_cases(Path("evals/datasets/shadow_agent_v2_development_v1.jsonl"))

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
    assert sum("expected_second_tool" in case for case in cases) == 2
