from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.domain.interview import (
    AnswerKind,
    Difficulty,
    InterviewStatus,
    QuestionType,
    assert_transition,
)
from agent_mentor.infrastructure.database.models import (
    InterviewQuestionModel,
    InterviewSessionModel,
    QuestionReferenceModel,
    UserAnswerModel,
    WorkflowCheckpointModel,
)
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
    finish_interview,
    generate_question,
    load_profile,
    persist_answer,
    plan_interview,
    wait_for_answer,
)

QUESTION_PROMPT_VERSION = "interview_question_v1"


@dataclass(frozen=True, slots=True)
class InterviewSnapshot:
    session: InterviewSessionModel
    current_question: InterviewQuestionModel | None
    current_reference_chunk_ids: tuple[UUID, ...]
    answers: tuple[UserAnswerModel, ...]


class InterviewQuestionOutput(BaseModel):
    question_text: str = Field(min_length=1, max_length=1200)
    reference_answer: str = Field(min_length=1, max_length=4000)
    required_points: list[str] = Field(default_factory=list, max_length=8)


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

    async def submit_answer(
        self,
        *,
        session_id: UUID,
        question_id: UUID,
        answer_text: str,
        idempotency_key: str,
    ) -> InterviewSnapshot:
        async with self._sessions() as db:
            interview = await self._get_session(db, session_id)
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

            if interview.status != InterviewStatus.WAITING_FOR_ANSWER:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Interview is not waiting for an answer.", 409
                )
            if question.sequence != interview.current_question_index + 1:
                raise AppError(
                    "WORKFLOW_STATE_CONFLICT", "Question is not the current question.", 409
                )

            db.add(
                UserAnswerModel(
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

            if interview.current_question_index + 1 >= interview.question_count:
                assert_transition(interview.status, InterviewStatus.COMPLETED)
                interview.current_question_index = interview.question_count
                interview.status = InterviewStatus.COMPLETED
                interview.completed_at = datetime.now(UTC)
                interview.updated_at = datetime.now(UTC)
                await self._checkpoint(
                    db, finish_interview(self._state(interview, "finish_interview"))
                )
            else:
                next_state = advance_question(self._state(interview, "advance_question"))
                interview.current_question_index = next_state.current_question_index
                interview.updated_at = datetime.now(UTC)
                await self._create_question(
                    db, interview, sequence=interview.current_question_index + 1
                )
                await self._checkpoint(db, wait_for_answer(next_state))

            await db.commit()
            await db.refresh(interview)
            return await self._snapshot(db, interview)

    async def events(self, session_id: UUID) -> AsyncIterator[dict[str, object]]:
        snapshot = await self.get(session_id)
        yield {
            "event": "workflow.state",
            "data": {
                "session_id": str(snapshot.session.id),
                "status": str(snapshot.session.status),
                "current_question_index": snapshot.session.current_question_index,
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
        query_text = f"{interview.topic} {interview.difficulty} interview question {sequence}"
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
        question_type = self._question_type(sequence)
        generated = await self._generate_question_output(interview, sequence, question_type, chunks)
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
        return question

    async def _generate_question_output(
        self,
        interview: InterviewSessionModel,
        sequence: int,
        question_type: QuestionType,
        chunks: list[RetrievedChunk],
    ) -> InterviewQuestionOutput:
        fallback = InterviewQuestionOutput(
            question_text=self._question_text(interview, sequence, chunks),
            reference_answer=self._reference_answer(chunks),
            required_points=[interview.topic],
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
                        content=self._question_prompt(interview, sequence, question_type, chunks),
                    ),
                ],
                response_model=InterviewQuestionOutput,
                model_policy=ModelPolicy(model=self._default_model),
                trace_context=TraceContext(trace_id=str(uuid4()), operation="interview_question"),
            )
        except Exception:
            return fallback

    def _question_prompt(
        self,
        interview: InterviewSessionModel,
        sequence: int,
        question_type: QuestionType,
        chunks: list[RetrievedChunk],
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
        return (
            f"主题：{interview.topic}\n"
            f"难度：{interview.difficulty}\n"
            f"题号：{sequence}/{interview.question_count}\n"
            f"题型要求：{type_hint}\n\n"
            "检索资料：\n"
            f"{chr(10).join(context) if context else '无'}\n\n"
            "请输出 JSON：question_text、reference_answer、required_points。"
        )

    def _question_type(self, sequence: int) -> QuestionType:
        types = (QuestionType.CONCEPT, QuestionType.SCENARIO, QuestionType.DESIGN)
        return types[(sequence - 1) % len(types)]

    def _question_text(
        self, interview: InterviewSessionModel, sequence: int, chunks: list[RetrievedChunk]
    ) -> str:
        question_type = self._question_type(sequence)
        context = interview.topic
        if chunks:
            heading = " > ".join(chunks[0].heading_path) or chunks[0].document_title
            context = f"{interview.topic}（参考资料：{heading}）"

        prefix = f"[{sequence}/{interview.question_count}]"
        if question_type == QuestionType.CONCEPT:
            return f"{prefix} 请说明 {context} 的核心概念，并明确哪些结论需要后续用资料验证。"
        if question_type == QuestionType.SCENARIO:
            return (
                f"{prefix} 如果你要把 {context} 落地到自己的 AI 面试助手项目里，"
                "你会如何设计数据流、关键组件和异常处理？"
            )
        return (
            f"{prefix} 请从面试官视角复盘 {context}：它最容易被追问的工程取舍、"
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
        if interview.status == InterviewStatus.WAITING_FOR_ANSWER:
            current_question = await db.scalar(
                select(InterviewQuestionModel).where(
                    InterviewQuestionModel.session_id == interview.id,
                    InterviewQuestionModel.sequence == interview.current_question_index + 1,
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
            current_reference_chunk_ids=reference_ids,
            answers=answers,
        )

    async def _get_session(self, db: AsyncSession, session_id: UUID) -> InterviewSessionModel:
        interview = await db.get(InterviewSessionModel, session_id)
        if interview is None:
            raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)
        return interview

    async def _get_question(self, db: AsyncSession, question_id: UUID) -> InterviewQuestionModel:
        question = await db.get(InterviewQuestionModel, question_id)
        if question is None:
            raise AppError("QUESTION_NOT_FOUND", "Interview question was not found.", 404)
        return question
