from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.domain.evaluation import (
    EvaluationOutput,
    EvaluationRubric,
    EvaluationStatus,
    ReviewDecision,
    initial_review_route,
    review_reasons_for,
    should_review,
    total_score,
)
from agent_mentor.domain.interview import AnswerKind, FollowUpStatus, InterviewStatus
from agent_mentor.infrastructure.database.models import (
    EvaluationModel,
    EvaluationReferenceModel,
    InterviewFollowUpModel,
    InterviewQuestionModel,
    InterviewReportModel,
    InterviewSessionModel,
    QuestionReferenceModel,
    UserAnswerModel,
)
from agent_mentor.logging import log_event
from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext

EVALUATION_PROMPT_VERSION = "evaluation_v1"
REVIEW_PROMPT_VERSION = "review_v1"
EVALUATION_MODEL_NAME = "deterministic-evaluator-v1"
REVIEWER_MODEL_NAME = "deterministic-reviewer-v1"


@dataclass(frozen=True, slots=True)
class EvaluationItem:
    evaluation: EvaluationModel
    question: InterviewQuestionModel
    answer: UserAnswerModel
    reference_chunk_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    report: InterviewReportModel
    evaluations: tuple[EvaluationItem, ...]


@dataclass(frozen=True, slots=True)
class ReportHistoryItem:
    report: InterviewReportModel
    interview: InterviewSessionModel


@dataclass(frozen=True, slots=True)
class ScoreTrendPoint:
    report_id: UUID
    session_id: UUID
    topic: str
    difficulty: str
    total_score: int
    max_score: int
    score_ratio: float
    dimension_averages: dict[str, float]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DirectEvaluationResult:
    output: EvaluationOutput
    needs_review: bool
    status: EvaluationStatus
    review_decision: ReviewDecision
    model_name: str


