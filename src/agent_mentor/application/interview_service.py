from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.application.coverage_catalog import map_question_coverage
from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.domain.interview import (
    AnswerKind,
    Difficulty,
    FollowUpStatus,
    InterviewStatus,
    QuestionType,
    assert_transition,
)
from agent_mentor.infrastructure.database.models import (
    InterviewFollowUpModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    KnowledgeCatalogPointModel,
    KnowledgeCatalogSourceModel,
    QuestionCoverageModel,
    QuestionReferenceModel,
    UserAnswerModel,
    WorkflowCheckpointModel,
)
from agent_mentor.logging import log_event
from agent_mentor.ports.knowledge_retriever import (
    KnowledgeRetriever,
    RetrievalQuery,
    RetrievedChunk,
)
from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext
from agent_mentor.rag.retrieval import validate_citations
from agent_mentor.workflows.interview import (
    InterviewWorkflowState,
    advance_question,
    checkpoint_summary,
    finish_interview,
    generate_question,
    load_profile,
    persist_answer,
    plan_interview,
    wait_for_answer,
    workflow_node_spec,
)

QUESTION_PROMPT_VERSION = "interview_question_v1"
RECENT_QUESTION_COOLDOWN_LIMIT = 12


@dataclass(frozen=True, slots=True)
class InterviewSnapshot:
    session: InterviewSessionModel
    current_question: InterviewQuestionModel | None
    current_follow_up: InterviewFollowUpModel | None
    current_reference_chunk_ids: tuple[UUID, ...]
    answers: tuple[UserAnswerModel, ...]


@dataclass(frozen=True, slots=True)
class WorkflowTraceItem:
    checkpoint_id: UUID
    node: str
    event: str
    label: str
    input_summary: str
    output_summary: str
    waiting_for_answer: bool
    is_fallback: bool
    error_message: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CoverageFocus:
    point_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class QuestionAngle:
    key: str
    title: str
    prompt_hint: str
    search_hint: str


@dataclass(frozen=True, slots=True)
class InterviewPolicyDecision:
    next_action: str
    reason: str
    target_topic: str
    difficulty: str
    deterministic_gate: str


class InterviewQuestionOutput(BaseModel):
    question_text: str = Field(min_length=1, max_length=1200)
    reference_answer: str = Field(min_length=1, max_length=4000)
    required_points: list[str] = Field(default_factory=list, max_length=8)
    generation_mode: str = "llm"
    fallback_reason: str | None = None


class FollowUpDecisionOutput(BaseModel):
    should_follow_up: bool = False
    follow_up_question: str | None = Field(default=None, max_length=1200)
    reference_answer: str | None = Field(default=None, max_length=3000)
    expected_points: list[str] = Field(default_factory=list, max_length=6)
    reason: str = Field(default="不需要追问。", max_length=800)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    generation_mode: str = "llm"
    fallback_reason: str | None = None


QUESTION_ANGLES: tuple[QuestionAngle, ...] = (
    QuestionAngle(
        key="concept_boundary",
        title="概念边界",
        prompt_hint="要求候选人说清定义、适用边界、容易混淆的相邻概念。",
        search_hint="定义 边界 概念混淆 适用场景",
    ),
    QuestionAngle(
        key="architecture_tradeoff",
        title="架构取舍",
        prompt_hint="要求候选人从组件职责、数据流、工程取舍和替代方案展开。",
        search_hint="架构 取舍 组件 数据流 替代方案",
    ),
    QuestionAngle(
        key="failure_handling",
        title="异常与降级",
        prompt_hint="要求候选人说明失败场景、兜底策略、重试/幂等和风险控制。",
        search_hint="异常 降级 重试 幂等 风险",
    ),
    QuestionAngle(
        key="production_observability",
        title="生产化与观测",
        prompt_hint="要求候选人结合日志、指标、Trace、评估集或运行态可观测性说明落地方案。",
        search_hint="生产化 可观测 日志 指标 Trace 评估",
    ),
    QuestionAngle(
        key="comparison",
        title="对比辨析",
        prompt_hint="要求候选人对比相似方案，说明为什么选当前方案以及不选什么。",
        search_hint="对比 区别 方案选择 优缺点",
    ),
    QuestionAngle(
        key="quality_evaluation",
        title="质量评估",
        prompt_hint="要求候选人说明如何验证效果、设计指标、构造评测和判断质量提升。",
        search_hint="质量 评估 指标 验收 回归",
    ),
)


