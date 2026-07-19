from __future__ import annotations

import json
import logging
import sys
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def log_event(level: int, event: str, **fields: object) -> None:
    logging.getLogger("agent_mentor").log(
        level,
        json.dumps({"event": event, **fields}, ensure_ascii=False, default=str),
    )


async def trace_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
    request.state.trace_id = trace_id
    try:
        response = await call_next(request)
    except Exception:
        log_event(logging.ERROR, "request.failed", trace_id=trace_id, path=request.url.path)
        raise

    response.headers["X-Trace-Id"] = trace_id
    log_event(
        logging.INFO,
        "request.completed",
        trace_id=trace_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response
