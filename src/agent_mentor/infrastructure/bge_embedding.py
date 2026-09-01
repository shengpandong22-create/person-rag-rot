"""BGE embedding gateway for local semantic retrieval.

The project keeps ``DevelopmentEmbeddingGateway`` for offline tests and
fallback demos.  This gateway is the production-like local embedding path used
when ``AGENT_MENTOR_EMBEDDING_PROVIDER=bge``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from threading import Lock
from typing import Any


class BgeEmbeddingGateway:
    """Local BGE embedding gateway backed by sentence-transformers."""

    def __init__(
        self,
        *,
        model_name: str,
        dimension: int,
        batch_size: int,
        normalize_embeddings: bool = True,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._batch_size = batch_size
        self._normalize_embeddings = normalize_embeddings
        self._model: Any | None = None
        self._model_lock = Lock()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of document chunks."""
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, list(texts))

    async def embed_query(self, text: str) -> list[float]:
        """Embed a retrieval query."""
        vectors = await self.embed_documents([text])
        return vectors[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model_sync()
        encoded = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=self._normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = encoded.tolist()
        if not isinstance(vectors, list):
            raise RuntimeError("BGE model returned an invalid embedding payload.")
        self._validate_vectors(vectors, expected_count=len(texts))
        return vectors

    def _load_model_sync(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as error:  # pragma: no cover - depends on optional runtime dependency
                raise RuntimeError(
                    "sentence-transformers is required when embedding_provider=bge. "
                    "Run `uv sync` or rebuild the api Docker image."
                ) from error
            try:
                self._model = SentenceTransformer(self._model_name)
            except Exception as error:  # pragma: no cover - depends on network/cache/runtime
                raise RuntimeError(
                    f"Failed to load BGE embedding model {self._model_name!r}. "
                    "Check HuggingFace cache/network access and Docker memory."
                ) from error
            return self._model

    def _validate_vectors(self, vectors: object, *, expected_count: int) -> None:
        if not isinstance(vectors, list) or len(vectors) != expected_count:
            raise RuntimeError(
                f"BGE model returned {len(vectors) if isinstance(vectors, list) else 'invalid'} "
                f"vectors, expected {expected_count}."
            )
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != self._dimension:
                actual = len(vector) if isinstance(vector, list) else "invalid"
                raise RuntimeError(
                    f"BGE embedding dimension mismatch: expected {self._dimension}, got {actual}."
                )
