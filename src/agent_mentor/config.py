from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class EmbeddingProvider(StrEnum):
    DEVELOPMENT = "development"
    BGE = "bge"


PGVECTOR_DIMENSION = 512
DEFAULT_BGE_MODEL = "BAAI/bge-small-zh-v1.5"


class Settings(BaseSettings):
    """Typed application configuration with a dedicated environment-variable prefix."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT_MENTOR_",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://agentmentor:agentmentor@localhost:5432/agentmentor"
    alembic_database_url: str = "postgresql+psycopg://agentmentor:agentmentor@localhost:5432/agentmentor"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_default_model: str | None = None
    embedding_provider: EmbeddingProvider = EmbeddingProvider.DEVELOPMENT
    embedding_model: str | None = None
    embedding_dimension: int = PGVECTOR_DIMENSION
    document_storage_path: str = "uploads"
    max_upload_mb: int = 20
    max_pdf_pages: int = 200
    chunk_size: int = 600
    chunk_overlap: int = 100
    embedding_batch_size: int = 16
    retrieval_candidate_k: int = 20
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.013
    retrieval_max_chunks_per_document: int = 3

    @model_validator(mode="after")
    def clear_model_credentials_in_test(self) -> Settings:
        """Tests must never consume a developer's real model credential."""
        if self.app_env is AppEnvironment.TEST:
            self.llm_api_key = None
        return self

    @model_validator(mode="after")
    def validate_embedding_runtime(self) -> Settings:
        """Keep the default local embedding aligned with the current pgvector schema."""
        if self.embedding_dimension != PGVECTOR_DIMENSION:
            raise ValueError(
                f"embedding_dimension must be {PGVECTOR_DIMENSION} for the current "
                "pgvector schema. Changing it requires a migration and chunk reindex."
            )
        if self.embedding_provider is EmbeddingProvider.BGE and not self.embedding_model:
            self.embedding_model = DEFAULT_BGE_MODEL
        return self


@lru_cache
def get_settings() -> Settings:
    """Load .env only outside test mode, while always honoring explicit variables."""
    app_env = os.getenv("AGENT_MENTOR_APP_ENV", AppEnvironment.DEVELOPMENT).lower()
    env_file = None if app_env == AppEnvironment.TEST else ".env"
    # Pydantic Settings accepts this runtime-only keyword although its type stub omits it.
    return Settings(_env_file=env_file)  # type: ignore[call-arg]


def reset_settings_cache() -> None:
    """Test helper for environment-dependent settings."""
    get_settings.cache_clear()
