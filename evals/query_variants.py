"""Deterministic eval-only query views for candidate-recall ablation."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from agent_mentor.rag.retrieval import normalize_query


class QueryVariantStrategy(StrEnum):
    ORIGINAL = "original"
    CJK_NORMALIZED = "cjk-normalized"
    KEYWORD_PRESERVE = "keyword-preserve"
    MULTI_QUERY = "multi-query"


_QUESTION_PUNCTUATION = re.compile(r"[，。！？；：、（）【】《》“”‘’?!.;:,()\[\]{}]+")
_QUESTION_FRAMING = re.compile(
    r"^(?:请问|请说明|请解释|请分析|能否说明|能否解释|请介绍|请描述)"
)
_FUNCTION_PHRASES = re.compile(
    r"(?:为什么|是什么|有哪些|有什么|如何|怎样|分别|具体|当前|本项目|系统中|项目中)"
)


def cjk_normalize_query(question: str) -> str:
    """Normalize width/punctuation and remove only leading conversational framing."""
    normalized = unicodedata.normalize("NFKC", question)
    normalized = _QUESTION_FRAMING.sub("", normalized.strip())
    normalized = _QUESTION_PUNCTUATION.sub(" ", normalized)
    return normalize_query(normalized)


def keyword_preserve_query(question: str) -> str:
    """Keep surface forms without label- or corpus-derived expansion."""
    normalized = cjk_normalize_query(question)
    normalized = _FUNCTION_PHRASES.sub(" ", normalized)
    return normalize_query(normalized)


def build_query_variants(question: str, strategy: QueryVariantStrategy) -> tuple[str, ...]:
    original = normalize_query(question)
    cjk_normalized = cjk_normalize_query(question)
    keyword_preserved = keyword_preserve_query(question)
    if strategy is QueryVariantStrategy.ORIGINAL:
        candidates = (original,)
    elif strategy is QueryVariantStrategy.CJK_NORMALIZED:
        candidates = (cjk_normalized,)
    elif strategy is QueryVariantStrategy.KEYWORD_PRESERVE:
        candidates = (keyword_preserved,)
    else:
        candidates = (original, cjk_normalized, keyword_preserved)
    return tuple(dict.fromkeys(item for item in candidates if item))
