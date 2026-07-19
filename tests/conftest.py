from __future__ import annotations

import pytest

from agent_mentor.config import AppEnvironment, Settings
from agent_mentor.main import create_app


class HealthyDatabase:
    async def check(self) -> bool:
        return True


class UnhealthyDatabase:
    async def check(self) -> bool:
        return False


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env=AppEnvironment.TEST,
        database_url="postgresql+asyncpg://agentmentor:agentmentor@localhost:5432/agentmentor",
    )


@pytest.fixture
def app(test_settings: Settings):
    application = create_app(test_settings)
    application.state.database_health_checker = HealthyDatabase()
    return application
