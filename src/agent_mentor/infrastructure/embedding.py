"""开发环境 Embedding — 使用特征哈希（Feature Hashing）生成确定性向量，无需真实 Embedding 模型。

设计目的：
    - 不配置 LLM Key 时也能运行本地检索
    - 相同文本始终产生相同向量（确定性）
    - 不需要下载模型、不需要 GPU

算法：Feature Hashing + BLAKE2b
    1. 提取文本特征（英文单词 + 中文 2-gram/3-gram）
    2. 对每个特征做 BLAKE2b 哈希 → 得到 8 字节摘要
    3. 前 4 字节取模确定桶位置（bucket），第 5 字节的末位确定符号（sign）
    4. 向量归一化（L2 归一化）
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence


class DevelopmentEmbeddingGateway:
    """特征哈希向量生成器 — 无需真实模型，离线可用，确定性输出。
    
    使用场景：
        - 本地开发/测试环境
        - 未配置 LLM/Embedding API Key 时自动启用
    """

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """批量文档向量化"""
        return [self._embed_text(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        """单条查询向量化"""
        return (await self.embed_documents([text]))[0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化（别名）"""
        return await self.embed_documents(texts)

    def _embed_text(self, text: str) -> list[float]:
        """核心算法：将文本特征映射为固定维度向量。
        
        步骤：
            1. 提取文本特征（单词 + n-gram）
            2. 每个特征通过 BLAKE2b 哈希映射到向量维度
            3. 使用符号位（+1/-1）累积到对应桶
            4. L2 归一化
        """
        vector = [0.0] * self._dimension
        for feature in self._features(text):
            # BLAKE2b 哈希 → 8 字节摘要
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            # 前 4 字节 → 桶索引（0 ~ dimension-1）
            bucket = int.from_bytes(digest[:4], "big") % self._dimension
            # 第 5 字节末位 → 符号（+1 或 -1）
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        # L2 归一化：使向量模长为 1，保证余弦相似度计算正确
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def _features(self, text: str) -> tuple[str, ...]:
        """提取文本特征：英文单词（2+字符）+ 中文 2-gram 和 3-gram。
        
        例："HashMap 扩容机制"
        → 英文: ["hashmap"]
        → 中文: ["扩容", "容机", "机制", "扩容机", "容机制"]
        """
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        # 英文单词：2 个字符以上的字母数字组合
        words = re.findall(r"[a-z0-9_]{2,}", normalized)
        # 中文连续片段 → 拆分为 2-gram 和 3-gram
        chinese_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
        chinese_ngrams = [
            segment[index : index + size]
            for segment in chinese_segments
            for size in (2, 3)  # 2-gram 和 3-gram
            for index in range(max(0, len(segment) - size + 1))
        ]
        return tuple([*words, *chinese_ngrams])
