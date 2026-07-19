from __future__ import annotations

import hashlib
from collections.abc import Sequence


class DevelopmentEmbeddingGateway:
    """Deterministic local vectors keep local development offline and reproducible."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            seed = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append(
                [((seed[index % len(seed)] / 255) * 2) - 1 for index in range(self._dimension)]
            )
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_documents(texts)
