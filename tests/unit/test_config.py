from __future__ import annotations

from agent_mentor.config import AppEnvironment, Settings


def test_test_environment_discards_model_credential(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MENTOR_LLM_API_KEY", "must-not-be-used")

    settings = Settings(app_env=AppEnvironment.TEST)

    assert settings.llm_api_key is None
