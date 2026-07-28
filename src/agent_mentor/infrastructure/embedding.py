from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence


class DevelopmentEmbeddingGateway:
    """Deterministic feature-hashed vectors keep local retrieval useful and offline."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_documents(texts)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def _features(self, text: str) -> tuple[str, ...]:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        words = re.findall(r"[a-z0-9_]{2,}", normalized)
        chinese_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
        chinese_ngrams = [
            segment[index : index + size]
            for segment in chinese_segments
            for size in (2, 3)
            for index in range(max(0, len(segment) - size + 1))
        ]
        return tuple([*words, *chinese_ngrams])
