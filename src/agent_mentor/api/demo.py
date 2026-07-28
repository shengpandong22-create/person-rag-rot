from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent_mentor.application.demo_readiness_service import (
    DemoReadiness,
    DemoReadinessService,
    ReadinessCheck,
)

router = APIRouter(prefix="/api/v1", tags=["demo"])


class ReadinessCheckResponse(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str


class DemoReadinessResponse(BaseModel):
    score: int
    status: str
    checks: list[ReadinessCheckResponse]
    next_action: str


def service(request: Request) -> DemoReadinessService:
    return request.app.state.demo_readiness_service


def check_response(check: ReadinessCheck) -> ReadinessCheckResponse:
    return ReadinessCheckResponse(
        key=check.key,
        label=check.label,
        passed=check.passed,
        detail=check.detail,
    )


def readiness_response(readiness: DemoReadiness) -> DemoReadinessResponse:
    return DemoReadinessResponse(
        score=readiness.score,
        status=readiness.status,
        checks=[check_response(check) for check in readiness.checks],
        next_action=readiness.next_action,
    )


@router.get("/demo/readiness", response_model=DemoReadinessResponse)
async def demo_readiness(request: Request) -> DemoReadinessResponse:
    return readiness_response(await service(request).inspect())
