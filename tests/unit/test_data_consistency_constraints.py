from __future__ import annotations

from typing import cast

from sqlalchemy import Table, UniqueConstraint

from agent_mentor.infrastructure.database.models import (
    AbilityProfileModel,
    EvaluationModel,
    EvaluationReferenceModel,
    IngestionJobModel,
    InterviewQuestionModel,
    InterviewReportModel,
    KnowledgeChunkModel,
    ProfileUpdateEventModel,
    QuestionCoverageModel,
    QuestionReferenceModel,
    UserAnswerModel,
)


def _unique_constraints(model: object) -> list[UniqueConstraint]:
    table = cast(Table, model.__table__)  # pyright: ignore[reportAttributeAccessIssue]
    return [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]


def _has_unique_constraint(model: object, name: str | None, columns: set[str]) -> bool:
    return any(
        constraint.name == name
        and {column.name for column in constraint.columns} == columns
        for constraint in _unique_constraints(model)
    )


def test_interview_questions_are_unique_per_session_sequence() -> None:
    assert _has_unique_constraint(
        InterviewQuestionModel,
        "uq_interview_question_sequence",
        {"session_id", "sequence"},
    )


def test_user_answers_are_idempotent_per_question_key() -> None:
    assert _has_unique_constraint(
        UserAnswerModel,
        "uq_answer_idempotency",
        {"question_id", "idempotency_key"},
    )


def test_each_answer_can_have_only_one_evaluation() -> None:
    assert _has_unique_constraint(EvaluationModel, "uq_evaluation_answer", {"answer_id"})


def test_each_interview_can_have_only_one_report() -> None:
    assert _has_unique_constraint(InterviewReportModel, None, {"session_id"})


def test_profile_update_event_is_idempotent_per_evaluation() -> None:
    assert _has_unique_constraint(
        ProfileUpdateEventModel,
        "uq_profile_event_evaluation",
        {"evaluation_id"},
    )


def test_question_and_evaluation_references_are_not_duplicated() -> None:
    assert _has_unique_constraint(
        QuestionReferenceModel,
        "uq_question_chunk_reference",
        {"question_id", "chunk_id"},
    )
    assert _has_unique_constraint(
        EvaluationReferenceModel,
        "uq_evaluation_chunk_reference",
        {"evaluation_id", "chunk_id"},
    )


def test_question_coverage_and_ability_profile_are_scoped_by_knowledge_base() -> None:
    assert _has_unique_constraint(
        QuestionCoverageModel,
        "uq_question_coverage_point",
        {"question_id", "knowledge_point_id"},
    )
    assert _has_unique_constraint(
        AbilityProfileModel,
        "uq_ability_user_base_point",
        {"user_id", "knowledge_base_id", "knowledge_point"},
    )


def test_knowledge_chunks_support_soft_deactivation_for_safe_reindex() -> None:
    table = cast(Table, KnowledgeChunkModel.__table__)

    assert "is_active" in table.columns
    assert table.columns["is_active"].nullable is False


def test_ingestion_jobs_are_persisted_for_restart_recovery() -> None:
    table = cast(Table, IngestionJobModel.__table__)

    assert table.name == "ingestion_jobs"
    assert "document_id" in table.columns
    assert "status" in table.columns
    assert "attempt_count" in table.columns
