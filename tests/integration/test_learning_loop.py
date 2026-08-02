from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from agent_mentor.application.answer_service import AnswerService
from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.application.interview_service import InterviewService
from agent_mentor.application.knowledge_service import KnowledgeService
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.domain.interview import Difficulty, InterviewStatus
from agent_mentor.domain.knowledge import DocumentStatus, TrustLevel
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.embedding import DevelopmentEmbeddingGateway
from agent_mentor.infrastructure.retriever import PostgresHybridRetriever
from agent_mentor.ports.knowledge_retriever import RetrievalQuery
from agent_mentor.rag.documents import DocumentParser

DATABASE_URL = os.getenv("AGENT_MENTOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="isolated PostgreSQL test DB not configured",
)


@pytest.mark.asyncio
async def test_database_backed_learning_loop_is_idempotent_and_recoverable(tmp_path) -> None:
    assert DATABASE_URL is not None
    engine = create_database_engine(DATABASE_URL)
    sessions = create_session_factory(engine)
    embedding = DevelopmentEmbeddingGateway(1536)
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
    interviews = InterviewService(
        sessions,
        retriever,
        retrieval_candidate_k=20,
    )
    evaluations = EvaluationService(sessions)
    profiles = ProfileService(sessions)

    try:
        base = await knowledge.create_base("集成测试知识库", "隔离数据库端到端回归")
        document, duplicate = await knowledge.add_document(
            base.id,
            "langgraph.md",
            (
                "# LangGraph checkpoint\n\n"
                "LangGraph 使用 checkpoint 持久化工作流状态，支持中断恢复和人工介入。\n\n"
                "## 可靠性\n\n幂等键可以避免网络重试导致同一道题答案重复写入。"
            ).encode(),
            TrustLevel.CURATED,
            None,
            "integration-test",
        )
        assert not duplicate
        await knowledge.ingest(document.id)
        assert (await knowledge.get_document(document.id)).status == DocumentStatus.READY

        interrupted, _ = await knowledge.add_document(
            base.id,
            "interrupted.md",
            b"# Interrupted background ingestion",
            TrustLevel.CURATED,
            None,
            "integration-test",
        )
        async with sessions() as db:
            stale = await db.get(type(interrupted), interrupted.id)
            assert stale is not None
            stale.updated_at = datetime.now(UTC) - timedelta(minutes=20)
            await db.commit()
        assert await knowledge.recover_interrupted_ingestions() == 1
        recovered = await knowledge.get_document(interrupted.id)
        assert recovered.status == DocumentStatus.FAILED
        assert "重新索引" in (recovered.error_message or "")

        retrieved = await retriever.retrieve(
            query=RetrievalQuery(
                knowledge_base_id=base.id,
                query="LangGraph 如何利用 checkpoint 恢复工作流状态？",
                top_k=3,
                candidate_k=10,
            )
        )
        assert retrieved
        assert "checkpoint" in retrieved[0].content.lower()

        rag = await answers.answer(
            knowledge_base_id=base.id,
            question="LangGraph 如何利用 checkpoint 恢复工作流状态？",
        )
        assert rag.citations
        assert rag.generation_mode == "deterministic"

        interview = await interviews.create_interview(
            knowledge_base_id=base.id,
            topic="LangGraph checkpoint",
            difficulty=Difficulty.MEDIUM,
            question_count=2,
        )
        snapshot = await interviews.start(interview.id)
        first_question = snapshot.current_question
        assert first_question is not None
        await knowledge.ingest(document.id)
        assert (await knowledge.get_document(document.id)).status == DocumentStatus.READY
        assert (await interviews.get(interview.id)).current_reference_chunk_ids

        first = await interviews.submit_answer(
            session_id=interview.id,
            question_id=first_question.id,
            answer_text=first_question.reference_answer,
            idempotency_key="integration-answer-1",
        )
        duplicate_submit = await interviews.submit_answer(
            session_id=interview.id,
            question_id=first_question.id,
            answer_text=first_question.reference_answer,
            idempotency_key="integration-answer-1",
        )
        assert len(first.answers) == len(duplicate_submit.answers) == 1

        second_question = first.current_question
        assert second_question is not None
        completed = await interviews.submit_answer(
            session_id=interview.id,
            question_id=second_question.id,
            answer_text=second_question.reference_answer,
            idempotency_key="integration-answer-2",
        )
        assert completed.session.status == InterviewStatus.COMPLETED
        assert len(completed.answers) == 2
        assert (await interviews.get(interview.id)).session.status == InterviewStatus.COMPLETED

        first_report = await evaluations.build_report(interview.id)
        second_report = await evaluations.build_report(interview.id)
        assert first_report.report.id == second_report.report.id
        assert first_report.report.total_score == second_report.report.total_score

        first_profile = await profiles.apply_interview_evaluations(interview.id)
        second_profile = await profiles.apply_interview_evaluations(interview.id)
        topic_profiles = [item for item in first_profile.abilities if item.profile_level == "topic"]
        subtopic_profiles = [
            item for item in first_profile.abilities if item.profile_level == "subtopic"
        ]
        assert len(topic_profiles) == 1
        assert topic_profiles[0].topic_key == "langgraph"
        assert topic_profiles[0].knowledge_point == "topic::langgraph"
        assert subtopic_profiles
        assert all(item.topic_key == "langgraph" for item in subtopic_profiles)
        assert all(item.knowledge_point != item.subtopic_title for item in subtopic_profiles)
        first_versions = {
            item.knowledge_point: (item.version, item.confidence_weighted_count)
            for item in first_profile.abilities
        }
        second_versions = {
            item.knowledge_point: (item.version, item.confidence_weighted_count)
            for item in second_profile.abilities
        }
        assert first_versions
        assert first_versions == second_versions
        assert await profiles.backfill_two_layer_profiles(interview.user_id) == 0

        isolated_base = await knowledge.create_base(
            "画像隔离对照知识库", "不应读取另一知识库的画像和报告"
        )
        isolated_profile = await profiles.get_snapshot(interview.user_id, isolated_base.id)
        assert isolated_profile.abilities == ()
        assert isolated_profile.errors == ()
        assert isolated_profile.review_tasks == ()
        assert await evaluations.list_report_history(interview.user_id, isolated_base.id) == []

        scoped_profile = await profiles.get_snapshot(interview.user_id, base.id)
        scoped_history = await evaluations.list_report_history(interview.user_id, base.id)
        assert scoped_profile.abilities
        assert len(scoped_history) == 1
        assert scoped_history[0].report.session_id == interview.id
    finally:
        await engine.dispose()
