from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from agent_mentor import __version__
from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.config import get_settings
from agent_mentor.domain.evaluation import total_score
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway
from evals.metrics import ScoringCaseResult, compute_scoring_metrics


@dataclass(frozen=True, slots=True)
class ScoringEvalCase:
    case_id: str
    topic: str
    question: str
    answer: str
    human_scores: dict[str, int]
    expected_review: bool
    expected_band: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringEvalReport:
    dataset: str
    metadata: dict[str, object]
    metrics: dict[str, object]
    cases: list[dict[str, object]]


async def run_scoring_eval(
    *,
    dataset_path: Path,
    output_dir: Path,
    use_llm: bool = False,
) -> ScoringEvalReport:
    cases = _load_cases(dataset_path)
    settings = get_settings()
    llm = None
    if use_llm and settings.llm_base_url and settings.llm_api_key and settings.llm_default_model:
        llm = OpenAICompatibleLLMGateway(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            default_model=settings.llm_default_model,
        )
    service = EvaluationService(
        sessions=None,  # type: ignore[arg-type]
        llm=llm,
        default_model=settings.llm_default_model if llm else None,
    )
    case_rows: list[dict[str, object]] = []
    metric_inputs: list[ScoringCaseResult] = []
    for case in cases:
        result = await service.evaluate_answer_direct(
            question_text=case.question,
            answer_text=case.answer,
            reference_answer=_reference_answer(case),
            knowledge_points=(case.topic, case.question),
            rubric=_rubric(case),
            allowed_reference_ids=(UUID("00000000-0000-0000-0000-000000000001"),),
            reviewer_available=True,
        )
        predicted_total = total_score(result.output)
        human_total = sum(case.human_scores.values())
        predicted_review = result.needs_review or result.status.value != "final"
        metric_inputs.append(
            ScoringCaseResult(
                case_id=case.case_id,
                predicted_total=predicted_total,
                human_total=human_total,
                predicted_review=predicted_review,
                expected_review=case.expected_review,
                expected_band=case.expected_band,
            )
        )
        case_rows.append(
            {
                "id": case.case_id,
                "topic": case.topic,
                "question": case.question,
                "human_total": human_total,
                "predicted_total": predicted_total,
                "absolute_error": abs(predicted_total - human_total),
                "human_scores": case.human_scores,
                "predicted_scores": {
                    "correctness": result.output.correctness,
                    "completeness": result.output.completeness,
                    "reasoning": result.output.reasoning,
                    "communication": result.output.communication,
                },
                "expected_review": case.expected_review,
                "predicted_review": predicted_review,
                "expected_band": case.expected_band,
                "confidence": result.output.confidence,
                "status": result.status.value,
                "review_decision": result.review_decision.value,
                "review_reasons": result.output.review_reasons,
                "feedback": result.output.feedback,
            }
        )

    report = ScoringEvalReport(
        dataset=str(dataset_path),
        metadata={
            "generated_at": datetime.now(UTC).isoformat(),
            "app_version": __version__,
            "dataset_sha256": _file_sha256(dataset_path),
            "use_llm": use_llm,
            "llm_enabled": llm is not None,
            "llm_model": settings.llm_default_model if llm else None,
        },
        metrics=asdict(compute_scoring_metrics(metric_inputs)),
        cases=case_rows,
    )
    _write_report(report, output_dir)
    return report


