from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.domain.shadow_agent import ShadowAgentRun
from agent_mentor.infrastructure.database.models import ShadowAgentRunModel


class SqlAlchemyShadowTraceRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(
        self, *, user_id: UUID, knowledge_base_id: UUID, run: ShadowAgentRun
    ) -> None:
        async with self._sessions() as db:
            db.add(
                ShadowAgentRunModel(
                    id=UUID(run.run_id),
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    status=run.status,
                    recommendation=run.recommendation.model_dump(mode="json"),
                    trajectory=[step.model_dump(mode="json") for step in run.steps],
                    termination_reason=run.termination_reason,
                    used_fallback=run.used_fallback,
                    business_writes=run.business_writes,
                )
            )
            await db.commit()

