from __future__ import annotations

from typing import Protocol

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent_mentor.api.errors import AppError

router = APIRouter(prefix="/health", tags=["health"])


class HealthChecker(Protocol):
    async def check(self) -> bool: ...


class HealthResponse(BaseModel):
    status: str


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready(request: Request) -> HealthResponse:
    checker: HealthChecker = request.app.state.database_health_checker
    if not await checker.check():
        raise AppError(
            code="DEPENDENCY_UNAVAILABLE",
            message="Database is not ready.",
            status_code=503,
        )
    return HealthResponse(status="ok")