def _load_cases(path: Path) -> list[ScoringEvalCase]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    cases: list[ScoringEvalCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            try:
                cases.append(
                    ScoringEvalCase(
                        case_id=str(raw["id"]),
                        topic=str(raw["topic"]),
                        question=str(raw["question"]),
                        answer=str(raw["answer"]),
                        human_scores={
                            "correctness": int(raw["human_scores"]["correctness"]),
                            "completeness": int(raw["human_scores"]["completeness"]),
                            "reasoning": int(raw["human_scores"]["reasoning"]),
                            "communication": int(raw["human_scores"]["communication"]),
                        },
                        expected_review=bool(raw["expected_review"]),
                        expected_band=(
                            str(raw["expected_band"]) if raw.get("expected_band") else None
                        ),
                    )
                )
            except KeyError as error:
                raise ValueError(f"Invalid dataset row {line_number}: missing {error}") from error
    if not cases:
        raise ValueError(f"Dataset is empty: {path}")
    return cases


def _reference_answer(case: ScoringEvalCase) -> str:
    return f"{case.topic} 面试参考答案应覆盖题目要求，并说明关键概念、流程、风险和工程取舍。"


def _rubric(case: ScoringEvalCase) -> dict[str, object]:
    return {
        "max_score": 20,
        "items": [
            {
                "criterion": "正确性",
                "description": "回答是否符合题目和主题事实。",
                "weight": 25,
                "required_points": [case.topic],
            },
            {
                "criterion": "完整性",
                "description": "回答是否覆盖题目中的关键要求。",
                "weight": 25,
                "required_points": [case.question],
            },
            {
                "criterion": "推理",
                "description": "回答是否解释原因、流程或取舍。",
                "weight": 25,
                "required_points": ["原因", "流程", "取舍"],
            },
            {
                "criterion": "表达",
                "description": "回答是否结构清晰。",
                "weight": 25,
                "required_points": ["结构清晰"],
            },
        ],
    }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_report(report: ScoringEvalReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "scoring_eval.json"
    markdown_path = output_dir / "scoring_eval.md"
    json_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metrics = report.metrics
    lines = [
        "# Scoring Eval Report",
        "",
        f"- dataset: `{report.dataset}`",
        f"- generated_at: {report.metadata['generated_at']}",
        f"- app_version: {report.metadata['app_version']}",
        f"- dataset_sha256: `{report.metadata['dataset_sha256']}`",
        f"- use_llm: {report.metadata['use_llm']}",
        f"- llm_enabled: {report.metadata['llm_enabled']}",
        f"- llm_model: {report.metadata['llm_model']}",
        f"- total: {metrics['total']}",
        f"- MAE: {metrics['mean_absolute_error']}",
        f"- Pearson correlation: {metrics['pearson_correlation']}",
        f"- Reviewer routing accuracy: {metrics['reviewer_routing_accuracy']}",
        f"- Band order accuracy: {metrics['band_order_accuracy']}",
        f"- Predicted average by band: {metrics['predicted_average_by_band']}",
        f"- Human average by band: {metrics['human_average_by_band']}",
        "",
    ]
    high_error_cases = [
        row for row in report.cases if _integer_value(row, "absolute_error") >= 6
    ]
    review_mismatches = [
        row
        for row in report.cases
        if bool(row["expected_review"]) != bool(row["predicted_review"])
    ]
    if high_error_cases:
        lines.extend(["## High Error Cases", ""])
        for row in high_error_cases:
            lines.extend(
                [
                    f"### {row['id']}",
                    "",
                    f"- topic: {row['topic']}",
                    f"- expected_band: {row['expected_band']}",
                    f"- human_total: {row['human_total']}",
                    f"- predicted_total: {row['predicted_total']}",
                    f"- absolute_error: {row['absolute_error']}",
                    f"- status: {row['status']}",
                    "",
                ]
            )
    if review_mismatches:
        lines.extend(["## Review Routing Mismatches", ""])
        for row in review_mismatches:
            lines.extend(
                [
                    f"### {row['id']}",
                    "",
                    f"- expected_review: {row['expected_review']}",
                    f"- predicted_review: {row['predicted_review']}",
                    f"- confidence: {row['confidence']}",
                    f"- review_reasons: {row['review_reasons']}",
                    "",
                ]
            )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def _integer_value(row: dict[str, object], key: str) -> int:
    value = row[key]
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"{key} must be numeric, got {type(value).__name__}")
