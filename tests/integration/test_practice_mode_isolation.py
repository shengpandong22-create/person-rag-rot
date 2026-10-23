from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import select

from agent_mentor.application.answer_service import AnswerService
from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.application.interview_service import InterviewService, InterviewSnapshot
from agent_mentor.application.knowledge_service import KnowledgeService
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.config import PGVECTOR_DIMENSION
from agent_mentor.domain.interview import AnswerKind, Difficulty, InterviewStatus, TrainingMode
from agent_mentor.domain.knowledge import TrustLevel
from agent_mentor.infrastructure.database.models import (
    InterviewQuestionModel,
    ProfileUpdateEventModel,
    QuestionCoverageModel,
    ReviewTaskModel,
)
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.embedding import DevelopmentEmbeddingGateway
from agent_mentor.infrastructure.retriever import PostgresHybridRetriever
from agent_mentor.rag.documents import DocumentParser

DATABASE_URL = os.getenv("AGENT_MENTOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="isolated PostgreSQL test DB not configured",
)

DOCUMENT_BODY = (
    "# LangGraph checkpoint\n\n"
    "LangGraph 使用 checkpoint 持久化工作流状态，支持中断恢复和人工介入。\n\n"
    "## 可靠性\n\n幂等键可以避免网络重试导致同一道题答案重复写入。\n\n"
    "## 引用边界\n\nRAG 回答必须基于检索证据，并返回可校验引用。"
).encode()


async def _complete_interview(
    interviews: InterviewService, interview_id: UUID
) -> InterviewSnapshot:
    snapshot = await interviews.start(interview_id)
    for _ in range(12):
        if snapshot.current_question is None:
            break
        question = snapshot.current_question
        snapshot = await interviews.submit_answer(
            session_id=interview_id,
            question_id=question.id,
            answer_text=question.reference_answer,
            idempotency_key=f"practice-isolation-{question.id}",
        )
        follow_up = snapshot.current_follow_up
        if follow_up is not None:
            snapshot = await interviews.submit_follow_up_answer(
                session_id=interview_id,
                follow_up_id=follow_up.id,
                answer_text=follow_up.reference_answer,
                idempotency_key=f"practice-isolation-follow-up-{follow_up.id}",
            )
    return snapshot


@pytest.mark.asyncio
async def test_practice_mode_never_pollutes_profile_or_coverage(tmp_path) -> None:
    assert DATABASE_URL is not None
    engine = create_database_engine(DATABASE_URL)
    sessions = create_session_factory(engine)
    embedding = DevelopmentEmbeddingGateway(PGVECTOR_DIMENSION)
    knowledge = KnowledgeService(
        sessions,
        DocumentParser(max_pdf_pages=20),
        embedding,
        tmp_path,
        240,
        40,
        8,
        5,
    )
    retriever = PostgresHybridRetriever(sessions, embedding, max_chunks_per_document=3)
    answers = AnswerService(
        sessions,
        retriever,
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    del answers
    interviews = InterviewService(
        sessions,
        retriever,
        retrieval_candidate_k=20,
    )
    evaluations = EvaluationService(sessions)
    profiles = ProfileService(sessions)

    try:
        base = await knowledge.create_base("练习隔离测试知识库", "practice 模式不得污染画像与覆盖")
        document, duplicate = await knowledge.add_document(
            base.id,
            "langgraph.md",
            DOCUMENT_BODY,
            TrustLevel.CURATED,
            None,
            "integration-test",
        )
        assert not duplicate
        await knowledge.ingest(document.id)
        assert (await knowledge.get_document(document.id)).status == "ready"

        coverage_before = await profiles.get_coverage(base.id)
        assert coverage_before.attempted == 0
        assert coverage_before.verified == 0

        # --- practice run: 5 hard questions must not touch learning state ---
        practice = await interviews.create_interview(
            knowledge_base_id=base.id,
            topic="LangGraph checkpoint",
            difficulty=Difficulty.HARD,
            question_count=5,
            training_mode=TrainingMode.PRACTICE,
        )
        assert practice.training_mode == "practice"
        assert practice.difficulty == "hard"
        assert practice.question_count == 5

        completed = await _complete_interview(interviews, practice.id)
        assert completed.session.status == InterviewStatus.COMPLETED
        assert sum(answer.answer_kind == AnswerKind.PRIMARY for answer in completed.answers) == 5

        practice_report = await evaluations.build_report(practice.id)
        assert practice_report.training_mode == "practice"

        practice_profile = await profiles.apply_interview_evaluations(practice.id)
        assert practice_profile.abilities == ()
        assert practice_profile.errors == ()
        assert practice_profile.review_tasks == ()

        async with sessions() as db:
            practice_question_ids = list(
                (
                    await db.scalars(
                        select(InterviewQuestionModel.id).where(
                            InterviewQuestionModel.session_id == practice.id
                        )
                    )
                ).all()
            )
            practice_coverage = list(
                (
                    await db.scalars(
                        select(QuestionCoverageModel).where(
                            QuestionCoverageModel.question_id.in_(practice_question_ids)
                        )
                    )
                ).all()
            )
            profile_events = list(
                (
                    await db.scalars(
                        select(ProfileUpdateEventModel).where(
                            ProfileUpdateEventModel.knowledge_base_id == base.id
                        )
                    )
                ).all()
            )
            review_tasks = list(
                (
                    await db.scalars(
                        select(ReviewTaskModel).where(
                            ReviewTaskModel.knowledge_base_id == base.id
                        )
                    )
                ).all()
            )
        assert practice_coverage == []
        assert profile_events == []
        assert review_tasks == []

        coverage_after_practice = await profiles.get_coverage(base.id)
        assert coverage_after_practice.attempted == coverage_before.attempted
        assert coverage_after_practice.verified == coverage_before.verified
        assert coverage_after_practice.uncovered == coverage_before.uncovered

        # --- profile training run: hard/1 request is coerced to 3 medium ---
        training = await interviews.create_interview(
            knowledge_base_id=base.id,
            topic="LangGraph checkpoint",
            difficulty=Difficulty.HARD,
            question_count=1,
            training_mode=TrainingMode.PROFILE_TRAINING,
        )
        assert training.training_mode == "profile_training"
        assert training.difficulty == "medium"
        assert training.question_count == 3

        trained = await _complete_interview(interviews, training.id)
        assert trained.session.status == InterviewStatus.COMPLETED

        training_report = await evaluations.build_report(training.id)
        assert training_report.training_mode == "profile_training"

        trained_profile = await profiles.apply_interview_evaluations(training.id)
        assert trained_profile.abilities

        async with sessions() as db:
            training_question_ids = list(
                (
                    await db.scalars(
                        select(InterviewQuestionModel.id).where(
                            InterviewQuestionModel.session_id == training.id
                        )
                    )
                ).all()
            )
            training_coverage = list(
                (
                    await db.scalars(
                        select(QuestionCoverageModel).where(
                            QuestionCoverageModel.question_id.in_(training_question_ids)
                        )
                    )
                ).all()
            )
        assert training_coverage

        coverage_after_training = await profiles.get_coverage(base.id)
        assert coverage_after_training.attempted > coverage_before.attempted
    finally:
        await engine.dispose()
