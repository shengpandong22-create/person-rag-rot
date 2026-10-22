"""Five-run, one-case scoring repeatability observation.

The result is intentionally narrower than a scoring-accuracy evaluation: it
measures whether the same configured model returns the same score shape for a
fixed answer.  It does not measure agreement with a human reviewer.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.config import get_settings
from agent_mentor.domain.evaluation import total_score
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway
from evals.provenance import collect_git_state
from evals.runners.scoring_runner import ScoringEvalCase, _reference_answer, _rubric


def compute_stability_metrics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) < 2:
        raise ValueError("stability observation requires at least two runs")
    totals = [int(row["total"]) for row in runs]
    dimensions = ("correctness", "completeness", "reasoning", "communication")
    dimension_metrics: dict[str, dict[str, object]] = {}
    for dimension in dimensions:
        values = [int(row[dimension]) for row in runs]
        dimension_metrics[dimension] = _numeric_summary(values)
    score_shapes = [tuple(row[name] for name in (*dimensions, "total")) for row in runs]
    routing_shapes = [
        (row["needs_review"], row["status"], row["review_decision"]) for row in runs
    ]
    return {
        "run_count": len(runs),
        "total_score": _numeric_summary(totals),
        "dimensions": dimension_metrics,
        "exact_score_shape_stable": len(set(score_shapes)) == 1,
        "unique_score_shape_count": len(set(score_shapes)),
        "review_routing_stable": len(set(routing_shapes)) == 1,
        "unique_review_routing_count": len(set(routing_shapes)),
    }


def _numeric_summary(values: list[int]) -> dict[str, object]:
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.fmean(values), 4),
        "population_stddev": round(statistics.pstdev(values), 4),
    }


async def run_scoring_stability(
    *, dataset_path: Path, case_id: str, output_dir: Path, runs: int = 5
) -> dict[str, object]:
    if runs != 5:
        raise ValueError("this protocol is fixed at exactly five runs")
    case = _load_case(dataset_path, case_id)
    settings = get_settings()
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_default_model):
        raise RuntimeError("real LLM configuration is required for scoring stability")
    llm = OpenAICompatibleLLMGateway(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        default_model=settings.llm_default_model,
    )
    service = EvaluationService(
        sessions=None,  # type: ignore[arg-type]
        llm=llm,
        default_model=settings.llm_default_model,
    )
    rows: list[dict[str, Any]] = []
    try:
        for index in range(1, runs + 1):
            started = time.perf_counter()
            result = await service.evaluate_answer_direct(
                question_text=case.question,
                answer_text=case.answer,
                reference_answer=_reference_answer(case),
                knowledge_points=(case.topic, case.question),
                rubric=_rubric(case),
                allowed_reference_ids=(UUID("00000000-0000-0000-0000-000000000001"),),
                reviewer_available=False,
            )
            rows.append(
                {
                    "run": index,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "correctness": result.output.correctness,
                    "completeness": result.output.completeness,
                    "reasoning": result.output.reasoning,
                    "communication": result.output.communication,
                    "total": total_score(result.output),
                    "confidence": result.output.confidence,
                    "needs_review": result.needs_review,
                    "status": result.status.value,
                    "review_decision": result.review_decision.value,
                    "model_name": result.model_name,
                }
            )
    finally:
        await llm.aclose()
    report: dict[str, Any] = {
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            **collect_git_state().to_json(),
            "dataset": str(dataset_path),
            "dataset_sha256": _file_sha256(dataset_path),
            "case_id": case.case_id,
            "llm_model": settings.llm_default_model,
            "run_count": runs,
            "reviewer_available": False,
            "scope": "single fixed-answer repeatability observation, not human agreement",
        },
        "runs": rows,
        "metrics": compute_stability_metrics(rows),
    }
    write_scoring_stability_report(report, output_dir)
    return report


def _load_case(dataset_path: Path, case_id: str) -> ScoringEvalCase:
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("id") == case_id:
            return ScoringEvalCase(
                case_id=str(row["id"]),
                topic=str(row["topic"]),
                question=str(row["question"]),
                answer=str(row["answer"]),
                human_scores={key: int(value) for key, value in row["human_scores"].items()},
                expected_review=bool(row["expected_review"]),
                expected_band=str(row["expected_band"]) if row.get("expected_band") else None,
            )
    raise ValueError(f"case_id not found: {case_id}")


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_scoring_stability_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scoring_stability.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = report["metadata"]
    metrics = report["metrics"]
    runs = report["runs"]
    assert isinstance(metadata, dict)
    assert isinstance(metrics, dict)
    assert isinstance(runs, list)
    total = metrics["total_score"]
    assert isinstance(total, dict)
    lines = [
        "# Scoring Stability Observation",
        "",
        "## Scope and boundary",
        "",
        "The same fixed answer was evaluated five times with a fixed configured model. "
        "The reviewer step was disabled to isolate the primary evaluator.",
        "This is a small-sample repeatability observation, not a human adjudication study, "
        "accuracy result, or reviewer override rate.",
        "",
        "## Reproducibility",
        "",
        f"- dataset: `{metadata['dataset']}`",
        f"- dataset_sha256: `{metadata['dataset_sha256']}`",
        f"- case_id: `{metadata['case_id']}`",
        f"- llm_model: `{metadata['llm_model']}`",
        f"- git_commit: `{metadata['git_commit']}`",
        "",
        "## Result",
        "",
        f"- total-score range: `{total['min']}–{total['max']}`",
        f"- total-score population standard deviation: `{total['population_stddev']}`",
        f"- exact score shape stable: `{metrics['exact_score_shape_stable']}`",
        f"- review routing stable: `{metrics['review_routing_stable']}`",
        "",
        "| run | total | correctness | completeness | reasoning | communication | "
        "confidence | elapsed ms |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in runs:
        assert isinstance(row, dict)
        lines.append(
            "| {run} | {total} | {correctness} | {completeness} | {reasoning} | "
            "{communication} | {confidence} | {elapsed_ms} |".format(**row)
        )
    (output_dir / "scoring_stability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
