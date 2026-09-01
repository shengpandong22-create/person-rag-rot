from __future__ import annotations

from agent_mentor.config import EmbeddingProvider, Settings
from agent_mentor.infrastructure.bge_embedding import BgeEmbeddingGateway
from agent_mentor.infrastructure.embedding import DevelopmentEmbeddingGateway
from agent_mentor.ports.embedding_gateway import EmbeddingGateway


def create_embedding_gateway(settings: Settings) -> EmbeddingGateway:
    if settings.embedding_provider == EmbeddingProvider.BGE:
        if not settings.embedding_model:
            raise ValueError("embedding_model is required when embedding_provider=bge.")
        return BgeEmbeddingGateway(
            model_name=settings.embedding_model,
            dimension=settings.embedding_dimension,
            batch_size=settings.embedding_batch_size,
        )
    return DevelopmentEmbeddingGateway(settings.embedding_dimension)
