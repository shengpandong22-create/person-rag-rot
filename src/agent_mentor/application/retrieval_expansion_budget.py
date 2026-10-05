"""Pure context planning for a future second-stage retrieval expansion.

The planner consumes already-retrieved chunks. It never performs retrieval and never
mutates, reorders, truncates, or removes the primary context.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


@dataclass(frozen=True, slots=True)
class RetrievalExpansionBudget:
    primary_chunks_max: int = 6
    supplemental_chunks_max: int = 7
    combined_chunks_max: int = 13
    supplemental_content_chars_max: int = 7_000
    combined_content_chars_max: int = 18_000


@dataclass(frozen=True, slots=True)
class RetrievalExpansionContextPlan:
    primary_chunks: tuple[RetrievedChunk, ...]
    consumed_supplemental_chunks: tuple[RetrievedChunk, ...]
    combined_chunks: tuple[RetrievedChunk, ...]
    deduplicated_chunk_ids: tuple[UUID, ...]
    budget_rejected_chunk_ids: tuple[UUID, ...]
    primary_content_chars: int
    supplemental_content_chars: int
    combined_content_chars: int


DEFAULT_RETRIEVAL_EXPANSION_BUDGET = RetrievalExpansionBudget()


def plan_retrieval_expansion_context(
    primary: Sequence[RetrievedChunk],
    supplemental: Sequence[RetrievedChunk],
    *,
    budget: RetrievalExpansionBudget = DEFAULT_RETRIEVAL_EXPANSION_BUDGET,
) -> RetrievalExpansionContextPlan:
    """Append whole, unique supplemental chunks while respecting the frozen budget."""

    primary_chunks = tuple(primary)
    _validate_budget(budget)
    if len(primary_chunks) > budget.primary_chunks_max:
        raise ValueError("primary context exceeds the chunk budget")

    primary_ids = [chunk.chunk_id for chunk in primary_chunks]
    if len(primary_ids) != len(set(primary_ids)):
        raise ValueError("primary context contains duplicate chunk ids")

    primary_chars = sum(len(chunk.content) for chunk in primary_chunks)
    if primary_chars > budget.combined_content_chars_max:
        raise ValueError("primary context exceeds the combined character budget")

    seen = set(primary_ids)
    consumed: list[RetrievedChunk] = []
    deduplicated: list[UUID] = []
    rejected: list[UUID] = []
    supplemental_chars = 0
    budget_exhausted = False

    for chunk in supplemental:
        if chunk.chunk_id in seen:
            deduplicated.append(chunk.chunk_id)
            continue
        seen.add(chunk.chunk_id)
        if budget_exhausted:
            rejected.append(chunk.chunk_id)
            continue

        next_supplemental_chars = supplemental_chars + len(chunk.content)
        next_combined_chars = primary_chars + next_supplemental_chars
        if (
            len(consumed) >= budget.supplemental_chunks_max
            or len(primary_chunks) + len(consumed) >= budget.combined_chunks_max
            or next_supplemental_chars > budget.supplemental_content_chars_max
            or next_combined_chars > budget.combined_content_chars_max
        ):
            budget_exhausted = True
            rejected.append(chunk.chunk_id)
            continue

        consumed.append(chunk)
        supplemental_chars = next_supplemental_chars

    consumed_chunks = tuple(consumed)
    combined = primary_chunks + consumed_chunks
    return RetrievalExpansionContextPlan(
        primary_chunks=primary_chunks,
        consumed_supplemental_chunks=consumed_chunks,
        combined_chunks=combined,
        deduplicated_chunk_ids=tuple(deduplicated),
        budget_rejected_chunk_ids=tuple(rejected),
        primary_content_chars=primary_chars,
        supplemental_content_chars=supplemental_chars,
        combined_content_chars=primary_chars + supplemental_chars,
    )


def _validate_budget(budget: RetrievalExpansionBudget) -> None:
    values = (
        budget.primary_chunks_max,
        budget.supplemental_chunks_max,
        budget.combined_chunks_max,
        budget.supplemental_content_chars_max,
        budget.combined_content_chars_max,
    )
    if any(value < 0 for value in values):
        raise ValueError("retrieval expansion budgets must be non-negative")
    if budget.primary_chunks_max + budget.supplemental_chunks_max > budget.combined_chunks_max:
        raise ValueError("combined chunk budget cannot hold primary and supplemental budgets")
