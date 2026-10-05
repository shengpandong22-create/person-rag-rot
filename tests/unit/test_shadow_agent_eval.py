from pathlib import Path
from typing import cast

import pytest

from evals.shadow_agent_eval import evaluate, load_cases

DATASET = Path("evals/datasets/shadow_agent_development_v1.jsonl")


def test_shadow_agent_fixture_has_twenty_unique_cases() -> None:
    cases = load_cases(DATASET)

    assert len(cases) == 20
    assert len({case["case_id"] for case in cases}) == 20
    assert {case["expected_status"] for case in cases} == {"completed", "fallback"}


@pytest.mark.asyncio
async def test_shadow_agent_contract_fixture_passes_all_hard_guards() -> None:
    report = await evaluate(DATASET)
    metrics = cast(dict[str, float], report["metrics"])

    assert metrics["status_accuracy"] == 1
    assert metrics["first_tool_accuracy"] == 1
    assert metrics["recommendation_action_accuracy"] == 1
    assert metrics["max_step_adherence"] == 1
    assert metrics["confirmation_guard_rate"] == 1
    assert metrics["business_zero_write_rate"] == 1
