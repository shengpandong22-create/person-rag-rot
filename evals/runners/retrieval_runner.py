from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

from agent_mentor.application.answer_service import AnswerService
from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.retriever import PostgresHybridRetriever
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from evals.metrics import RetrievalCaseResult, compute_retrieval_metrics
from evals.runners.runtime import create_embedding_gateway


@dataclass(frozen=True, slots=True)
class RetrievalEvalCase:
    case_id: str
    question: str
    expected_keywords: tuple[str, ...]
    answerable: bool


@dataclass(frozen=True, slots=True)
class RetrievalEvalReport:
    dataset: str
    knowledge_base_id: str
    metrics: dict[str, object]
    cases: list[dict[str, object]]


async def run_retrieval_eval(
    *,
    dataset_path: Path,
    knowledge_base_id: UUID,
    output_dir: Path,
    top_k: int = 6,
    candidate_k: int = 20,
    min_evidence_score: float | None = None,
) -> RetrievalEvalReport:
    cases = _load_cases(dataset_path)
    settings = get_settings()
    threshold = (
        min_evidence_score if min_evidence_score is not None else settings.retrieval_min_score
    )
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    embedding = create_embedding_gateway(settings)
    retriever = PostgresHybridRetriever(
        sessions,
        embedding,
        max_chunks_per_document=settings.retrieval_max_chunks_per_document,
    )
    answer_service = AnswerService(
        sessions,
        retriever,
        default_top_k=top_k,
        default_candidate_k=candidate_k,
        min_evidence_score=threshold,
        default_model=settings.llm_default_model,
    )
    case_rows: list[dict[str, object]] = []
    metric_inputs: list[RetrievalCaseResult] = []
    try:
        for case in cases:
            chunks = await retriever.retrieve(
                RetrievalQuery(
                    knowledge_base_id=knowledge_base_id,
                    query=case.question,
                    top_k=top_k,
                    candidate_k=candidate_k,
                )
            )
            first_rank = _first_relevant_rank(chunks, case.expected_keywords)
            supported_chunks, evidence_sufficient = answer_service.assess_evidence(
                case.question, chunks
            )
            metric_inputs.append(
                RetrievalCaseResult(
                    case_id=case.case_id,
                    answerable=case.answerable,
                    first_relevant_rank=first_rank,
                    evidence_sufficient=evidence_sufficient,
                )
            )
            case_rows.append(
                {
                    "id": case.case_id,
                    "question": case.question,
                    "answerable": case.answerable,
                    "expected_keywords": list(case.expected_keywords),
                    "first_relevant_rank": first_rank,
                    "evidence_sufficient": evidence_sufficient,
                    "supported_chunk_count": len(supported_chunks),
                    "top_chunks": [
                        {
                            "rank": index,
                            "chunk_id": str(chunk.chunk_id),
                            "document_title": chunk.document_title,
                            "score": chunk.score,
                            "matched_keywords": _matched_keywords(
                                chunk, case.expected_keywords
                            ),
                        }
                        for index, chunk in enumerate(chunks[:top_k], start=1)
                    ],
                }
            )
    finally:
        await engine.dispose()

    metrics = compute_retrieval_metrics(metric_inputs)
    report = RetrievalEvalReport(
        dataset=str(dataset_path),
        knowledge_base_id=str(knowledge_base_id),
        metrics=asdict(metrics),
        cases=case_rows,
    )
    _write_report(report, output_dir)
    return report


def _load_cases(path: Path) -> list[RetrievalEvalCase]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    cases: list[RetrievalEvalCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            try:
                cases.append(
                    RetrievalEvalCase(
                        case_id=str(raw["id"]),
                        question=str(raw["question"]),
                        expected_keywords=tuple(str(item) for item in raw["expected_keywords"]),
                        answerable=bool(raw["answerable"]),
                    )
                )
            except KeyError as error:
                raise ValueError(f"Invalid dataset row {line_number}: missing {error}") from error
    if not cases:
        raise ValueError(f"Dataset is empty: {path}")
    return cases


def _first_relevant_rank(chunks: list[RetrievedChunk], keywords: tuple[str, ...]) -> int | None:
    for rank, chunk in enumerate(chunks, start=1):
        if _matched_keywords(chunk, keywords):
            return rank
    return None


def _matched_keywords(chunk: RetrievedChunk, keywords: tuple[str, ...]) -> list[str]:
    haystack = " ".join(
        [
            chunk.document_title,
            " ".join(chunk.heading_path),
            chunk.content,
        ]
    ).casefold()
    return [keyword for keyword in keywords if keyword.casefold() in haystack]


def _write_report(report: RetrievalEvalReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "retrieval_eval"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metrics = report.metrics
    lines = [
        "# Retrieval Eval Report",
        "",
        f"- dataset: `{report.dataset}`",
        f"- knowledge_base_id: `{report.knowledge_base_id}`",
        f"- total: {metrics['total']}",
        f"- Recall@1: {metrics['recall_at_1']}",
        f"- Recall@3: {metrics['recall_at_3']}",
        f"- Recall@6: {metrics['recall_at_6']}",
        f"- MRR: {metrics['mrr']}",
        f"- Evidence sufficient accuracy: {metrics['evidence_sufficient_accuracy']}",
        f"- Negative rejection accuracy: {metrics['negative_rejection_accuracy']}",
        "",
    ]
    failed_cases = [
        row
        for row in report.cases
        if bool(row["answerable"]) != bool(row["evidence_sufficient"])
    ]
    if failed_cases:
        lines.extend(["## Evidence Gate Failures", ""])
        for row in failed_cases:
            top_chunks = row.get("top_chunks", [])
            first_chunk = top_chunks[0] if isinstance(top_chunks, list) and top_chunks else {}
            lines.extend(
                [
                    f"### {row['id']}",
                    "",
                    f"- question: {row['question']}",
                    f"- answerable: {row['answerable']}",
                    f"- evidence_sufficient: {row['evidence_sufficient']}",
                    f"- supported_chunk_count: {row.get('supported_chunk_count', 0)}",
                    f"- top_document: {first_chunk.get('document_title', '-')}",
                    f"- top_score: {first_chunk.get('score', '-')}",
                    "",
                ]
            )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
