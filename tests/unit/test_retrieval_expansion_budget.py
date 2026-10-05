from __future__ import annotations

from uuid import UUID

import pytest

from agent_mentor.application.retrieval_expansion_budget import (
    RetrievalExpansionBudget,
    plan_retrieval_expansion_context,
)
from agent_mentor.ports.knowledge_retriever import RetrievedChunk


def test_preserves_primary_top_six_and_deduplicates_supplemental_chunks() -> None:
    primary = [_chunk(index, content=f"primary-{index}") for index in range(1, 7)]
    new_chunk = _chunk(7, content="new evidence")

    plan = plan_retrieval_expansion_context(
        primary,
        [primary[2], new_chunk, new_chunk],
    )

    assert plan.primary_chunks == tuple(primary)
    assert plan.combined_chunks[:6] == tuple(primary)
    assert plan.consumed_supplemental_chunks == (new_chunk,)
    assert plan.deduplicated_chunk_ids == (primary[2].chunk_id, new_chunk.chunk_id)
    assert [chunk.chunk_id for chunk in plan.combined_chunks] == [
        *(chunk.chunk_id for chunk in primary),
        new_chunk.chunk_id,
    ]


def test_stops_at_seven_supplemental_and_thirteen_combined_chunks() -> None:
    primary = [_chunk(index) for index in range(1, 7)]
    supplemental = [_chunk(index) for index in range(7, 16)]

    plan = plan_retrieval_expansion_context(primary, supplemental)

    assert len(plan.consumed_supplemental_chunks) == 7
    assert len(plan.combined_chunks) == 13
    assert plan.budget_rejected_chunk_ids == (
        supplemental[7].chunk_id,
        supplemental[8].chunk_id,
    )


def test_stops_before_first_whole_chunk_that_exceeds_character_budget() -> None:
    primary = [_chunk(1, content="p" * 10_000)]
    supplemental = [
        _chunk(2, content="a" * 4_000),
        _chunk(3, content="b" * 3_001),
        _chunk(4, content="c"),
    ]

    plan = plan_retrieval_expansion_context(primary, supplemental)

    assert plan.consumed_supplemental_chunks == (supplemental[0],)
    assert plan.supplemental_content_chars == 4_000
    assert plan.combined_content_chars == 14_000
    assert plan.budget_rejected_chunk_ids == (
        supplemental[1].chunk_id,
        supplemental[2].chunk_id,
    )


def test_combined_character_budget_can_be_tighter_than_supplemental_budget() -> None:
    budget = RetrievalExpansionBudget(
        supplemental_content_chars_max=7_000,
        combined_content_chars_max=18_000,
    )
    primary = [_chunk(1, content="p" * 17_500)]
    supplemental = [_chunk(2, content="s" * 501)]

    plan = plan_retrieval_expansion_context(primary, supplemental, budget=budget)

    assert plan.consumed_supplemental_chunks == ()
    assert plan.budget_rejected_chunk_ids == (supplemental[0].chunk_id,)


def test_rejects_primary_context_that_cannot_be_preserved_safely() -> None:
    duplicate = _chunk(1)
    with pytest.raises(ValueError, match="duplicate"):
        plan_retrieval_expansion_context([duplicate, duplicate], [])

    with pytest.raises(ValueError, match="chunk budget"):
        plan_retrieval_expansion_context([_chunk(index) for index in range(1, 8)], [])

    with pytest.raises(ValueError, match="character budget"):
        plan_retrieval_expansion_context([_chunk(1, content="x" * 18_001)], [])


def _chunk(index: int, *, content: str = "content") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID(int=index),
        document_id=UUID(int=100 + index),
        document_title=f"document-{index}",
        source_url=None,
        trust_level="official",
        heading_path=(f"heading-{index}",),
        page_number=None,
        block_type="paragraph",
        chunk_index=index,
        content=content,
        score=1.0,
        retrieval_explanation="test",
    )
