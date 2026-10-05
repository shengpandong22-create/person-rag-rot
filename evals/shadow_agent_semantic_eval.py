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
    ShadowToolArguments,
    ShadowToolName,
    ShadowTrainingObjective,
)
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway

DEFAULT_DATASET = Path("evals/datasets/shadow_agent_semantic_development_v1.jsonl")


@dataclass(slots=True)
class SemanticFixtureTools:
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
        raise RuntimeError("A real LLM must be configured for semantic evaluation.")
    gateway = OpenAICompatibleLLMGateway(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        default_model=settings.llm_default_model,
    )
    cases = load_cases(path)
    rows: list[dict[str, object]] = []
    try:
        for round_index in range(1, rounds + 1):
            for case in cases:
                started = perf_counter()
                run = await ShadowAgentService(
                    SemanticFixtureTools(case["tool_results"]),
                    gateway,
                    default_model=settings.llm_default_model,
                ).recommend(
                    user_id=uuid4(),
                    knowledge_base_id=uuid4(),
                    objective=ShadowTrainingObjective(case["objective"]),
                )
                latency_ms = round((perf_counter() - started) * 1000, 3)
                first_tool = next(
                    (
                        step.tool_name.value
                        for step in run.steps
                        if step.decision == "tool" and step.tool_name is not None
                    ),
                    None,
                )
                acceptable_tools = case.get(
                    "acceptable_first_tools", [case.get("expected_first_tool")]
                )
                acceptable_actions = case.get(
                    "acceptable_actions", [case.get("expected_action")]
                )
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "round": round_index,
                        "objective": case["objective"],
                        "status": run.status,
                        "first_tool": first_tool,
                        "tool_correct": first_tool in acceptable_tools,
                        "action": run.recommendation.recommended_action.value,
                        "action_correct": (
                            run.recommendation.recommended_action.value in acceptable_actions
                        ),
                        "requires_confirmation": run.recommendation.requires_confirmation,
                        "step_count": len(run.steps),
                        "business_writes": run.business_writes,
                        "termination_reason": run.termination_reason,
                        "latency_ms": latency_ms,
                    }
                )
    finally:
        await gateway.aclose()

    total = len(rows)
    action_sets: dict[str, set[tuple[object, object]]] = {}
    for row in rows:
        action_sets.setdefault(str(row["case_id"]), set()).add(
            (row["first_tool"], row["action"])
        )
    latencies = [float(cast(float, row["latency_ms"])) for row in rows]
    metrics = {
        "case_count": len(cases),
        "rounds": rounds,
        "run_count": total,
        "schema_valid_rate": sum(row["status"] == "completed" for row in rows) / total,
        "tool_selection_accuracy": sum(bool(row["tool_correct"]) for row in rows) / total,
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
        "decision_stability": sum(len(values) == 1 for values in action_sets.values())
        / len(action_sets),
        "latency_p50_ms": round(statistics.median(latencies), 3),
        "latency_p95_ms": round(percentile(latencies, 0.95), 3),
    }
    return {
        "dataset": str(path),
        "model": settings.llm_default_model,
        "metrics": metrics,
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real-model Shadow Agent Development.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.dataset, args.rounds))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
