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


class RuntimeResponse(BaseModel):
    status: str
    app_version: str
    started_at: str
    llm_enabled: bool
    llm_model: str | None
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int


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


@router.get("/runtime", response_model=RuntimeResponse)
async def runtime(request: Request) -> RuntimeResponse:
    return RuntimeResponse(
        status="ok",
        app_version=str(getattr(request.app.state, "app_version", "unknown")),
        started_at=str(getattr(request.app.state, "started_at", "unknown")),
        llm_enabled=bool(getattr(request.app.state, "llm_enabled", False)),
        llm_model=getattr(request.app.state, "llm_model", None),
        embedding_provider=str(getattr(request.app.state, "embedding_provider", "unknown")),
        embedding_model=str(getattr(request.app.state, "embedding_model", "unknown")),
        embedding_dimension=int(getattr(request.app.state, "embedding_dimension", 0)),
    )
