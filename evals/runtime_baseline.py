"""Pure report helpers for the single-request runtime baseline.

This module deliberately contains no application startup or HTTP code.  The
runner supplies measurements from an explicitly selected AgentMentor instance;
keeping aggregation pure makes the reporting contract independently testable.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeMeasurement:
    mode: str
    phase: str
    case_id: str
    iteration: int
    elapsed_ms: float
    success: bool
    status_code: int | None
    generation_mode: str | None = None
    fallback_reason: str | None = None
    error: str | None = None


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must be between 0 and 1")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return round(ordered[index], 3)


def summarize_measurements(measurements: list[RuntimeMeasurement]) -> dict[str, object]:
    if not measurements:
        raise ValueError("at least one runtime measurement is required")
    successful = [item.elapsed_ms for item in measurements if item.success]
    failed = len(measurements) - len(successful)
    return {
        "sample_count": len(measurements),
        "success_count": len(successful),
        "failure_count": failed,
        "failure_rate": round(failed / len(measurements), 4),
        "latency_p50_ms": percentile(successful, 0.50),
        "latency_p95_ms": percentile(successful, 0.95),
    }


def build_runtime_report(
    *,
    metadata: dict[str, object],
    measurements: list[RuntimeMeasurement],
) -> dict[str, Any]:
    grouped: dict[str, list[RuntimeMeasurement]] = {}
    generated: dict[str, list[RuntimeMeasurement]] = {}
    for item in measurements:
        grouped.setdefault(f"{item.mode}:{item.phase}", []).append(item)
        if item.phase == "end_to_end" and item.generation_mode is not None:
            generated.setdefault(f"{item.mode}:end_to_end:{item.generation_mode}", []).append(item)
    return {
        "metadata": metadata,
        "metrics": {name: summarize_measurements(rows) for name, rows in sorted(grouped.items())},
        "answer_outcome_metrics": {
            name: summarize_measurements(rows) for name, rows in sorted(generated.items())
        },
        "measurements": [asdict(item) for item in measurements],
    }


def write_runtime_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "runtime_baseline.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = report["metadata"]
    metrics = report["metrics"]
    answer_outcome_metrics = report["answer_outcome_metrics"]
    assert isinstance(metadata, dict)
    assert isinstance(metrics, dict)
    assert isinstance(answer_outcome_metrics, dict)
    lines = [
        "# Minimal Runtime Baseline",
        "",
        "## Scope",
        "",
        "This is a sequential single-request observation, not a concurrency load test "
        "or QPS claim.",
        "The `/ask` endpoint persists chat records, so this run is restricted to a dedicated "
        "benchmark knowledge base.",
        "",
        "## Reproducibility",
        "",
    ]
    for key in (
        "generated_at",
        "git_commit",
        "git_branch",
        "dataset",
        "dataset_sha256",
        "knowledge_base_id",
        "repetitions",
        "warmups",
    ):
        lines.append(f"- {key}: `{metadata.get(key)}`")
    runtime_modes = metadata.get("runtime_modes")
    lines.extend([f"- runtime_modes: `{runtime_modes}`", "", "## Results", ""])
    lines.extend(
        [
            "| mode / phase | samples | failures | failure rate | P50 ms | P95 ms |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, row in metrics.items():
        assert isinstance(row, dict)
        lines.append(
            "| {name} | {sample_count} | {failure_count} | {failure_rate:.2%} | "
            "{latency_p50_ms} | {latency_p95_ms} |".format(name=name, **row)
        )
    lines.extend(
        [
            "",
            "## End-to-end outcome breakdown",
            "",
            "This table separates Evidence Gate responses from actual LLM generation. "
            "Only the `llm` generation row represents an external model call.",
            "",
            "| mode / generation mode | samples | failures | failure rate | P50 ms | P95 ms |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, row in answer_outcome_metrics.items():
        assert isinstance(row, dict)
        lines.append(
            "| {name} | {sample_count} | {failure_count} | {failure_rate:.2%} | "
            "{latency_p50_ms} | {latency_p95_ms} |".format(name=name, **row)
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "P50/P95 describe only these sequential samples on the recorded machine and runtime. "
            "They do not establish throughput, concurrent capacity, or a production SLO.",
            "",
        ]
    )
    (output_dir / "runtime_baseline.md").write_text("\n".join(lines), encoding="utf-8")
