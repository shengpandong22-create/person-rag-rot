from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: str | None = None
    trace_id: str


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    detail: str | None = None


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        status_code=error.status_code,
        content=ErrorResponse(
            code=error.code,
            message=error.message,
            detail=error.detail,
            trace_id=trace_id,
        ).model_dump(),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            detail=str(error.errors()),
            trace_id=trace_id,
        ).model_dump(),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            trace_id=trace_id,
        ).model_dump(),
    )
