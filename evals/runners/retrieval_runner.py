from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select

from agent_mentor import __version__
from agent_mentor.application.answer_service import AnswerService
from agent_mentor.config import get_settings
from agent_mentor.domain.knowledge import DocumentStatus
from agent_mentor.infrastructure.database.models import (
    KnowledgeBaseModel,
    KnowledgeCatalogPointModel,
    KnowledgeChunkModel,
    SourceDocumentModel,
)
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.retriever import (
    PostgresHybridRetriever,
    RetrievalExperimentMode,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from evals.metrics import RetrievalCaseResult, compute_retrieval_metrics
from evals.provenance import build_provenance
from evals.runners.runtime import create_embedding_gateway
from evals.schema import (
    Answerability,
    LabelOrigin,
    RetrievalEvalCase,
    load_dataset,
)

GROUND_TRUTH_RESOLVED = "resolved"
GROUND_TRUTH_KEYWORD_FALLBACK = "keyword_fallback"
GROUND_TRUTH_ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class RetrievalEvalReport:
    dataset: str
    knowledge_base_id: str
    metadata: dict[str, object]
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
    experiment_mode: RetrievalExperimentMode = RetrievalExperimentMode.RRF_HEURISTIC,
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
    grading_counts = {"graded": 0, "ungraded": 0}
    ground_truth_counts: dict[str, int] = {}
    total_retrieval_ms = 0.0
    try:
        knowledge_base_fingerprint = await _knowledge_base_fingerprint(sessions, knowledge_base_id)
        all_keywords = sorted({keyword for case in cases for keyword in case.diagnostic_keywords})
        keyword_coverage = await _expected_keyword_coverage(
            sessions, knowledge_base_id, all_keywords
        )
        for case in cases:
            started = perf_counter()
            chunks = await retriever.retrieve(
                RetrievalQuery(
                    knowledge_base_id=knowledge_base_id,
                    query=case.question,
                    top_k=top_k,
                    candidate_k=candidate_k,
                ),
                experiment_mode=experiment_mode,
            )
            latency_ms = (perf_counter() - started) * 1000
            total_retrieval_ms += latency_ms
            ground_truth, ground_truth_mode = await _resolve_ground_truth(
                sessions,
                knowledge_base_id=knowledge_base_id,
                case=case,
            )
            graded = _is_graded(case)
            grading_counts["graded" if graded else "ungraded"] += 1
            ground_truth_counts[ground_truth_mode] = (
                ground_truth_counts.get(ground_truth_mode, 0) + 1
            )
            # Graded rows are ranked against resolved chunk ids; ungraded rows
            # fall back to keyword matching purely as a diagnostic, and are
            # excluded from formal Recall/MRR below.
            if ground_truth:
                first_rank = _first_relevant_rank_by_id(chunks, ground_truth)
            else:
                first_rank = _first_relevant_rank(chunks, case.diagnostic_keywords)
            supported_chunks, evidence_sufficient = answer_service.assess_evidence(
                case.question, chunks
            )
            formally_scorable = graded and (
                case.answerability is Answerability.NONE
                or ground_truth_mode == GROUND_TRUTH_RESOLVED
            )
            if formally_scorable:
                metric_inputs.append(
                    RetrievalCaseResult(
                        case_id=case.case_id,
                        answerable=case.answerable,
                        first_relevant_rank=first_rank,
                        evidence_sufficient=evidence_sufficient,
                        answerability=case.answerability.value,
                        negative_reason=(
                            case.negative_reason.value if case.negative_reason else None
                        ),
                        latency_ms=latency_ms,
                        candidate_count=len(chunks),
                    )
                )
            failure_category = _failure_category(
                case=case,
                ground_truth_mode=ground_truth_mode,
                first_rank=first_rank,
                evidence_sufficient=evidence_sufficient,
                top_k=top_k,
            )
            case_rows.append(
                {
                    "id": case.case_id,
                    "question": case.question,
                    "answerability": case.answerability.value,
                    "answerable": case.answerable,
                    "graded": graded,
                    "label_origin": case.label_origin.value,
                    "ground_truth_mode": ground_truth_mode,
                    "ground_truth_chunk_count": len(ground_truth),
                    "negative_reason": (
                        case.negative_reason.value if case.negative_reason else None
                    ),
                    "tags": list(case.tags),
                    "diagnostic_keywords": list(case.diagnostic_keywords),
                    "expected_keyword_coverage": {
                        keyword: keyword_coverage.get(keyword, 0)
                        for keyword in case.diagnostic_keywords
                    },
                    "first_relevant_rank": first_rank,
                    "experiment_mode": experiment_mode.value,
                    "latency_ms": round(latency_ms, 4),
                    "retrieved_candidate_count": len(chunks),
                    "evidence_sufficient": evidence_sufficient,
                    "evidence_decision": "accept" if evidence_sufficient else "reject",
                    "failure_category": failure_category,
                    "supported_chunk_count": len(supported_chunks),
                    "top_chunks": [
                        {
                            "rank": index,
                            "chunk_id": str(chunk.chunk_id),
                            "document_title": chunk.document_title,
                            "document_logical_name": chunk.document_logical_name,
                            "heading_path": list(chunk.heading_path),
                            "score": chunk.score,
                            "vector_rank": chunk.vector_rank,
                            "vector_score": chunk.vector_score,
                            "text_rank": chunk.text_rank,
                            "text_score": chunk.text_score,
                            "rrf_score": chunk.rrf_score,
                            "heuristic_rerank_score": chunk.heuristic_rerank_score,
                            "matched_keywords": _matched_keywords(chunk, case.diagnostic_keywords),
                            "matched_ground_truth": chunk.chunk_id in set(ground_truth),
                        }
                        for index, chunk in enumerate(chunks[:top_k], start=1)
                    ],
                }
            )
    finally:
        await engine.dispose()

    if not metric_inputs:
        raise ValueError(
            f"{dataset_path} contains no graded rows. Formal Recall/MRR requires human "
            "labels; run with a dataset whose positive rows carry relevant_sources."
        )
    metrics = compute_retrieval_metrics(metric_inputs)
    provenance = build_provenance(dataset_path=dataset_path)
    report = RetrievalEvalReport(
        dataset=str(dataset_path),
        knowledge_base_id=str(knowledge_base_id),
        metadata={
            "generated_at": datetime.now(UTC).isoformat(),
            "app_version": __version__,
            **provenance,
            "embedding_provider": settings.embedding_provider.value,
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "experiment_mode": experiment_mode.value,
            "retrieval_top_k": top_k,
            "retrieval_candidate_k": candidate_k,
            "retrieval_min_score": threshold,
            "rrf_k": 60,
            "heuristic_weights": {
                "vector": 0.003,
                "text": 0.004,
                "lexical": 0.006,
            },
            "freeze_manifest_sha256": _freeze_manifest_sha256(dataset_path),
            "run_duration_ms": round(total_retrieval_ms, 4),
            "retrieval_max_chunks_per_document": settings.retrieval_max_chunks_per_document,
            "knowledge_base": knowledge_base_fingerprint,
            "grading_counts": grading_counts,
            "ground_truth_counts": ground_truth_counts,
            "metrics_scope": "graded_rows_only",
        },
        metrics=asdict(metrics),
        cases=case_rows,
    )
    _write_report(report, output_dir)
    return report


def _freeze_manifest_sha256(dataset_path: Path) -> str | None:
    name = dataset_path.name.lower()
    if "validation" in name:
        manifest = dataset_path.with_name("VALIDATION_FREEZE.json")
    elif "holdout" in name:
        manifest = dataset_path.with_name("HOLDOUT_FREEZE.json")
    else:
        return None
    return _file_sha256(manifest) if manifest.exists() else None


def _failure_category(
    *,
    case: RetrievalEvalCase,
    ground_truth_mode: str,
    first_rank: int | None,
    evidence_sufficient: bool,
    top_k: int,
) -> str | None:
    if case.answerability is not Answerability.NONE and ground_truth_mode != GROUND_TRUTH_RESOLVED:
        return "source_label_unresolved"
    if case.answerability is Answerability.NONE:
        return "false_acceptance" if evidence_sufficient else "correct_rejection"
    if first_rank is None:
        return "retrieval_miss"
    if first_rank > top_k:
        return "ranking_miss"
    if not evidence_sufficient:
        return "evidence_gate_rejection"
    if case.answerability is Answerability.PARTIAL:
        return "partial_answer_boundary"
    return None


def _is_graded(case: RetrievalEvalCase) -> bool:
    """Whether this row may be scored as formal Recall/MRR.

    A negative row's label *is* its ``negative_reason`` — a human judgement —
    so it counts as graded even without ``relevant_sources``.
    """
    if case.label_origin is not LabelOrigin.HUMAN:
        return False
    if case.answerability is Answerability.NONE:
        return case.negative_reason is not None
    return bool(case.relevant_sources)


async def _resolve_ground_truth(
    sessions: Any,
    *,
    knowledge_base_id: UUID,
    case: RetrievalEvalCase,
) -> tuple[tuple[UUID, ...], str]:
    """Map stable document/heading labels onto the chunk ids of the live KB.

    Resolution happens at run time on purpose: chunk ids change whenever the
    knowledge base is re-chunked or re-embedded, so storing ids in the dataset
    would silently invalidate every label after a rebuild.
    """
    if not case.relevant_sources:
        return (), GROUND_TRUTH_ABSENT
    matched: set[UUID] = set()
    unresolved: list[str] = []
    async with sessions() as session:
        for source in case.relevant_sources:
            rows = (
                await session.execute(
                    select(KnowledgeChunkModel, SourceDocumentModel)
                    .join(
                        SourceDocumentModel,
                        SourceDocumentModel.id == KnowledgeChunkModel.document_id,
                    )
                    .where(
                        SourceDocumentModel.knowledge_base_id == knowledge_base_id,
                        SourceDocumentModel.logical_name == source.document_logical_name,
                        SourceDocumentModel.is_active.is_(True),
                        KnowledgeChunkModel.is_active.is_(True),
                    )
                )
            ).all()
            if not rows:
                unresolved.append(source.document_logical_name)
                continue
            for chunk, document in rows:
                if _source_heading_matches(
                    source.heading_path,
                    tuple(chunk.heading_path),
                    document.title,
                ):
                    matched.add(chunk.id)
    if unresolved and not matched:
        return (), GROUND_TRUTH_KEYWORD_FALLBACK
    if not matched:
        return (), GROUND_TRUTH_ABSENT
    return tuple(sorted(matched, key=str)), GROUND_TRUTH_RESOLVED


def _heading_matches(expected: tuple[str, ...], actual: tuple[str, ...]) -> bool:
    """Match an expected heading path against a chunk's path.

    An empty expectation matches any chunk in the document.  Otherwise the
    expectation must appear as a contiguous subsequence so that adding an outer
    chapter to a document does not break the label.
    """
    if not expected:
        return True
    if len(expected) > len(actual):
        return False
    for start in range(len(actual) - len(expected) + 1):
        if all(
            expected[index].strip() == actual[start + index].strip()
            for index in range(len(expected))
        ):
            return True
    return False


def _source_heading_matches(
    expected: tuple[str, ...], actual: tuple[str, ...], document_title: str
) -> bool:
    """Resolve both canonical heading-only and parser full-path labels."""
    if _heading_matches(expected, actual):
        return True
    if expected and expected[0].strip() == document_title.strip():
        return _heading_matches(expected[1:], actual)
    return False


def _load_cases(path: Path) -> tuple[RetrievalEvalCase, ...]:
    """Load a v2 dataset in migration mode.

    Ungraded rows are tolerated so a partially labelled regression set can
    still run, but they are excluded from formal metrics by :func:`_is_graded`.
    """
    return load_dataset(path, require_graded=False).cases


def _first_relevant_rank_by_id(
    chunks: list[RetrievedChunk], ground_truth: tuple[UUID, ...]
) -> int | None:
    """Rank of the first retrieved chunk that a human marked as relevant.

    This is the only ranking signal used for formal Recall/MRR: it compares
    retrieved ids against resolved human labels, not against keyword strings.
    """
    allowed = set(ground_truth)
    for rank, chunk in enumerate(chunks, start=1):
        if chunk.chunk_id in allowed:
            return rank
    return None


def _first_relevant_rank(chunks: list[RetrievedChunk], keywords: tuple[str, ...]) -> int | None:
    """Diagnostic-only keyword rank, used for rows without human labels."""
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


async def _knowledge_base_fingerprint(sessions: Any, knowledge_base_id: UUID) -> dict[str, object]:
    async with sessions() as session:
        knowledge_base = await session.get(KnowledgeBaseModel, knowledge_base_id)
        if knowledge_base is None:
            return {"id": str(knowledge_base_id), "exists": False}

        documents = (
            (
                await session.execute(
                    select(SourceDocumentModel)
                    .where(SourceDocumentModel.knowledge_base_id == knowledge_base_id)
                    .order_by(SourceDocumentModel.logical_name, SourceDocumentModel.version)
                )
            )
            .scalars()
            .all()
        )
        chunk_count = await session.scalar(
            select(func.count(KnowledgeChunkModel.id))
            .join(SourceDocumentModel, KnowledgeChunkModel.document_id == SourceDocumentModel.id)
            .where(SourceDocumentModel.knowledge_base_id == knowledge_base_id)
        )
        catalog_point_count = await session.scalar(
            select(func.count(KnowledgeCatalogPointModel.id)).where(
                KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id
            )
        )
        document_hash_digest = sha256()
        for document in documents:
            document_hash_digest.update(document.content_hash.encode("utf-8"))
        return {
            "id": str(knowledge_base.id),
            "exists": True,
            "name": knowledge_base.name,
            "document_count": len(documents),
            "active_document_count": sum(1 for document in documents if document.is_active),
            "ready_document_count": sum(
                1 for document in documents if document.status == DocumentStatus.READY
            ),
            "chunk_count": int(chunk_count or 0),
            "catalog_point_count": int(catalog_point_count or 0),
            "document_hash_sha256": document_hash_digest.hexdigest(),
            "documents": [
                {
                    "title": document.title,
                    "logical_name": document.logical_name,
                    "version": document.version,
                    "status": _status_value(document.status),
                    "is_active": document.is_active,
                    "content_hash": document.content_hash,
                }
                for document in documents
            ],
        }


async def _expected_keyword_coverage(
    sessions: Any, knowledge_base_id: UUID, keywords: list[str]
) -> dict[str, int]:
    coverage: dict[str, int] = {}
    async with sessions() as session:
        for keyword in keywords:
            if not keyword:
                coverage[keyword] = 0
                continue
            like_pattern = f"%{keyword}%"
            count = await session.scalar(
                select(func.count(KnowledgeChunkModel.id))
                .join(
                    SourceDocumentModel,
                    KnowledgeChunkModel.document_id == SourceDocumentModel.id,
                )
                .where(
                    SourceDocumentModel.knowledge_base_id == knowledge_base_id,
                    or_(
                        KnowledgeChunkModel.content.ilike(like_pattern),
                        SourceDocumentModel.title.ilike(like_pattern),
                    ),
                )
            )
            coverage[keyword] = int(count or 0)
    return coverage


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _status_value(status: object) -> str:
    if isinstance(status, DocumentStatus):
        return status.value
    return str(status)


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
    metadata = report.metadata
    grading = _as_dict(metadata.get("grading_counts"))
    ground_truth = _as_dict(metadata.get("ground_truth_counts"))
    lines = [
        "# Retrieval Eval Report",
        "",
        "## Reproducibility",
        "",
        f"- git_commit: `{metadata.get('git_commit', 'unknown')}`"
        f" (dirty={metadata.get('git_dirty', 'unknown')})",
        f"- git_branch: `{metadata.get('git_branch', 'unknown')}`",
        f"- dataset: `{report.dataset}`",
        f"- dataset_sha256: `{metadata.get('dataset_sha256', 'unknown')}`",
        f"- freeze_manifest_sha256: `{metadata.get('freeze_manifest_sha256', 'n/a')}`",
        f"- app_version: {metadata['app_version']}",
        f"- generated_at: {metadata['generated_at']}",
        f"- run_duration_ms: {metadata.get('run_duration_ms', 'n/a')}",
        f"- holdout_intact: {metadata.get('holdout_intact', 'n/a')}",
        f"- holdout_detail: {metadata.get('holdout_detail', 'n/a')}",
        "",
        "## Scope",
        "",
        f"- metrics_scope: {metadata.get('metrics_scope', 'unknown')}",
        f"- graded_rows: {grading.get('graded', 'n/a')}",
        f"- ungraded_rows: {grading.get('ungraded', 'n/a')}",
        f"- ground_truth_resolution: {ground_truth}",
        "- ungraded 行仅作诊断，不进入下方 Recall/MRR。"
        "ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，"
        "该行结论不可信，需先修标注。",
        "",
        "## Configuration",
        "",
        f"- embedding: {metadata['embedding_provider']} / {metadata['embedding_model']}",
        f"- embedding_dimension: {metadata['embedding_dimension']}",
        f"- experiment_mode: {metadata['experiment_mode']}",
        "- retrieval: "
        f"top_k={metadata['retrieval_top_k']}, "
        f"candidate_k={metadata['retrieval_candidate_k']}, "
        f"min_score={metadata['retrieval_min_score']}",
        f"- rrf_k: {metadata['rrf_k']}",
        f"- heuristic_weights: {metadata['heuristic_weights']}",
        f"- knowledge_base: {_knowledge_base_summary(metadata['knowledge_base'])}",
        "",
        "## Metrics (graded rows only)",
        "",
        f"- total: {metrics['total']}",
        f"- Recall@1: {metrics['recall_at_1']}",
        f"- Recall@3: {metrics['recall_at_3']}",
        f"- Recall@6: {metrics['recall_at_6']}",
        f"- MRR: {metrics['mrr']}",
        f"- Full answerability accuracy: {metrics['full_answerability_accuracy']}",
        f"- Partial answerability accuracy: {metrics['partial_answerability_accuracy']}",
        f"- Evidence sufficient accuracy: {metrics['evidence_sufficient_accuracy']}",
        f"- Negative rejection accuracy: {metrics['negative_rejection_accuracy']}",
        f"- Rejection by negative reason: {metrics['rejection_by_negative_reason']}",
        f"- Retrieval latency P50/P95 ms: {metrics['latency_p50_ms']} / "
        f"{metrics['latency_p95_ms']}",
        f"- Average candidate count: {metrics['average_candidate_count']}",
        "",
    ]
    rows: list[dict[str, Any]] = [dict(row) for row in report.cases]
    unresolved = [
        row for row in rows if row.get("ground_truth_mode") == GROUND_TRUTH_KEYWORD_FALLBACK
    ]
    if unresolved:
        lines.extend(["## Unresolved Labels (fix before trusting any number)", ""])
        for row in unresolved:
            lines.append(f"- `{row['id']}`: {row['question']}")
        lines.append("")
    failed_cases = [
        row
        for row in rows
        if bool(row["graded"]) and bool(row["answerable"]) != bool(row["evidence_sufficient"])
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
                    f"- answerability: {row['answerability']}",
                    f"- evidence_sufficient: {row['evidence_sufficient']}",
                    f"- supported_chunk_count: {row.get('supported_chunk_count', 0)}",
                    f"- diagnostic_keyword_coverage: {row.get('expected_keyword_coverage', {})}",
                    f"- top_document: {first_chunk.get('document_title', '-')}",
                    f"- top_score: {first_chunk.get('score', '-')}",
                    "",
                ]
            )
    attributed = [row for row in rows if row.get("failure_category")]
    if attributed:
        lines.extend(["## Failure Attribution", ""])
        for row in attributed:
            lines.append(
                f"- `{row['id']}`: {row['failure_category']} "
                f"(decision={row['evidence_decision']}, rank={row['first_relevant_rank']})"
            )
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    """Narrow an untyped metadata value to a dict for report rendering."""
    return value if isinstance(value, dict) else {}


def _knowledge_base_summary(value: object) -> str:
    if not isinstance(value, dict):
        return "-"
    if not value.get("exists"):
        return f"{value.get('id', '-')} (missing)"
    return (
        f"{value.get('name', '-')} "
        f"(documents={value.get('document_count', 0)}, "
        f"active={value.get('active_document_count', 0)}, "
        f"ready={value.get('ready_document_count', 0)}, "
        f"chunks={value.get('chunk_count', 0)}, "
        f"catalog_points={value.get('catalog_point_count', 0)})"
    )
