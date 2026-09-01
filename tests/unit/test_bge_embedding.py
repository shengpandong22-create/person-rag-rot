from __future__ import annotations

from agent_mentor.infrastructure.bge_embedding import BgeEmbeddingGateway


def test_bge_embedding_validates_vector_dimension() -> None:
    gateway = BgeEmbeddingGateway(model_name="unused", dimension=3, batch_size=2)

    gateway._validate_vectors([[1.0, 0.0, 0.0]], expected_count=1)


def test_bge_embedding_rejects_dimension_mismatch() -> None:
    gateway = BgeEmbeddingGateway(model_name="unused", dimension=3, batch_size=2)

    try:
        gateway._validate_vectors([[1.0, 0.0]], expected_count=1)
    except RuntimeError as error:
        assert "dimension mismatch" in str(error)
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("Expected dimension mismatch to raise RuntimeError.")
