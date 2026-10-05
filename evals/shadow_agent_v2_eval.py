from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import UUID, uuid4

from agent_mentor.application.shadow_agent_service import ShadowAgentService
from agent_mentor.config import get_settings
from agent_mentor.domain.shadow_agent import (
    PRIMARY_TOOL_BY_OBJECTIVE,
    ShadowToolArguments,
    ShadowToolName,
    ShadowTrainingObjective,
)
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway

DEFAULT_DATASET = Path("evals/datasets/shadow_agent_v2_development_v1.jsonl")


@dataclass(slots=True)
class V2FixtureTools:
    results: dict[str, dict[str, object]]

    async def execute(
        self,
        tool_name: ShadowToolName,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        arguments: ShadowToolArguments,
    ) -> dict[str, object]:
        del user_id, knowledge_base_id, arguments
        return self.results.get(tool_name.value, {"items": []})


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


async def evaluate(path: Path, rounds: int) -> dict[str, object]:
    settings = get_settings()
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_default_model):
        raise RuntimeError("A real LLM must be configured for V2 semantic evaluation.")
    gateway = OpenAICompatibleLLMGateway(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        default_model=settings.llm_default_model,
    )
    rows: list[dict[str, object]] = []
    try:
        for round_index in range(1, rounds + 1):
            for case in load_cases(path):
                objective = ShadowTrainingObjective(case["objective"])
                started = perf_counter()
                run = await ShadowAgentService(
                    V2FixtureTools(case["tool_results"]),
                    gateway,
                    default_model=settings.llm_default_model,
                ).recommend(
                    user_id=uuid4(), knowledge_base_id=uuid4(), objective=objective
                )
                latency_ms = round((perf_counter() - started) * 1000, 3)
                tool_steps = [step.tool_name.value for step in run.steps if step.tool_name]
                expected_primary = PRIMARY_TOOL_BY_OBJECTIVE[objective].value
                expected_second = case.get("expected_second_tool")
                primary_correct = bool(tool_steps and tool_steps[0] == expected_primary)
                second_correct = (
                    None
                    if expected_second is None
                    else len(tool_steps) > 1 and tool_steps[1] == expected_second
                )
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "round": round_index,
                        "objective": objective.value,
                        "status": run.status,
                        "primary_tool": tool_steps[0] if tool_steps else None,
                        "primary_tool_correct": primary_correct,
                        "second_tool": tool_steps[1] if len(tool_steps) > 1 else None,
                        "second_tool_correct": second_correct,
                        "action": run.recommendation.recommended_action.value,
                        "action_correct": run.recommendation.recommended_action.value
                        == case["expected_action"],
                        "requires_confirmation": run.recommendation.requires_confirmation,
                        "step_count": len(run.steps),
                        "business_writes": run.business_writes,
                        "latency_ms": latency_ms,
                    }
                )
    finally:
        await gateway.aclose()

    total = len(rows)
    second_rows = [row for row in rows if row["second_tool_correct"] is not None]
    stability: dict[str, set[tuple[object, object]]] = {}
    for row in rows:
        stability.setdefault(str(row["case_id"]), set()).add(
            (row["second_tool"], row["action"])
        )
    latencies = [float(cast(float, row["latency_ms"])) for row in rows]
    return {
        "dataset": str(path),
        "model": settings.llm_default_model,
        "metrics": {
            "case_count": len(stability),
            "rounds": rounds,
            "run_count": total,
            "schema_valid_rate": sum(row["status"] == "completed" for row in rows) / total,
            "primary_route_accuracy": sum(bool(row["primary_tool_correct"]) for row in rows)
            / total,
            "supplementary_tool_accuracy": (
                sum(bool(row["second_tool_correct"]) for row in second_rows) / len(second_rows)
                if second_rows
                else 1.0
            ),
            "recommendation_action_accuracy": sum(bool(row["action_correct"]) for row in rows)
            / total,
            "max_step_adherence": sum(
                cast(int, row["step_count"]) <= 3 for row in rows
            )
            / total,
            "confirmation_guard_rate": sum(bool(row["requires_confirmation"]) for row in rows)
            / total,
            "business_zero_write_rate": sum(row["business_writes"] == 0 for row in rows)
            / total,
            "decision_stability": sum(len(values) == 1 for values in stability.values())
            / len(stability),
            "latency_p50_ms": round(statistics.median(latencies), 3),
            "latency_p95_ms": round(percentile(latencies, 0.95), 3),
        },
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real-model Shadow Agent V2 Development.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.dataset, args.rounds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
