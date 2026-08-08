from __future__ import annotations

import pytest

from agent_mentor.config import AppEnvironment, EmbeddingProvider, Settings


def test_test_environment_discards_model_credential(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MENTOR_LLM_API_KEY", "must-not-be-used")

    settings = Settings(app_env=AppEnvironment.TEST)

    assert settings.llm_api_key is None


def test_embedding_dimension_must_match_current_pgvector_schema() -> None:
    with pytest.raises(ValueError, match="embedding_dimension must be 1536"):
        Settings(embedding_dimension=512)


def test_bge_provider_is_explicitly_guarded_until_migration_exists() -> None:
    with pytest.raises(ValueError, match="BGE embedding is planned"):
        Settings(embedding_provider=EmbeddingProvider.BGE)
