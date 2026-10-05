from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from agent_mentor.api.errors import AppError
from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.application.shadow_agent_service import ShadowAgentService
from agent_mentor.domain.shadow_agent import ShadowAgentRun

router = APIRouter(prefix="/api/v1", tags=["shadow-agent"])


def service(request: Request) -> ShadowAgentService:
    if not bool(request.app.state.shadow_agent_enabled):
        raise AppError(
            "SHADOW_AGENT_DISABLED",
            "The read-only shadow agent is disabled.",
            404,
        )
    return request.app.state.shadow_agent_service


@router.post(
    "/knowledge-bases/{knowledge_base_id}/shadow-agent/recommendation",
    response_model=ShadowAgentRun,
)
async def create_shadow_recommendation(
    knowledge_base_id: UUID, request: Request
) -> ShadowAgentRun:
    return await service(request).recommend(
        user_id=DEFAULT_USER_ID,
        knowledge_base_id=knowledge_base_id,
    )