class InterviewService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        retriever: KnowledgeRetriever,
        llm: LLMGateway | None = None,
        *,
        retrieval_candidate_k: int,
        default_model: str | None = None,
    ) -> None:
        self._sessions = sessions
        self._retriever = retriever
        self._llm = llm
        self._retrieval_candidate_k = retrieval_candidate_k
        self._default_model = default_model

    async def create_interview(
        self,
        *,
        knowledge_base_id: UUID,
        topic: str,
        profile_topic_key: str | None = None,
        profile_topic_title: str | None = None,
        profile_subtopic_key: str | None = None,
        profile_subtopic_title: str | None = None,
        difficulty: Difficulty,
        question_count: int,
    ) -> InterviewSessionModel:
        now = datetime.now(UTC)
        session_id = uuid4()
        interview = InterviewSessionModel(
            id=session_id,
            user_id=DEFAULT_USER_ID,
            knowledge_base_id=knowledge_base_id,
            topic=topic,
            profile_topic_key=profile_topic_key,
            profile_topic_title=profile_topic_title,
            profile_subtopic_key=profile_subtopic_key,
            profile_subtopic_title=profile_subtopic_title,
            difficulty=difficulty,
            question_count=question_count,
            status=InterviewStatus.CREATED,
            current_question_index=0,
            workflow_thread_id=str(session_id),
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        async with self._sessions() as db:
            db.add(interview)
            await db.commit()
            await db.refresh(interview)
        return interview

    async def start(self, session_id: UUID) -> InterviewSnapshot:
        async with self._sessions() as db:
            interview = await self._get_session(db, session_id)
            if interview.status == InterviewStatus.WAITING_FOR_ANSWER:
                return await self._snapshot(db, interview)
            if interview.status != InterviewStatus.CREATED:
                raise AppError("WORKFLOW_STATE_CONFLICT", "Interview cannot be started now.", 409)
            assert_transition(interview.status, InterviewStatus.WAITING_FOR_ANSWER)
            now = datetime.now(UTC)
            interview.status = InterviewStatus.WAITING_FOR_ANSWER
            interview.started_at = now
            interview.updated_at = now
            await self._checkpoint(
                db,
                load_profile(self._state(interview, "load_profile", waiting=False)),
            )
            await self._checkpoint(db, plan_interview(self._state(interview, "plan_interview")))
            question = await self._create_question(db, interview, sequence=1)
            await self._checkpoint(
                db,
                wait_for_answer(generate_question(self._state(interview, "generate_question"))),
            )
            await db.commit()
            await db.refresh(question)
            await db.refresh(interview)
            return await self._snapshot(db, interview)

    async def get(self, session_id: UUID) -> InterviewSnapshot:
        async with self._sessions() as db:
            return await self._snapshot(db, await self._get_session(db, session_id))

    async def workflow_trace(self, session_id: UUID) -> tuple[WorkflowTraceItem, ...]:
        async with self._sessions() as db:
            await self._get_session(db, session_id)
            checkpoints = (
                await db.scalars(
                    select(WorkflowCheckpointModel)
                    .where(WorkflowCheckpointModel.session_id == session_id)
                    .order_by(WorkflowCheckpointModel.created_at, WorkflowCheckpointModel.id)
                )
            ).all()
            return tuple(self._trace_item(checkpoint) for checkpoint in checkpoints)

    async def submit_answer(
        self,
        *,
        session_id: UUID,
        question_id: UUID,
        answer_text: str,
        idempotency_key: str,
    ) -> InterviewSnapshot:
        async with self._sessions() as db:
            interview = await self._get_session_for_update(db, session_id)
            question = await self._get_question(db, question_id)
            if question.session_id != session_id:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Question does not belong to interview.", 409
                )

            existing = await db.scalar(
                select(UserAnswerModel).where(
                    UserAnswerModel.question_id == question_id,
                    UserAnswerModel.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                return await self._snapshot(db, interview)

            existing_primary = await db.scalar(
                select(UserAnswerModel).where(
                    UserAnswerModel.question_id == question_id,
                    UserAnswerModel.answer_kind == AnswerKind.PRIMARY,
                )
            )
            if existing_primary is not None:
                return await self._snapshot(db, interview)

            if interview.status != InterviewStatus.WAITING_FOR_ANSWER:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Interview is not waiting for an answer.", 409
                )
            if question.sequence != interview.current_question_index + 1:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Question is not the current question.", 409
                )

            db.add(
                answer := UserAnswerModel(
                    id=uuid4(),
                    question_id=question_id,
                    answer_text=answer_text,
                    answer_kind=AnswerKind.PRIMARY,
                    idempotency_key=idempotency_key,
                    submitted_at=datetime.now(UTC),
                )
            )
            question.placeholder_feedback = "Answer received; evaluation will run after completion."
            await self._checkpoint(db, persist_answer(self._state(interview, "persist_answer")))

            await db.flush()
            follow_up = await self._maybe_create_follow_up(db, interview, question, answer)
            if follow_up is None:
                await self._advance_or_finish_after_answer(db, interview)

            try:
                await db.commit()
            except IntegrityError as error:
                await db.rollback()
                if "uq_answer_idempotency" not in str(error.orig):
                    raise
                interview = await self._get_session(db, session_id)
                return await self._snapshot(db, interview)
            await db.refresh(interview)
            return await self._snapshot(db, interview)

    async def submit_follow_up_answer(
        self,
        *,
        session_id: UUID,
        follow_up_id: UUID,
        answer_text: str,
        idempotency_key: str,
    ) -> InterviewSnapshot:
        async with self._sessions() as db:
            interview = await self._get_session_for_update(db, session_id)
            follow_up = await self._get_follow_up(db, follow_up_id)
            question = await self._get_question(db, follow_up.question_id)
            if question.session_id != session_id:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Follow-up does not belong to interview.", 409
                )
            if interview.status != InterviewStatus.WAITING_FOR_ANSWER:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Interview is not waiting for an answer.", 409
                )
            if question.sequence != interview.current_question_index + 1:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT",
                    "Follow-up is not attached to the current question.",
                    409,
                )

            existing = await db.scalar(
                select(UserAnswerModel)
                .where(
                    UserAnswerModel.question_id == question.id,
                    UserAnswerModel.idempotency_key == idempotency_key,
                )
                .order_by(UserAnswerModel.submitted_at)
            )
            if existing is not None:
                if follow_up.status == FollowUpStatus.PENDING:
                    follow_up.status = FollowUpStatus.ANSWERED
                    follow_up.answer_id = existing.id
                    follow_up.answered_at = existing.submitted_at
                    await self._advance_or_finish_after_answer(db, interview)
                    await db.commit()
                return await self._snapshot(db, interview)

            if follow_up.status != FollowUpStatus.PENDING:
                return await self._snapshot(db, interview)

            answer = UserAnswerModel(
                id=uuid4(),
                question_id=question.id,
                answer_text=answer_text,
                answer_kind=AnswerKind.FOLLOW_UP,
                idempotency_key=idempotency_key,
                submitted_at=datetime.now(UTC),
            )
            db.add(answer)
            await db.flush()
            follow_up.status = FollowUpStatus.ANSWERED
            follow_up.answer_id = answer.id
            follow_up.answered_at = answer.submitted_at
            await self._checkpoint(db, self._state(interview, "persist_follow_up"))
            await self._advance_or_finish_after_answer(db, interview)

            try:
                await db.commit()
            except IntegrityError as error:
                await db.rollback()
                if "uq_answer_idempotency" not in str(error.orig):
                    raise
                interview = await self._get_session(db, session_id)
                return await self._snapshot(db, interview)
            await db.refresh(interview)
            return await self._snapshot(db, interview)

    async def _maybe_create_follow_up(
        self,
        db: AsyncSession,
        interview: InterviewSessionModel,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
    ) -> InterviewFollowUpModel | None:
        existing = await db.scalar(
            select(InterviewFollowUpModel).where(InterviewFollowUpModel.question_id == question.id)
        )
        if existing is not None:
            return existing if existing.status == FollowUpStatus.PENDING else None

        decision = await self._generate_follow_up_decision(interview, question, answer)
        prompt = (decision.follow_up_question or "").strip()
        if (
            not decision.should_follow_up
            or not prompt
            or decision.confidence < 0.70
            or question.sequence > interview.question_count
        ):
            return None

        follow_up = InterviewFollowUpModel(
            id=uuid4(),
            question_id=question.id,
            prompt=prompt,
            reference_answer=(
                decision.reference_answer
                or self._follow_up_reference_answer(question, decision.expected_points)
            ),
            reason=decision.reason,
            expected_points=decision.expected_points or self._required_points(question)[:3],
            confidence=round(decision.confidence, 2),
            status=FollowUpStatus.PENDING,
            answer_id=None,
            created_at=datetime.now(UTC),
            answered_at=None,
        )
        db.add(follow_up)
        await self._checkpoint(db, self._state(interview, "generate_follow_up", waiting=True))
        return follow_up

    async def _generate_follow_up_decision(
        self,
        interview: InterviewSessionModel,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
    ) -> FollowUpDecisionOutput:
        if self._answer_has_substantive_signal(answer.answer_text):
            return FollowUpDecisionOutput(
                should_follow_up=False,
                reason="主回答已经具备工程化展开信号，本题不追加追问。",
                confidence=0.84,
                generation_mode="deterministic_gate",
            )
        fallback = self._deterministic_follow_up_decision(question, answer)
        if self._llm is None:
            return fallback
        try:
            return await self._llm.generate_structured(
                operation="interview_follow_up_decision",
                messages=[
                    Message(
                        role="system",
                        content=(
                            "你是资深 AI Agent 面试官。你只能决定是否对当前题追加一次追问。"
                            "追问必须基于题目、用户回答、参考答案和 Rubric，不能引入资料外断言。"
                            "如果回答已经覆盖主要要点，should_follow_up 必须为 false。"
                        ),
                    ),
                    Message(
                        role="user",
                        content=self._follow_up_prompt(interview, question, answer),
                    ),
                ],
                response_model=FollowUpDecisionOutput,
                model_policy=ModelPolicy(model=self._default_model),
                trace_context=TraceContext(
                    trace_id=str(uuid4()), operation="interview_follow_up_decision"
                ),
            )
        except Exception as error:
            log_event(
                logging.WARNING,
                "interview_follow_up.llm_fallback",
                error_type=type(error).__name__,
                fallback="deterministic_follow_up",
                topic=interview.topic,
                question_id=str(question.id),
            )
            return fallback

    def _deterministic_follow_up_decision(
        self, question: InterviewQuestionModel, answer: UserAnswerModel
    ) -> FollowUpDecisionOutput:
        answer_text = answer.answer_text.strip()
        answer_lower = answer_text.lower()
        weak_markers = ("不知道", "不确定", "不会", "不清楚", "uncertain", "not sure")
        required_points = self._required_points(question)
        covered = [
            point
            for point in required_points
            if self._contains_meaning(answer_lower, point.lower())
        ]
        coverage_ratio = len(covered) / max(1, len(required_points))
        has_uncertainty = any(
            marker in answer_lower or marker in answer_text for marker in weak_markers
        )
        should_follow_up = (
            coverage_ratio < 0.80
            and (len(answer_text) < 120 or coverage_ratio < 0.45 or has_uncertainty)
        )
        if not should_follow_up:
            return FollowUpDecisionOutput(
                should_follow_up=False,
                reason="主回答已经覆盖大部分 Rubric 要点，不追加追问。",
                confidence=0.82,
                generation_mode="deterministic",
            )
        missing = [point for point in required_points if point not in covered][:3]
        focus = "、".join(missing or required_points[:2] or question.knowledge_points[:2])
        return FollowUpDecisionOutput(
            should_follow_up=True,
            follow_up_question=(
                f"追问：你刚才的回答还没有充分展开“{focus or question.question_text[:30]}”。"
                "请补充它在实际项目中的边界、风险和验证方式。"
            ),
            reference_answer=self._follow_up_reference_answer(question, missing),
            expected_points=missing or required_points[:3] or question.knowledge_points[:3],
            reason="主回答偏短或覆盖要点不足，需要一次受控追问验证知识边界。",
            confidence=0.76,
            generation_mode="deterministic",
            fallback_reason="llm_unavailable",
        )

    def _follow_up_prompt(
        self,
        interview: InterviewSessionModel,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
    ) -> str:
        return (
            f"面试主题：{interview.topic}\n"
            f"题号：{question.sequence}/{interview.question_count}\n"
            f"题目：{question.question_text}\n"
            f"参考答案：{question.reference_answer[:2400]}\n"
            f"Rubric：{question.rubric}\n"
            f"用户主回答：{answer.answer_text[:2400]}\n\n"
            "请判断是否需要一次追问。只有当用户回答明显遗漏关键点、边界、风险或工程验证方式时才追问。"
            "如果需要追问，请输出一个聚焦的问题、参考答案、expected_points、reason、confidence。"
            "如果不需要追问，should_follow_up=false。"
        )

    def _follow_up_reference_answer(
        self, question: InterviewQuestionModel, expected_points: list[str]
    ) -> str:
        focus = "、".join(expected_points[:3]) if expected_points else "遗漏的关键点"
        return (
            f"应围绕 {focus} 补充：先给出定义或判断标准，再说明工程流程、边界风险，"
            f"最后结合本题参考答案说明如何验证。参考依据：{question.reference_answer[:1000]}"
        )

    async def _advance_or_finish_after_answer(
        self, db: AsyncSession, interview: InterviewSessionModel
    ) -> None:
        if interview.current_question_index + 1 >= interview.question_count:
            assert_transition(interview.status, InterviewStatus.COMPLETED)
            interview.current_question_index = interview.question_count
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.now(UTC)
            interview.updated_at = datetime.now(UTC)
            await self._checkpoint(db, finish_interview(self._state(interview, "finish_interview")))
            return
        next_state = advance_question(self._state(interview, "advance_question"))
        interview.current_question_index = next_state.current_question_index
        interview.updated_at = datetime.now(UTC)
        await self._create_question(db, interview, sequence=interview.current_question_index + 1)
        await self._checkpoint(db, wait_for_answer(next_state))

    async def events(self, session_id: UUID) -> AsyncIterator[dict[str, object]]:
        snapshot = await self.get(session_id)
        trace = await self.workflow_trace(session_id)
        yield {
            "event": "workflow.state",
            "data": {
                "session_id": str(snapshot.session.id),
                "status": str(snapshot.session.status),
                "current_question_index": snapshot.session.current_question_index,
                "waiting_for_answer": snapshot.session.status == InterviewStatus.WAITING_FOR_ANSWER,
            },
        }
        for item in trace:
            yield {
                "event": item.event,
                "data": {
                    "checkpoint_id": str(item.checkpoint_id),
                    "session_id": str(session_id),
                    "node": item.node,
                    "label": item.label,
                    "input_summary": item.input_summary,
                    "output_summary": item.output_summary,
                    "waiting_for_answer": item.waiting_for_answer,
                    "is_fallback": item.is_fallback,
                    "error_message": item.error_message,
                    "created_at": item.created_at.isoformat(),
                },
            }
        if snapshot.current_question is not None:
            yield {
                "event": "question.current",
                "data": {
                    "question_id": str(snapshot.current_question.id),
                    "sequence": snapshot.current_question.sequence,
                },
            }
        if snapshot.session.status == InterviewStatus.COMPLETED:
            yield {"event": "workflow.completed", "data": {"session_id": str(session_id)}}

    async def _create_question(
        self, db: AsyncSession, interview: InterviewSessionModel, *, sequence: int
    ) -> InterviewQuestionModel:
        existing = await db.scalar(
            select(InterviewQuestionModel).where(
                InterviewQuestionModel.session_id == interview.id,
                InterviewQuestionModel.sequence == sequence,
            )
        )
        if existing is not None:
            return existing
        question_type = self._question_type(sequence)
        prior_questions = list(
            (
                await db.scalars(
                    select(InterviewQuestionModel.question_text)
                    .where(
                        InterviewQuestionModel.session_id == interview.id,
                        InterviewQuestionModel.sequence < sequence,
                    )
                    .order_by(InterviewQuestionModel.sequence)
                )
            ).all()
        )
        recent_questions = await self._recent_knowledge_base_questions(db, interview)
        avoid_questions = [*prior_questions, *recent_questions]
        coverage_focus = await self._coverage_gap_focus(db, interview, sequence=sequence)
        coverage_focus_title = coverage_focus.title if coverage_focus else None
        profile_focus_title = self._profile_focus_title(interview)
        primary_focus_title = coverage_focus_title or profile_focus_title
        question_angle = self._question_angle(interview, sequence)
        policy = self._question_policy(
            interview,
            sequence=sequence,
            coverage_focus=coverage_focus_title,
            profile_focus=profile_focus_title,
            question_angle=question_angle,
            recent_questions=recent_questions,
        )
        query_text = self._question_search_text(
            interview, question_type, primary_focus_title, question_angle
        )
        chunks = await self._retriever.retrieve(
            RetrievalQuery(
                knowledge_base_id=interview.knowledge_base_id,
                query=query_text,
                top_k=3,
                candidate_k=self._retrieval_candidate_k,
            )
        )
        citation_ids = [chunk.chunk_id for chunk in chunks[:2]]
        validate_citations(citation_ids, chunks)
        generated = await self._generate_question_output(
            interview,
            sequence,
            question_type,
            question_angle,
            chunks,
            prior_questions,
            recent_questions,
            coverage_focus_title,
            profile_focus_title,
            policy,
        )
        for focus_title in (profile_focus_title, coverage_focus_title):
            if focus_title and focus_title not in generated.required_points:
                generated.required_points.insert(0, focus_title)
        generated.required_points = generated.required_points[:8]
        if self._is_too_similar(generated.question_text, avoid_questions):
            generated = InterviewQuestionOutput(
                question_text=self._question_text(interview, sequence, question_angle, chunks),
                reference_answer=generated.reference_answer,
                required_points=generated.required_points,
                generation_mode="deterministic_similarity_fallback",
                fallback_reason=(
                    "similar_to_current_interview_question"
                    if self._is_too_similar(generated.question_text, prior_questions)
                    else "similar_to_recent_knowledge_base_question"
                ),
            )
        question = InterviewQuestionModel(
            id=uuid4(),
            session_id=interview.id,
            sequence=sequence,
            question_text=generated.question_text,
            question_type=question_type,
            difficulty=interview.difficulty,
            knowledge_points=generated.required_points or [interview.topic],
            reference_answer=generated.reference_answer,
            rubric={
                "question_angle": {
                    "key": question_angle.key,
                    "title": question_angle.title,
                    "prompt_hint": question_angle.prompt_hint,
                },
                "generation": {
                    "mode": generated.generation_mode,
                    "fallback_reason": generated.fallback_reason,
                    "prompt_version": QUESTION_PROMPT_VERSION,
                    "recent_question_cooldown_count": len(recent_questions),
                },
                "interview_policy": {
                    "next_action": policy.next_action,
                    "reason": policy.reason,
                    "target_topic": policy.target_topic,
                    "difficulty": policy.difficulty,
                    "deterministic_gate": policy.deterministic_gate,
                },
                "items": [
                    {
                        "criterion": "correctness",
                        "description": "回答是否准确覆盖核心概念和资料依据。",
                        "weight": 35,
                        "required_points": generated.required_points or [interview.topic],
                    },
                    {
                        "criterion": "completeness",
                        "description": "回答是否覆盖场景、边界和工程注意事项。",
                        "weight": 30,
                        "required_points": generated.required_points[:3],
                    },
                    {
                        "criterion": "reasoning",
                        "description": "回答是否有清晰推理链路和取舍说明。",
                        "weight": 20,
                        "required_points": [],
                    },
                    {
                        "criterion": "communication",
                        "description": "表达是否结构化、适合面试交流。",
                        "weight": 15,
                        "required_points": [],
                    },
                ],
            },
            prompt_version=QUESTION_PROMPT_VERSION,
            placeholder_feedback=None,
            created_at=datetime.now(UTC),
        )
        db.add(question)
        await db.flush()
        for position, chunk in enumerate(chunks[:2], start=1):
            db.add(
                QuestionReferenceModel(
                    id=uuid4(),
                    question_id=question.id,
                    chunk_id=chunk.chunk_id,
                    position=position,
                    created_at=datetime.now(UTC),
                )
            )
        await map_question_coverage(db, question_id=question.id, chunk_ids=citation_ids)
        if coverage_focus is not None:
            await self._ensure_question_coverage(
                db,
                question_id=question.id,
                knowledge_point_id=coverage_focus.point_id,
            )
        return question

    async def _generate_question_output(
        self,
        interview: InterviewSessionModel,
        sequence: int,
        question_type: QuestionType,
        question_angle: QuestionAngle,
        chunks: list[RetrievedChunk],
        prior_questions: list[str],
        recent_questions: list[str],
        coverage_focus: str | None,
        profile_focus: str | None,
        policy: InterviewPolicyDecision,
    ) -> InterviewQuestionOutput:
        fallback = InterviewQuestionOutput(
            question_text=self._question_text(interview, sequence, question_angle, chunks),
            reference_answer=self._reference_answer(chunks),
            required_points=[coverage_focus or profile_focus or interview.topic],
            generation_mode="deterministic_fallback",
            fallback_reason="llm_unavailable",
        )
        if self._llm is None:
            return fallback
        try:
            return await self._llm.generate_structured(
                operation="interview_question",
                messages=[
                    Message(
                        role="system",
                        content=(
                            "你是资深 AI Agent 面试官，正在帮助 Java 后端开发者转型。"
                            "请基于给定资料生成一道真实、有区分度、可追问的中文面试题。"
                            "题目必须贴合资料，不要编造资料外结论。"
                        ),
                    ),
                    Message(
                        role="user",
                        content=self._question_prompt(
                            interview,
                            sequence,
                            question_type,
                            question_angle,
                            chunks,
                            prior_questions,
                            recent_questions,
                            coverage_focus,
                            profile_focus,
                            policy,
                        ),
                    ),
                ],
                response_model=InterviewQuestionOutput,
                model_policy=ModelPolicy(model=self._default_model),
                trace_context=TraceContext(trace_id=str(uuid4()), operation="interview_question"),
            )
        except Exception as error:
            log_event(
                logging.WARNING,
                "interview_question.llm_fallback",
                error_type=type(error).__name__,
                fallback="deterministic_question",
                topic=interview.topic,
                sequence=sequence,
                candidate_count=len(chunks),
            )
            return fallback

    def _question_prompt(
        self,
        interview: InterviewSessionModel,
        sequence: int,
        question_type: QuestionType,
        question_angle: QuestionAngle,
        chunks: list[RetrievedChunk],
        prior_questions: list[str],
        recent_questions: list[str],
        coverage_focus: str | None,
        profile_focus: str | None = None,
        policy: InterviewPolicyDecision | None = None,
    ) -> str:
        context = []
        for index, chunk in enumerate(chunks[:3], start=1):
            context.append(
                "\n".join(
                    [
                        f"资料 {index}",
                        f"document: {chunk.document_title}",
                        f"heading: {' > '.join(chunk.heading_path)}",
                        f"content: {chunk.content[:1200]}",
                    ]
                )
            )
        type_hint = {
            QuestionType.CONCEPT: "概念理解题：考察核心概念、为什么需要、解决什么问题。",
            QuestionType.SCENARIO: "场景落地题：考察工程设计、数据流、异常处理和边界。",
            QuestionType.DESIGN: "设计复盘题：考察架构取舍、可观测性、成本和可量化效果。",
            QuestionType.DEBUGGING: "排障题：考察定位问题、验证假设和修复方案。",
        }[question_type]
        policy_block = (
            "\n".join(
                [
                    f"面试官策略动作：{policy.next_action}",
                    f"策略原因：{policy.reason}",
                    f"目标主题：{policy.target_topic}",
                    f"难度策略：{policy.difficulty}",
                    f"确定性边界：{policy.deterministic_gate}",
                ]
            )
            if policy is not None
            else "无"
        )
        return (
            f"主题：{interview.topic}\n"
            f"难度：{interview.difficulty}\n"
            f"题号：{sequence}/{interview.question_count}\n"
            f"题型要求：{type_hint}\n\n"
            f"本题考察角度：{question_angle.title}\n"
            f"角度要求：{question_angle.prompt_hint}\n"
            "题目必须体现该考察角度，避免只换说法但重复考同一个点。\n\n"
            f"覆盖保底考点：{coverage_focus or '无'}\n"
            "如果存在覆盖保底考点，题目必须优先围绕该考点展开，但仍需基于检索资料。\n\n"
            f"画像推荐考点：{profile_focus or '无'}\n"
            "如果存在画像推荐考点，题目需要围绕该薄弱点或专项点命题，不要只泛泛围绕主题出题。\n\n"
            "轻量面试官策略：\n"
            f"{policy_block}\n"
            "策略只用于指导出题角度，不能覆盖状态机、幂等和引用校验等确定性边界。\n\n"
            f"本轮已出题目：{prior_questions or '无'}\n"
            "不得重复已出题目的核心问法，应考察不同角度。\n\n"
            f"同知识库最近历史题目：{recent_questions or '无'}\n"
            "应主动避开最近历史题目的核心问法；如果必须考同一知识点，也要切换到不同场景、边界或排障角度。\n\n"
            "检索资料：\n"
            f"{chr(10).join(context) if context else '无'}\n\n"
            "请输出 JSON：question_text、reference_answer、required_points。"
        )

    async def _recent_knowledge_base_questions(
        self, db: AsyncSession, interview: InterviewSessionModel
    ) -> list[str]:
        return list((await db.scalars(self._recent_question_statement(interview))).all())

    def _recent_question_statement(self, interview: InterviewSessionModel):
        return (
            select(InterviewQuestionModel.question_text)
            .join(
                InterviewSessionModel,
                InterviewSessionModel.id == InterviewQuestionModel.session_id,
            )
            .where(
                InterviewSessionModel.knowledge_base_id == interview.knowledge_base_id,
                InterviewSessionModel.id != interview.id,
            )
            .order_by(InterviewQuestionModel.created_at.desc())
            .limit(RECENT_QUESTION_COOLDOWN_LIMIT)
        )

    def _question_policy(
        self,
        interview: InterviewSessionModel,
        *,
        sequence: int,
        coverage_focus: str | None,
        profile_focus: str | None,
        question_angle: QuestionAngle,
        recent_questions: list[str],
    ) -> InterviewPolicyDecision:
        if coverage_focus:
            return InterviewPolicyDecision(
                next_action="ask_coverage_gap_question",
                reason="当前知识库存在未覆盖知识点，本题优先用于查漏，避免画像只反映已考内容。",
                target_topic=coverage_focus,
                difficulty=str(interview.difficulty),
                deterministic_gate=(
                    "LLM 只生成题目，题目入库、引用校验和状态推进"
                    "由 InterviewService 控制。"
                ),
            )
        if profile_focus:
            return InterviewPolicyDecision(
                next_action="ask_profile_targeted_question",
                reason="本轮由能力画像或复习任务推荐进入，题目需要围绕画像薄弱点命题。",
                target_topic=profile_focus,
                difficulty=str(interview.difficulty),
                deterministic_gate=(
                    "画像只提供训练目标，题目生成、引用校验、状态推进仍由"
                    " InterviewService 控制。"
                ),
            )
        if sequence > 1 and recent_questions:
            return InterviewPolicyDecision(
                next_action="ask_cooldown_aware_question",
                reason="同知识库近期已经出现相似训练题，本题需要切换角度以提升题目多样性。",
                target_topic=f"{interview.topic} · {question_angle.title}",
                difficulty=str(interview.difficulty),
                deterministic_gate="历史题冷却由应用层计算，LLM 不能绕过相似度检测。",
            )
        return InterviewPolicyDecision(
            next_action="ask_planned_question",
            reason="按本轮主题、题型和考察角度生成题目，保持三题面试的结构化推进。",
            target_topic=f"{interview.topic} · {question_angle.title}",
            difficulty=str(interview.difficulty),
            deterministic_gate="状态迁移、幂等写入和 checkpoint 仍由确定性状态机负责。",
        )

    async def _coverage_gap_focus(
        self, db: AsyncSession, interview: InterviewSessionModel, *, sequence: int
    ) -> CoverageFocus | None:
        if sequence != self._coverage_gap_sequence(interview.question_count):
            return None
        point = await db.scalar(self._coverage_gap_focus_statement(interview.knowledge_base_id))
        if point is None:
            return None
        return CoverageFocus(point_id=point.id, title=point.title)

    def _coverage_gap_focus_statement(self, knowledge_base_id: UUID):
        covered_point_ids = select(QuestionCoverageModel.knowledge_point_id)
        source_count = func.count(KnowledgeCatalogSourceModel.id).label("source_count")
        return (
            select(KnowledgeCatalogPointModel)
            .join(
                KnowledgeCatalogSourceModel,
                KnowledgeCatalogSourceModel.knowledge_point_id == KnowledgeCatalogPointModel.id,
            )
            .where(
                KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id,
                KnowledgeCatalogPointModel.id.not_in(covered_point_ids),
            )
            .group_by(KnowledgeCatalogPointModel.id)
            .order_by(source_count.desc(), KnowledgeCatalogPointModel.title)
            .limit(1)
        )

    async def _ensure_question_coverage(
        self, db: AsyncSession, *, question_id: UUID, knowledge_point_id: UUID
    ) -> None:
        existing = await db.scalar(
            select(QuestionCoverageModel.id).where(
                QuestionCoverageModel.question_id == question_id,
                QuestionCoverageModel.knowledge_point_id == knowledge_point_id,
            )
        )
        if existing is not None:
            return
        db.add(
            QuestionCoverageModel(
                id=uuid4(),
                question_id=question_id,
                knowledge_point_id=knowledge_point_id,
                created_at=datetime.now(UTC),
            )
        )

    def _coverage_gap_sequence(self, question_count: int) -> int:
        return 2 if question_count >= 2 else 1

    def _question_search_text(
        self,
        interview: InterviewSessionModel,
        question_type: QuestionType,
        focus: str | None,
        question_angle: QuestionAngle | None = None,
    ) -> str:
        parts = [
            focus or "",
            interview.topic,
            self._question_type_search_hint(question_type),
        ]
        if question_angle is not None:
            parts.extend([question_angle.title, question_angle.search_hint])
        if focus:
            parts.extend(["专项训练", focus])
        return " ".join(part for part in parts if part)

    def _profile_focus_title(self, interview: InterviewSessionModel) -> str | None:
        return (
            interview.profile_subtopic_title
            or interview.profile_topic_title
            or (
                interview.topic
                if interview.profile_subtopic_key or interview.profile_topic_key
                else None
            )
        )

    def _question_angle(self, interview: InterviewSessionModel, sequence: int) -> QuestionAngle:
        offset = interview.id.int % len(QUESTION_ANGLES)
        return QUESTION_ANGLES[(offset + sequence - 1) % len(QUESTION_ANGLES)]

    def _question_type(self, sequence: int) -> QuestionType:
        types = (QuestionType.CONCEPT, QuestionType.SCENARIO, QuestionType.DESIGN)
        return types[(sequence - 1) % len(types)]

    def _question_type_search_hint(self, question_type: QuestionType) -> str:
        return {
            QuestionType.CONCEPT: "定义 原理 核心概念",
            QuestionType.SCENARIO: "工程落地 数据流 异常处理",
            QuestionType.DESIGN: "架构取舍 边界 可观测性",
            QuestionType.DEBUGGING: "故障定位 验证 修复",
        }[question_type]

    def _is_too_similar(self, question: str, prior_questions: list[str]) -> bool:
        current = self._question_terms(question)
        if not current:
            return False
        for prior in prior_questions:
            previous = self._question_terms(prior)
            union = current | previous
            if union and len(current & previous) / len(union) >= 0.72:
                return True
        return False

    def _question_terms(self, text: str) -> set[str]:
        terms = set(re.findall(r"[a-z0-9_]{2,}", text.lower()))
        for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
            terms.update(segment[index : index + 2] for index in range(len(segment) - 1))
        return terms

    def _required_points(self, question: InterviewQuestionModel) -> list[str]:
        raw_items = question.rubric.get("items", [])
        points: list[str] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                raw_points = item.get("required_points", [])
                if isinstance(raw_points, list):
                    points.extend(str(point) for point in raw_points if str(point).strip())
        return points or list(question.knowledge_points)

    def _contains_meaning(self, answer: str, point: str) -> bool:
        if point in answer:
            return True
        terms = self._question_terms(point)
        return bool(terms) and any(term in answer for term in terms)

    def _answer_has_substantive_signal(self, answer_text: str) -> bool:
        text = answer_text.strip()
        if len(text) < 80:
            return False
        uncertainty_markers = ("不知道", "不确定", "不会", "不清楚", "uncertain", "not sure")
        if any(marker in text.lower() or marker in text for marker in uncertainty_markers):
            return False
        engineering_markers = (
            "引用",
            "证据",
            "降级",
            "边界",
            "风险",
            "验证",
            "工程",
            "记录",
            "校验",
            "回归",
            "状态",
            "checkpoint",
            "幂等",
            "trace",
        )
        hit_count = sum(
            1 for marker in engineering_markers if marker in text.lower() or marker in text
        )
        return hit_count >= 3

    def _question_text(
        self,
        interview: InterviewSessionModel,
        sequence: int,
        question_angle: QuestionAngle,
        chunks: list[RetrievedChunk],
    ) -> str:
        question_type = self._question_type(sequence)
        context = interview.topic
        if chunks:
            heading = " > ".join(chunks[0].heading_path) or chunks[0].document_title
            context = f"{interview.topic}（参考资料：{heading}）"

        prefix = f"[{sequence}/{interview.question_count}]"
        angle = f"请从“{question_angle.title}”角度回答："
        if question_type == QuestionType.CONCEPT:
            return (
                f"{prefix} {angle}说明 {context} 的核心概念，并明确适用边界、"
                "易混淆点，以及哪些结论需要后续用资料验证。"
            )
        if question_type == QuestionType.SCENARIO:
            return (
                f"{prefix} {angle}如果你要把 {context} 落地到自己的 AI 面试助手项目里，"
                "你会如何设计数据流、关键组件和异常处理？"
            )
        return (
            f"{prefix} {angle}从面试官视角复盘 {context}：它最容易被追问的工程取舍、"
            "边界条件和可量化效果分别是什么？"
        )

    def _reference_answer(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "当前题目生成时没有检索到足够资料，请基于通用学习经验回答并标记不确定性。"
        return chunks[0].content[:800]

    async def _checkpoint(
        self, db: AsyncSession, state: InterviewWorkflowState
    ) -> WorkflowCheckpointModel:
        checkpoint = WorkflowCheckpointModel(
            id=uuid4(),
            session_id=state.session_id,
            thread_id=state.thread_id,
            node=state.current_node,
            state=state.checkpoint(),
            created_at=datetime.now(UTC),
        )
        db.add(checkpoint)
        return checkpoint

    def _trace_item(self, checkpoint: WorkflowCheckpointModel) -> WorkflowTraceItem:
        state = checkpoint.state
        spec = workflow_node_spec(checkpoint.node)
        input_summary, output_summary = checkpoint_summary(state)
        raw_error = state.get("error")
        error_message = raw_error if isinstance(raw_error, str) else None
        return WorkflowTraceItem(
            checkpoint_id=checkpoint.id,
            node=checkpoint.node,
            event=spec.event,
            label=spec.label,
            input_summary=input_summary,
            output_summary=output_summary,
            waiting_for_answer=bool(state.get("waiting_for_answer", False)),
            is_fallback=bool(state.get("fallback", False)),
            error_message=error_message,
            created_at=checkpoint.created_at,
        )

    def _state(
        self, interview: InterviewSessionModel, node: str, *, waiting: bool = False
    ) -> InterviewWorkflowState:
        return InterviewWorkflowState(
            session_id=interview.id,
            thread_id=interview.workflow_thread_id,
            current_node=node,
            current_question_index=interview.current_question_index,
            question_count=interview.question_count,
            waiting_for_answer=waiting,
        )

    async def _snapshot(
        self, db: AsyncSession, interview: InterviewSessionModel
    ) -> InterviewSnapshot:
        current_question = None
        current_follow_up = None
        if interview.status == InterviewStatus.WAITING_FOR_ANSWER:
            current_question = await db.scalar(
                select(InterviewQuestionModel).where(
                    InterviewQuestionModel.session_id == interview.id,
                    InterviewQuestionModel.sequence == interview.current_question_index + 1,
                )
            )
            if current_question is not None:
                current_follow_up = await db.scalar(
                    select(InterviewFollowUpModel).where(
                        InterviewFollowUpModel.question_id == current_question.id,
                        InterviewFollowUpModel.status == FollowUpStatus.PENDING,
                    )
                )
        answers = tuple(
            (
                await db.scalars(
                    select(UserAnswerModel)
                    .join(
                        InterviewQuestionModel,
                        InterviewQuestionModel.id == UserAnswerModel.question_id,
                    )
                    .where(InterviewQuestionModel.session_id == interview.id)
                    .order_by(UserAnswerModel.submitted_at)
                )
            ).all()
        )
        reference_ids: tuple[UUID, ...] = ()
        if current_question is not None:
            reference_ids = tuple(
                (
                    await db.scalars(
                        select(QuestionReferenceModel.chunk_id)
                        .where(QuestionReferenceModel.question_id == current_question.id)
                        .order_by(QuestionReferenceModel.position)
                    )
                ).all()
            )
        return InterviewSnapshot(
            session=interview,
            current_question=current_question,
            current_follow_up=current_follow_up,
            current_reference_chunk_ids=reference_ids,
            answers=answers,
        )

    async def _get_session(self, db: AsyncSession, session_id: UUID) -> InterviewSessionModel:
        interview = await db.get(InterviewSessionModel, session_id)
        if interview is None:
            raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)
        return interview

    async def _get_session_for_update(
        self, db: AsyncSession, session_id: UUID
    ) -> InterviewSessionModel:
        interview = await db.scalar(self._session_for_update_statement(session_id))
        if interview is None:
            raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)
        return interview

    def _session_for_update_statement(self, session_id: UUID):
        return (
            select(InterviewSessionModel)
            .where(InterviewSessionModel.id == session_id)
            .with_for_update()
        )

    async def _get_question(self, db: AsyncSession, question_id: UUID) -> InterviewQuestionModel:
        question = await db.get(InterviewQuestionModel, question_id)
        if question is None:
            raise AppError("QUESTION_NOT_FOUND", "Interview question was not found.", 404)
        return question

    async def _get_follow_up(
        self, db: AsyncSession, follow_up_id: UUID
    ) -> InterviewFollowUpModel:
        follow_up = await db.get(InterviewFollowUpModel, follow_up_id)
        if follow_up is None:
            raise AppError("FOLLOW_UP_NOT_FOUND", "Interview follow-up was not found.", 404)
        return follow_up
