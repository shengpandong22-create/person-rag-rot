from __future__ import annotations

import httpx
import pytest


class UnhealthyDatabase:
    async def check(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_live_endpoint_does_not_require_database(app) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Trace-Id": "live-trace"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Trace-Id"] == "live-trace"


@pytest.mark.asyncio
async def test_ready_endpoint_returns_structured_error_when_database_is_unavailable(app) -> None:
    app.state.database_health_checker = UnhealthyDatabase()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready", headers={"X-Trace-Id": "ready-trace"})

    assert response.status_code == 503
    assert response.json() == {
        "code": "DEPENDENCY_UNAVAILABLE",
        "message": "Database is not ready.",
        "detail": None,
        "trace_id": "ready-trace",
    }