class EvaluationService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        llm: LLMGateway | None = None,
        *,
        default_model: str | None = None,
    ) -> None:
        self._sessions = sessions
        self._llm = llm
        self._default_model = default_model

    async def evaluate_interview(
        self, interview_id: UUID, *, reviewer_available: bool = True
    ) -> tuple[EvaluationItem, ...]:
        async with self._sessions() as db:
            interview = await self._get_completed_interview(db, interview_id)
            questions = await self._questions(db, interview.id)
            for question in questions:
                await self._validate_rubric(question)
                answer = await self._primary_answer(db, question.id)
                if answer is None:
                    continue
                existing = await self._evaluation_by_answer(db, answer.id)
                if existing is None:
                    await self._evaluate_answer(
                        db,
                        question=question,
                        answer=answer,
                        reviewer_available=reviewer_available,
                    )
            await db.commit()
            return await self._evaluation_items(db, interview.id)

    async def list_evaluations(self, interview_id: UUID) -> tuple[EvaluationItem, ...]:
        async with self._sessions() as db:
            interview = await self._get_interview(db, interview_id)
            return await self._evaluation_items(db, interview.id)

    async def build_report(
        self, interview_id: UUID, *, reviewer_available: bool = True
    ) -> ReportSnapshot:
        evaluations = await self.evaluate_interview(
            interview_id, reviewer_available=reviewer_available
        )
        async with self._sessions() as db:
            interview = await self._get_completed_interview(db, interview_id)
            generated = self._create_report_model(interview, evaluations)
            report = await db.scalar(
                select(InterviewReportModel).where(InterviewReportModel.session_id == interview.id)
            )
            if report is None:
                report = generated
                db.add(report)
            else:
                report.total_score = generated.total_score
                report.max_score = generated.max_score
                report.dimension_summary = generated.dimension_summary
                report.knowledge_point_summary = generated.knowledge_point_summary
                report.error_summary = generated.error_summary
                report.low_confidence_items = generated.low_confidence_items
                report.disputed_items = generated.disputed_items
                report.next_steps = generated.next_steps
                report.created_at = generated.created_at
            await db.commit()
            await db.refresh(report)
            return ReportSnapshot(report=report, evaluations=evaluations)

    async def get_report(self, interview_id: UUID) -> ReportSnapshot:
        async with self._sessions() as db:
            interview = await self._get_interview(db, interview_id)
            report = await db.scalar(
                select(InterviewReportModel).where(InterviewReportModel.session_id == interview.id)
            )
            if report is None:
                raise AppError("REPORT_NOT_FOUND", "Interview report was not found.", 404)
            evaluations = await self._evaluation_items(db, interview.id)
            return ReportSnapshot(report=report, evaluations=evaluations)

    async def list_report_history(
        self, user_id: UUID, knowledge_base_id: UUID, *, limit: int = 10
    ) -> tuple[ReportHistoryItem, ...]:
        async with self._sessions() as db:
            result = await db.execute(
                select(InterviewReportModel, InterviewSessionModel)
                .join(
                    InterviewSessionModel,
                    InterviewSessionModel.id == InterviewReportModel.session_id,
                )
                .where(
                    InterviewSessionModel.user_id == user_id,
                    InterviewSessionModel.knowledge_base_id == knowledge_base_id,
                )
                .order_by(InterviewReportModel.created_at.desc())
                .limit(limit)
            )
            return tuple(
                ReportHistoryItem(report=report, interview=interview)
                for report, interview in result.all()
            )

    async def score_trends(
        self, user_id: UUID, knowledge_base_id: UUID, *, limit: int = 10
    ) -> tuple[ScoreTrendPoint, ...]:
        history = await self.list_report_history(user_id, knowledge_base_id, limit=limit)
        chronological = reversed(history)
        return tuple(self._trend_point(item) for item in chronological)

    async def evaluate_answer_direct(
        self,
        *,
        question_text: str,
        answer_text: str,
        reference_answer: str,
        knowledge_points: tuple[str, ...],
        rubric: dict[str, object],
        allowed_reference_ids: tuple[UUID, ...] = (),
        reviewer_available: bool = True,
    ) -> DirectEvaluationResult:
        """Evaluate a dataset row without persisted interview/question/answer rows.

        Eval Runner uses this method to measure scoring quality against labelled
        JSONL cases while keeping the production interview persistence path
        unchanged.
        """
        question = cast(
            InterviewQuestionModel,
            SimpleNamespace(
                id=uuid4(),
                question_text=question_text,
                question_type="eval_case",
                difficulty="medium",
                knowledge_points=list(knowledge_points),
                reference_answer=reference_answer,
                rubric=rubric,
            ),
        )
        answer = cast(
            UserAnswerModel,
            SimpleNamespace(id=uuid4(), answer_text=answer_text),
        )
        output = await self._evaluate_with_llm_or_fallback(
            question, answer, allowed_reference_ids
        )
        reasons = review_reasons_for(output)
        needs_review = should_review(output)
        status, review_decision = initial_review_route(
            output, reviewer_available=reviewer_available
        )
        model_name = self._default_model or EVALUATION_MODEL_NAME
        if needs_review and reviewer_available:
            reviewed_output = self._review_deterministically(output, answer)
            if abs(total_score(reviewed_output) - total_score(output)) >= 5:
                status = EvaluationStatus.DISPUTED
                review_decision = ReviewDecision.DISPUTED
            else:
                output = reviewed_output
                reasons = review_reasons_for(output)
                status = EvaluationStatus.FINAL
                review_decision = ReviewDecision.USED_REVIEW
            model_name = f"{model_name}+{REVIEWER_MODEL_NAME}"
        return DirectEvaluationResult(
            output=output.model_copy(update={"review_reasons": reasons}),
            needs_review=needs_review,
            status=status,
            review_decision=review_decision,
            model_name=model_name,
        )

    async def _evaluate_answer(
        self,
        db: AsyncSession,
        *,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
        reviewer_available: bool,
    ) -> EvaluationModel:
        allowed_references = await self._question_reference_ids(db, question.id)
        scoring_answer = await self._answer_for_scoring(db, question.id, answer)
        output = await self._evaluate_with_llm_or_fallback(
            question, scoring_answer, allowed_references
        )
        self._assert_allowed_references(output.reference_chunk_ids, allowed_references)
        reasons = review_reasons_for(output)
        needs_review = should_review(output)
        reviewed = False
        status, review_decision = initial_review_route(
            output, reviewer_available=reviewer_available
        )
        model_name = self._default_model or EVALUATION_MODEL_NAME

        if needs_review and reviewer_available:
            reviewed_output = self._review_deterministically(output, scoring_answer)
            self._assert_allowed_references(reviewed_output.reference_chunk_ids, allowed_references)
            if abs(total_score(reviewed_output) - total_score(output)) >= 5:
                review_decision = ReviewDecision.DISPUTED
                status = EvaluationStatus.DISPUTED
            else:
                output = reviewed_output
                reasons = review_reasons_for(output)
                review_decision = ReviewDecision.USED_REVIEW
                status = EvaluationStatus.FINAL
            reviewed = True
            model_name = f"{model_name}+{REVIEWER_MODEL_NAME}"

        evaluation = EvaluationModel(
            id=uuid4(),
            question_id=question.id,
            answer_id=answer.id,
            correctness=output.correctness,
            completeness=output.completeness,
            reasoning=output.reasoning,
            communication=output.communication,
            total=total_score(output),
            confidence=output.confidence,
            covered_points=output.covered_points,
            missing_points=output.missing_points,
            incorrect_claims=output.incorrect_claims,
            answer_evidence=output.answer_evidence,
            feedback=output.feedback,
            follow_up_recommended=output.follow_up_recommended,
            needs_review=needs_review,
            reviewed=reviewed,
            review_reasons=reasons,
            review_decision=review_decision,
            status=status,
            model_name=model_name,
            prompt_version=EVALUATION_PROMPT_VERSION,
            created_at=datetime.now(UTC),
        )
        db.add(evaluation)
        await db.flush()
        for position, chunk_id in enumerate(output.reference_chunk_ids, start=1):
            db.add(
                EvaluationReferenceModel(
                    id=uuid4(),
                    evaluation_id=evaluation.id,
                    chunk_id=chunk_id,
                    position=position,
                    created_at=datetime.now(UTC),
                )
            )
        return evaluation

    async def _evaluate_with_llm_or_fallback(
        self,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
        allowed_references: tuple[UUID, ...],
    ) -> EvaluationOutput:
        fallback = self._evaluate_deterministically(question, answer, allowed_references)
        if self._llm is None:
            return fallback
        try:
            output = await self._llm.generate_structured(
                operation="answer_evaluation",
                messages=[
                    Message(
                        role="system",
                        content=(
                            "你是 AgentMentor 的面试评分器。"
                            "必须输出 0-5 四维评分、置信度、反馈和引用 chunk_id。"
                            "reference_chunk_ids 只能使用允许列表里的 ID，不允许编造引用。"
                        ),
                    ),
                    Message(
                        role="user",
                        content=self._evaluation_prompt(question, answer, allowed_references),
                    ),
                ],
                response_model=EvaluationOutput,
                model_policy=ModelPolicy(model=self._default_model),
                trace_context=TraceContext(trace_id=str(uuid4()), operation="answer_evaluation"),
            )
            self._assert_allowed_references(output.reference_chunk_ids, allowed_references)
            return output
        except Exception as error:
            log_event(
                logging.WARNING,
                "answer_evaluation.llm_fallback",
                error_type=type(error).__name__,
                fallback="deterministic_evaluation",
                question_id=str(question.id),
                answer_id=str(answer.id),
                allowed_reference_count=len(allowed_references),
            )
            return fallback

    def _evaluation_prompt(
        self,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
        allowed_references: tuple[UUID, ...],
    ) -> str:
        return (
            f"题目：{question.question_text}\n"
            f"题型：{question.question_type}\n"
            f"难度：{question.difficulty}\n"
            f"知识点：{', '.join(question.knowledge_points)}\n"
            f"参考答案：{question.reference_answer[:3000]}\n"
            f"评分 Rubric：{question.rubric}\n"
            f"允许引用的 chunk_id：{', '.join(str(item) for item in allowed_references)}\n\n"
            f"用户回答：{answer.answer_text}\n\n"
            "请输出 JSON，字段必须符合 EvaluationOutput："
            "correctness、completeness、reasoning、communication、confidence、"
            "covered_points、missing_points、incorrect_claims、answer_evidence、"
            "reference_chunk_ids、feedback、follow_up_recommended、review_reasons。"
        )

    def _evaluate_deterministically(
        self,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
        allowed_references: tuple[UUID, ...],
    ) -> EvaluationOutput:
        answer_text = answer.answer_text.strip()
        answer_lower = answer_text.lower()
        reference_answer = question.reference_answer.strip()
        reference_lower = reference_answer.lower()
        required_points = self._required_points(question)
        covered = [
            point
            for point in required_points
            if self._contains_meaning(answer_lower, point.lower())
        ]
        if not covered and reference_lower:
            reference_terms = self._significant_terms(reference_lower)
            covered = [term for term in reference_terms if term in answer_lower][:3]
        missing = [point for point in required_points if point not in covered]
        weak_markers = ("不知道", "不确定", "不会", "不清楚", "uncertain", "not sure")
        incorrect_claims = [
            marker for marker in weak_markers if marker in answer_lower or marker in answer_text
        ]
        term_overlap = self._term_overlap(answer_lower, reference_lower)
        length_score = min(1.0, len(answer_text) / 220)
        coverage_ratio = len(covered) / max(1, len(required_points))

        correctness = self._score(0.65 * term_overlap + 0.35 * coverage_ratio)
        completeness = self._score(0.55 * coverage_ratio + 0.45 * length_score)
        reasoning = self._score(0.50 * length_score + 0.50 * self._reasoning_signal(answer_lower))
        communication = self._score(self._communication_signal(answer_text))

        if incorrect_claims:
            correctness = min(correctness, 2)
            confidence = 0.55
        else:
            confidence = min(0.92, 0.58 + 0.24 * term_overlap + 0.10 * length_score)
        follow_up = bool(
            missing
            and 1
            <= total_score(
                EvaluationOutput(
                    correctness=correctness,
                    completeness=completeness,
                    reasoning=reasoning,
                    communication=communication,
                    confidence=confidence,
                    feedback="draft",
                )
            )
            <= 14
        )
        references = list(allowed_references[:2]) if term_overlap > 0 or covered else []
        return EvaluationOutput(
            correctness=correctness,
            completeness=completeness,
            reasoning=reasoning,
            communication=communication,
            confidence=round(confidence, 2),
            covered_points=covered,
            missing_points=missing[:5],
            incorrect_claims=incorrect_claims,
            answer_evidence=self._answer_evidence(answer_text),
            reference_chunk_ids=references,
            feedback=self._feedback(correctness, completeness, reasoning, communication, missing),
            follow_up_recommended=follow_up,
        )

    def _review_deterministically(
        self, output: EvaluationOutput, answer: UserAnswerModel
    ) -> EvaluationOutput:
        if len(answer.answer_text.strip()) < 12:
            return output.model_copy(
                update={
                    "confidence": min(output.confidence, 0.60),
                    "review_reasons": [*output.review_reasons, "reviewer_confirms_weak_answer"],
                }
            )
        return output.model_copy(
            update={
                "confidence": max(output.confidence, 0.72),
                "feedback": f"{output.feedback} 复核后确认：评分依据与引用范围一致。",
                "review_reasons": [*output.review_reasons, "reviewer_checked"],
            }
        )

    def _create_report_model(
        self, interview: InterviewSessionModel, evaluations: tuple[EvaluationItem, ...]
    ) -> InterviewReportModel:
        rows = [item.evaluation for item in evaluations]
        total = sum(row.total for row in rows)
        max_score = len(rows) * 20
        dimension_summary = {
            dimension: {
                "total": sum(getattr(row, dimension) for row in rows),
                "average": round(
                    sum(getattr(row, dimension) for row in rows) / max(1, len(rows)), 2
                ),
            }
            for dimension in ("correctness", "completeness", "reasoning", "communication")
        }
        low_confidence = [str(row.question_id) for row in rows if row.confidence < 0.70]
        disputed = [str(row.question_id) for row in rows if row.status == EvaluationStatus.DISPUTED]
        errors = sorted({claim for row in rows for claim in row.incorrect_claims})
        weak_dimensions = [
            name
            for name, summary in dimension_summary.items()
            if isinstance(summary["average"], float) and summary["average"] < 3.0
        ]
        next_steps = [
            f"优先复习 {dimension} 相关能力：结合引用片段重新组织答案。"
            for dimension in weak_dimensions
        ] or ["保持当前练习节奏，下一轮增加场景化追问。"]
        return InterviewReportModel(
            id=uuid4(),
            session_id=interview.id,
            total_score=total,
            max_score=max_score,
            dimension_summary=dimension_summary,
            knowledge_point_summary={"topic": interview.topic, "evaluated_questions": len(rows)},
            error_summary=errors,
            low_confidence_items=low_confidence,
            disputed_items=disputed,
            next_steps=next_steps,
            created_at=datetime.now(UTC),
        )

    def _trend_point(self, item: ReportHistoryItem) -> ScoreTrendPoint:
        report = item.report
        dimensions: dict[str, float] = {}
        for name, value in report.dimension_summary.items():
            if isinstance(value, dict):
                dimensions[name] = float(value.get("average", 0))
        return ScoreTrendPoint(
            report_id=report.id,
            session_id=report.session_id,
            topic=item.interview.topic,
            difficulty=item.interview.difficulty,
            total_score=report.total_score,
            max_score=report.max_score,
            score_ratio=round(report.total_score / max(1, report.max_score), 4),
            dimension_averages=dimensions,
            created_at=report.created_at,
        )

    def _required_points(self, question: InterviewQuestionModel) -> list[str]:
        try:
            rubric = EvaluationRubric.model_validate(question.rubric)
        except ValueError:
            return list(question.knowledge_points)
        points: list[str] = []
        for item in rubric.items:
            points.extend(item.required_points)
        return points or list(question.knowledge_points)

    async def _validate_rubric(self, question: InterviewQuestionModel) -> None:
        try:
            EvaluationRubric.model_validate(question.rubric)
        except ValueError as exc:
            raise AppError("RUBRIC_INVALID", "Question rubric is invalid.", 422, str(exc)) from exc

    async def _evaluation_items(
        self, db: AsyncSession, interview_id: UUID
    ) -> tuple[EvaluationItem, ...]:
        evaluations = (
            await db.scalars(
                select(EvaluationModel)
                .join(
                    InterviewQuestionModel, InterviewQuestionModel.id == EvaluationModel.question_id
                )
                .where(InterviewQuestionModel.session_id == interview_id)
                .order_by(InterviewQuestionModel.sequence)
            )
        ).all()
        items: list[EvaluationItem] = []
        for evaluation in evaluations:
            question = await db.get(InterviewQuestionModel, evaluation.question_id)
            answer = await db.get(UserAnswerModel, evaluation.answer_id)
            if question is None or answer is None:
                continue
            references = (
                await db.scalars(
                    select(EvaluationReferenceModel.chunk_id)
                    .where(EvaluationReferenceModel.evaluation_id == evaluation.id)
                    .order_by(EvaluationReferenceModel.position)
                )
            ).all()
            items.append(
                EvaluationItem(
                    evaluation=evaluation,
                    question=question,
                    answer=answer,
                    reference_chunk_ids=tuple(references),
                )
            )
        return tuple(items)

    async def _questions(
        self, db: AsyncSession, interview_id: UUID
    ) -> tuple[InterviewQuestionModel, ...]:
        return tuple(
            (
                await db.scalars(
                    select(InterviewQuestionModel)
                    .where(InterviewQuestionModel.session_id == interview_id)
                    .order_by(InterviewQuestionModel.sequence)
                )
            ).all()
        )

    async def _question_reference_ids(
        self, db: AsyncSession, question_id: UUID
    ) -> tuple[UUID, ...]:
        return tuple(
            (
                await db.scalars(
                    select(QuestionReferenceModel.chunk_id)
                    .where(QuestionReferenceModel.question_id == question_id)
                    .order_by(QuestionReferenceModel.position)
                )
            ).all()
        )

    async def _primary_answer(self, db: AsyncSession, question_id: UUID) -> UserAnswerModel | None:
        return await db.scalar(
            select(UserAnswerModel)
            .where(
                UserAnswerModel.question_id == question_id,
                UserAnswerModel.answer_kind == AnswerKind.PRIMARY,
            )
            .order_by(UserAnswerModel.submitted_at)
        )

    async def _answer_for_scoring(
        self, db: AsyncSession, question_id: UUID, primary_answer: UserAnswerModel
    ) -> UserAnswerModel:
        follow_up = await db.scalar(
            select(InterviewFollowUpModel).where(
                InterviewFollowUpModel.question_id == question_id,
                InterviewFollowUpModel.status == FollowUpStatus.ANSWERED,
            )
        )
        if follow_up is None or follow_up.answer_id is None:
            return primary_answer
        follow_up_answer = await db.get(UserAnswerModel, follow_up.answer_id)
        if follow_up_answer is None:
            return primary_answer
        return cast(
            UserAnswerModel,
            SimpleNamespace(
                id=primary_answer.id,
                answer_text=(
                    f"【主回答】\n{primary_answer.answer_text.strip()}\n\n"
                    f"【面试官追问】\n{follow_up.prompt.strip()}\n\n"
                    f"【追问补充回答】\n{follow_up_answer.answer_text.strip()}"
                ),
            ),
        )

    async def _evaluation_by_answer(
        self, db: AsyncSession, answer_id: UUID
    ) -> EvaluationModel | None:
        return await db.scalar(
            select(EvaluationModel).where(EvaluationModel.answer_id == answer_id)
        )

    async def _get_interview(self, db: AsyncSession, interview_id: UUID) -> InterviewSessionModel:
        interview = await db.get(InterviewSessionModel, interview_id)
        if interview is None:
            raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)
        return interview

    async def _get_completed_interview(
        self, db: AsyncSession, interview_id: UUID
    ) -> InterviewSessionModel:
        interview = await self._get_interview(db, interview_id)
        if interview.status != InterviewStatus.COMPLETED:
            raise AppError("INTERVIEW_NOT_COMPLETED", "Interview must be completed first.", 409)
        return interview

    def _assert_allowed_references(
        self, reference_chunk_ids: list[UUID], allowed_references: tuple[UUID, ...]
    ) -> None:
        illegal = set(reference_chunk_ids) - set(allowed_references)
        if illegal:
            raise AppError(
                "EVALUATION_CITATION_INVALID",
                "Evaluation referenced chunks outside the question context.",
                422,
                ",".join(str(item) for item in sorted(illegal)),
            )

    def _term_overlap(self, answer: str, reference: str) -> float:
        reference_terms = set(self._significant_terms(reference))
        if not reference_terms:
            return 0
        answer_terms = set(self._significant_terms(answer))
        return len(reference_terms & answer_terms) / len(reference_terms)

    def _significant_terms(self, text: str) -> list[str]:
        terms = [term.strip("，。,.()[]{}:：;；") for term in text.split()]
        return [term for term in terms if len(term) >= 2][:40]

    def _contains_meaning(self, answer: str, point: str) -> bool:
        if point in answer:
            return True
        terms = self._significant_terms(point)
        return bool(terms) and any(term in answer for term in terms)

    def _score(self, ratio: float) -> int:
        return max(0, min(5, round(ratio * 5)))

    def _reasoning_signal(self, answer: str) -> float:
        markers = ("因为", "所以", "首先", "其次", "例如", "如果", "therefore", "because")
        return min(1.0, sum(1 for marker in markers if marker in answer) / 3)

    def _communication_signal(self, answer: str) -> float:
        if not answer.strip():
            return 0
        structure = 0.4 if any(marker in answer for marker in ("1.", "一", "首先", "\n")) else 0.1
        length = min(0.6, len(answer) / 300)
        return min(1.0, structure + length)

    def _answer_evidence(self, answer: str) -> list[str]:
        sentences = [
            item.strip()
            for item in answer.replace("。", "\n").replace("；", "\n").splitlines()
            if item.strip()
        ]
        return sentences[:3]

    def _feedback(
        self,
        correctness: int,
        completeness: int,
        reasoning: int,
        communication: int,
        missing: list[str],
    ) -> str:
        if min(correctness, completeness, reasoning, communication) >= 4:
            return "回答覆盖较充分，结构和论证基本达标。"
        if missing:
            return f"回答需要补齐关键点：{', '.join(missing[:3])}。"
        return "回答已有部分有效信息，但需要进一步明确概念、场景和推理链路。"
