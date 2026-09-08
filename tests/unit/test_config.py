from __future__ import annotations

import pytest

from agent_mentor.config import AppEnvironment, EmbeddingProvider, Settings


def test_test_environment_discards_model_credential(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MENTOR_LLM_API_KEY", "must-not-be-used")

    settings = Settings(app_env=AppEnvironment.TEST)

    assert settings.llm_api_key is None


def test_embedding_dimension_must_match_current_pgvector_schema() -> None:
    with pytest.raises(ValueError, match="embedding_dimension must be 512"):
        Settings(embedding_dimension=1536)


def test_bge_provider_uses_default_model_until_schema_rebuild() -> None:
    settings = Settings(embedding_provider=EmbeddingProvider.BGE)

    assert settings.embedding_model == "BAAI/bge-small-zh-v1.5"


def test_retrieval_min_score_filters_rrf_tail_but_keeps_vector_top_hit() -> None:
    settings = Settings()

    assert settings.retrieval_min_score == 0.013
    assert settings.retrieval_min_score > 1 / (60 + settings.retrieval_candidate_k)
    assert settings.retrieval_min_score < 1 / (60 + 1)
