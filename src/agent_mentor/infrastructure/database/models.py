from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from agent_mentor.domain.knowledge import DocumentStatus, TrustLevel


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class KnowledgeBaseModel(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list[SourceDocumentModel]] = relationship(back_populates="knowledge_base")


class SourceDocumentModel(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "content_hash", name="uq_document_content_hash"),
        UniqueConstraint(
            "knowledge_base_id", "logical_name", "version", name="uq_document_version"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    logical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    trust_level: Mapped[TrustLevel] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(String(32), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    knowledge_base: Mapped[KnowledgeBaseModel] = relationship(back_populates="documents")
    chunks: Mapped[list[KnowledgeChunkModel]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
        Index("ix_chunks_search_text", "search_text", postgresql_using="gin"),
        Index("ix_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    search_text: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[SourceDocumentModel] = relationship(back_populates="chunks")


class KnowledgePointModel(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False)


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    messages: Mapped[list[ChatMessageModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_diagnostics: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[ChatSessionModel] = relationship(back_populates="messages")
    citations: Mapped[list[ChatCitationModel]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class ChatCitationModel(Base):
    __tablename__ = "chat_citations"
    __table_args__ = (UniqueConstraint("message_id", "chunk_id", name="uq_message_chunk_citation"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_chunks.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message: Mapped[ChatMessageModel] = relationship(back_populates="citations")


class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(160), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    workflow_thread_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    questions: Mapped[list[InterviewQuestionModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    checkpoints: Mapped[list[WorkflowCheckpointModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class InterviewQuestionModel(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_interview_question_sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    knowledge_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=False)
    rubric: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    placeholder_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSessionModel] = relationship(back_populates="questions")
    references: Mapped[list[QuestionReferenceModel]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    answers: Mapped[list[UserAnswerModel]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class QuestionReferenceModel(Base):
    __tablename__ = "question_references"
    __table_args__ = (
        UniqueConstraint("question_id", "chunk_id", name="uq_question_chunk_reference"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_questions.id"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_chunks.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question: Mapped[InterviewQuestionModel] = relationship(back_populates="references")


class UserAnswerModel(Base):
    __tablename__ = "user_answers"
    __table_args__ = (
        UniqueConstraint("question_id", "idempotency_key", name="uq_answer_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_questions.id"), nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    question: Mapped[InterviewQuestionModel] = relationship(back_populates="answers")
    evaluations: Mapped[list[EvaluationModel]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )


class WorkflowCheckpointModel(Base):
    __tablename__ = "workflow_checkpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), nullable=False, index=True
    )
    thread_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    node: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSessionModel] = relationship(back_populates="checkpoints")


class EvaluationModel(Base):
    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("answer_id", name="uq_evaluation_answer"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_questions.id"), nullable=False, index=True
    )
    answer_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_answers.id"), nullable=False, index=True
    )
    correctness: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[int] = mapped_column(Integer, nullable=False)
    communication: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    covered_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    missing_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    incorrect_claims: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    answer_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    review_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    answer: Mapped[UserAnswerModel] = relationship(back_populates="evaluations")
    profile_events: Mapped[list[ProfileUpdateEventModel]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    references: Mapped[list[EvaluationReferenceModel]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationReferenceModel(Base):
    __tablename__ = "evaluation_references"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "chunk_id", name="uq_evaluation_chunk_reference"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("evaluations.id"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_chunks.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evaluation: Mapped[EvaluationModel] = relationship(back_populates="references")


class InterviewReportModel(Base):
    __tablename__ = "interview_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), nullable=False, unique=True
    )
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    dimension_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    knowledge_point_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    error_summary: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    low_confidence_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    disputed_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    next_steps: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AbilityProfileModel(Base):
    __tablename__ = "ability_profiles"
    __table_args__ = (UniqueConstraint("user_id", "knowledge_point", name="uq_ability_user_point"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    knowledge_point: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_level: Mapped[str] = mapped_column(String(20), nullable=False, default="legacy")
    topic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subtopic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subtopic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_weighted_count: Mapped[float] = mapped_column(Float, nullable=False)
    last_evaluation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evaluations.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ErrorPatternModel(Base):
    __tablename__ = "error_patterns"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "knowledge_point", "error_type", name="uq_error_user_point_type"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    knowledge_point: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_level: Mapped[str] = mapped_column(String(20), nullable=False, default="legacy")
    topic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subtopic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subtopic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluation_id: Mapped[UUID] = mapped_column(ForeignKey("evaluations.id"), nullable=False)


class ReviewTaskModel(Base):
    __tablename__ = "review_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    knowledge_point: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_level: Mapped[str] = mapped_column(String(20), nullable=False, default="legacy")
    topic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subtopic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subtopic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_evaluation_id: Mapped[UUID] = mapped_column(ForeignKey("evaluations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProfileUpdateEventModel(Base):
    __tablename__ = "profile_update_events"
    __table_args__ = (UniqueConstraint("evaluation_id", name="uq_profile_event_evaluation"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(ForeignKey("evaluations.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(80), nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    changes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evaluation: Mapped[EvaluationModel] = relationship(back_populates="profile_events")
