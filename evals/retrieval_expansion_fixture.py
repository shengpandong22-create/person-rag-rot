"""Eval-only provider and execution fixture for second-stage retrieval.

Nothing in production assembly imports this module. The fixture deliberately stops
after candidate generation, context budgeting, and trace construction.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from agent_mentor.application.retrieval_expansion_budget import (
    DEFAULT_RETRIEVAL_EXPANSION_BUDGET,
    RetrievalExpansionBudget,
    RetrievalExpansionContextPlan,
    plan_retrieval_expansion_context,
)
from agent_mentor.infrastructure.retriever import (
    CandidateExpansionStrategy,
    PostgresHybridRetriever,
    RetrievalExperimentMode,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from agent_mentor.ports.supplemental_candidate_provider import (
    SupplementalCandidateProvider,
    SupplementalCandidateRequest,
)


@dataclass(frozen=True, slots=True)
class RetrievalExpansionFixtureTrace:
    strategy: str
    primary_chunk_ids: tuple[UUID, ...]
    supplemental_candidate_chunk_ids: tuple[UUID, ...]
    consumed_supplemental_chunk_ids: tuple[UUID, ...]
    deduplicated_chunk_ids: tuple[UUID, ...]
    budget_rejected_chunk_ids: tuple[UUID, ...]
    combined_context_chunk_ids: tuple[UUID, ...]
    primary_candidate_count: int
    supplemental_candidate_count: int
    consumed_supplemental_count: int
    combined_context_count: int
    primary_content_chars: int
    supplemental_content_chars: int
    combined_content_chars: int
    retrieval_latency_ms: float


@dataclass(frozen=True, slots=True)
class RetrievalExpansionFixtureResult:
    candidates: tuple[RetrievedChunk, ...]
    plan: RetrievalExpansionContextPlan
    trace: RetrievalExpansionFixtureTrace


class HeadingShadowSupplementalProvider:
    """Explicit eval adapter over the existing heading-shadow diagnostic path."""

    strategy = CandidateExpansionStrategy.HEADING_SHADOW.value

    def __init__(self, retriever: PostgresHybridRetriever) -> None:
        self._retriever = retriever

    async def candidates(self, request: SupplementalCandidateRequest) -> tuple[RetrievedChunk, ...]:
        diagnostics = await self._retriever.retrieve_with_diagnostics(
            RetrievalQuery(
                knowledge_base_id=request.knowledge_base_id,
                query=request.question,
                top_k=6,
                candidate_k=request.candidate_k,
            ),
            experiment_mode=RetrievalExperimentMode.RRF_HEURISTIC,
            candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
        )
        return diagnostics.supplemental_candidates


class RetrievalExpansionExecutionFixture:
    """Run candidate generation and pure budgeting without Gate or generation."""

    def __init__(
        self,
        provider: SupplementalCandidateProvider,
        *,
        strategy: str,
        budget: RetrievalExpansionBudget = DEFAULT_RETRIEVAL_EXPANSION_BUDGET,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._provider = provider
        self._strategy = strategy
        self._budget = budget
        self._clock = clock

    async def execute(
        self,
        request: SupplementalCandidateRequest,
        *,
        primary: Sequence[RetrievedChunk],
    ) -> RetrievalExpansionFixtureResult:
        started_at = self._clock()
        candidates = await self._provider.candidates(request)
        retrieval_latency_ms = (self._clock() - started_at) * 1000
        plan = plan_retrieval_expansion_context(
            primary,
            candidates,
            budget=self._budget,
        )
        trace = RetrievalExpansionFixtureTrace(
            strategy=self._strategy,
            primary_chunk_ids=tuple(chunk.chunk_id for chunk in plan.primary_chunks),
            supplemental_candidate_chunk_ids=tuple(chunk.chunk_id for chunk in candidates),
            consumed_supplemental_chunk_ids=tuple(
                chunk.chunk_id for chunk in plan.consumed_supplemental_chunks
            ),
            deduplicated_chunk_ids=plan.deduplicated_chunk_ids,
            budget_rejected_chunk_ids=plan.budget_rejected_chunk_ids,
            combined_context_chunk_ids=tuple(chunk.chunk_id for chunk in plan.combined_chunks),
            primary_candidate_count=len(plan.primary_chunks),
            supplemental_candidate_count=len(candidates),
            consumed_supplemental_count=len(plan.consumed_supplemental_chunks),
            combined_context_count=len(plan.combined_chunks),
            primary_content_chars=plan.primary_content_chars,
            supplemental_content_chars=plan.supplemental_content_chars,
            combined_content_chars=plan.combined_content_chars,
            retrieval_latency_ms=retrieval_latency_ms,
        )
        return RetrievalExpansionFixtureResult(candidates=candidates, plan=plan, trace=trace)
