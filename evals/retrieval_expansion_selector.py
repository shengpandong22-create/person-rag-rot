"""Eval-only supplemental consumption selectors."""

from __future__ import annotations

from collections.abc import Sequence

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


def select_rank_capped_supplemental(
    candidates: Sequence[RetrievedChunk], *, max_chunks: int = 3
) -> tuple[RetrievedChunk, ...]:
    """Preserve provider order and expose at most the first whole chunks."""
    if max_chunks < 0:
        raise ValueError("max_chunks must be non-negative")
    return tuple(candidates[:max_chunks])
