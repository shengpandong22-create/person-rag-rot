from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from agent_mentor.application.shadow_agent_service import ShadowAgentService
from agent_mentor.domain.shadow_agent import ShadowToolArguments, ShadowToolName
from agent_mentor.infrastructure.fakes import FakeLLMGateway

DEFAULT_DATASET = Path("evals/datasets/shadow_agent_development_v1.jsonl")


@dataclass(slots=True)
class FixtureTools:
    results: dict[str, dict[str, object]]

    async def execute(
        self,
        tool_name: ShadowToolName,
        *,
        user_id: object,
        knowledge_base_id: object,
        arguments: ShadowToolArguments,
    ) -> dict[str, object]:
        del user_id, knowledge_base_id, arguments
        return self.results.get(tool_name.value, {"items": []})


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


async def evaluate(path: Path) -> dict[str, object]:
    cases = load_cases(path)
    rows: list[dict[str, object]] = []
    for case in cases:
        gateway = FakeLLMGateway(structured_responses=list(case["decisions"]))
        run = await ShadowAgentService(FixtureTools(case["tool_results"]), gateway).recommend(
            user_id=uuid4(), knowledge_base_id=uuid4()
        )
        first_tool = next(
            (
                step.tool_name.value
                for step in run.steps
                if step.decision == "tool" and step.tool_name is not None
            ),
            None,
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "status": run.status,
                "expected_status": case["expected_status"],
                "first_tool": first_tool,
                "expected_first_tool": case["expected_first_tool"],
                "action": run.recommendation.recommended_action.value,
                "expected_action": case["expected_action"],
                "step_count": len(run.steps),
                "business_writes": run.business_writes,
                "requires_confirmation": run.recommendation.requires_confirmation,
                "termination_reason": run.termination_reason,
            }
        )
    total = len(rows)
    metrics = {
        "case_count": total,
        "status_accuracy": sum(row["status"] == row["expected_status"] for row in rows)
        / total,
        "first_tool_accuracy": sum(
            row["first_tool"] == row["expected_first_tool"] for row in rows
        )
        / total,
        "recommendation_action_accuracy": sum(
            row["action"] == row["expected_action"] for row in rows
        )
        / total,
        "max_step_adherence": sum(
            cast(int, row["step_count"]) <= 3 for row in rows
        )
        / total,
        "confirmation_guard_rate": sum(bool(row["requires_confirmation"]) for row in rows)
        / total,
        "business_zero_write_rate": sum(row["business_writes"] == 0 for row in rows)
        / total,
    }
    return {"dataset": str(path), "metrics": metrics, "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the read-only shadow agent contract.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.dataset))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
