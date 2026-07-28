from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.domain.interview import InterviewStatus
from agent_mentor.domain.knowledge import DocumentStatus
from agent_mentor.infrastructure.database.models import (
    AbilityProfileModel,
    InterviewReportModel,
    InterviewSessionModel,
    KnowledgeBaseModel,
    SourceDocumentModel,
    WorkflowCheckpointModel,
)


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    key: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class DemoReadiness:
    score: int
    status: str
    checks: tuple[ReadinessCheck, ...]
    next_action: str


class DemoReadinessService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def inspect(self) -> DemoReadiness:
        async with self._sessions() as db:
            knowledge_base_count = await self._count(
                db,
                select(func.count(KnowledgeBaseModel.id)).where(
                    KnowledgeBaseModel.user_id == DEFAULT_USER_ID
                ),
            )
            ready_document_count = await self._count(
                db,
                select(func.count(SourceDocumentModel.id))
                .join(
                    KnowledgeBaseModel,
                    KnowledgeBaseModel.id == SourceDocumentModel.knowledge_base_id,
                )
                .where(
                    KnowledgeBaseModel.user_id == DEFAULT_USER_ID,
                    SourceDocumentModel.status == DocumentStatus.READY,
                    SourceDocumentModel.is_active.is_(True),
                ),
            )
            completed_interview_count = await self._count(
                db,
                select(func.count(InterviewSessionModel.id)).where(
                    InterviewSessionModel.user_id == DEFAULT_USER_ID,
                    InterviewSessionModel.status == InterviewStatus.COMPLETED,
                ),
            )
            report_count = await self._count(
                db,
                select(func.count(InterviewReportModel.id))
                .join(
                    InterviewSessionModel,
                    InterviewSessionModel.id == InterviewReportModel.session_id,
                )
                .where(InterviewSessionModel.user_id == DEFAULT_USER_ID),
            )
            profile_count = await self._count(
                db,
                select(func.count(AbilityProfileModel.id)).where(
                    AbilityProfileModel.user_id == DEFAULT_USER_ID
                ),
            )
            checkpoint_count = await self._count(
                db,
                select(func.count(WorkflowCheckpointModel.id))
                .join(
                    InterviewSessionModel,
                    InterviewSessionModel.id == WorkflowCheckpointModel.session_id,
                )
                .where(InterviewSessionModel.user_id == DEFAULT_USER_ID),
            )

        checks = (
            ReadinessCheck(
                "knowledge_base",
                "知识库",
                knowledge_base_count > 0,
                f"已创建 {knowledge_base_count} 个知识库",
            ),
            ReadinessCheck(
                "ready_documents",
                "可检索资料",
                ready_document_count > 0,
                f"READY 文档 {ready_document_count} 份",
            ),
            ReadinessCheck(
                "workflow_trace",
                "工作流轨迹",
                checkpoint_count > 0,
                f"checkpoint {checkpoint_count} 条",
            ),
            ReadinessCheck(
                "completed_interview",
                "完整面试",
                completed_interview_count > 0,
                f"已完成面试 {completed_interview_count} 场",
            ),
            ReadinessCheck(
                "report_history",
                "评分报告",
                report_count > 0,
                f"历史报告 {report_count} 份",
            ),
            ReadinessCheck(
                "ability_profile",
                "能力画像",
                profile_count > 0,
                f"画像知识点 {profile_count} 个",
            ),
        )
        score = round(sum(1 for check in checks if check.passed) / len(checks) * 100)
        return DemoReadiness(
            score=score,
            status=self._status(score),
            checks=checks,
            next_action=self._next_action(checks),
        )

    async def _count(self, db: AsyncSession, statement) -> int:  # type: ignore[no-untyped-def]
        return int((await db.execute(statement)).scalar_one())

    def _status(self, score: int) -> str:
        if score >= 90:
            return "ready"
        if score >= 50:
            return "partial"
        return "not_ready"

    def _next_action(self, checks: tuple[ReadinessCheck, ...]) -> str:
        for check in checks:
            if not check.passed:
                return {
                    "knowledge_base": "先创建知识库。",
                    "ready_documents": "上传至少一份学习资料并等待索引完成。",
                    "workflow_trace": "启动一场模拟面试以产生 checkpoint。",
                    "completed_interview": "完成一轮三题面试。",
                    "report_history": "生成评分报告。",
                    "ability_profile": "执行画像更新，形成下一轮训练计划。",
                }[check.key]
        return "演示闭环已就绪，可以按知识库、RAG、面试、报告、画像顺序演示。"
