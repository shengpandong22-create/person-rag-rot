from pathlib import Path

from evals.shadow_agent_eval import load_cases

DATASET = Path("evals/datasets/shadow_agent_development_v1.jsonl")


def test_shadow_agent_v1_fixture_is_preserved_as_historical_evidence() -> None:
    cases = load_cases(DATASET)

    assert len(cases) == 20
    assert len({case["case_id"] for case in cases}) == 20
    assert {case["expected_status"] for case in cases} == {"completed", "fallback"}
