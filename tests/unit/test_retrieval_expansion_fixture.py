from __future__ import annotations

from uuid import UUID

import pytest

from agent_mentor.infrastructure.retriever import (
    CandidateExpansionStrategy,
    RetrievalDiagnostics,
    RetrievalExperimentMode,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from agent_mentor.ports.supplemental_candidate_provider import SupplementalCandidateRequest
from evals.retrieval_expansion_fixture import (
    HeadingShadowSupplementalProvider,
    RetrievalExpansionExecutionFixture,
)


class _DiagnosticRetriever:
    def __init__(self, supplemental: tuple[RetrievedChunk, ...]) -> None:
        self.supplemental = supplemental
        self.calls: list[
            tuple[RetrievalQuery, RetrievalExperimentMode, CandidateExpansionStrategy]
        ] = []

    async def retrieve_with_diagnostics(
        self,
        query: RetrievalQuery,
        *,
        experiment_mode: RetrievalExperimentMode,
        candidate_expansion: CandidateExpansionStrategy,
    ) -> RetrievalDiagnostics:
        self.calls.append((query, experiment_mode, candidate_expansion))
        return RetrievalDiagnostics((), (), (), (), (), (), (), (), self.supplemental)


class _FakeProvider:
    def __init__(self, candidates: tuple[RetrievedChunk, ...]) -> None:
        self.result = candidates
        self.requests: list[SupplementalCandidateRequest] = []

    async def candidates(self, request: SupplementalCandidateRequest) -> tuple[RetrievedChunk, ...]:
        self.requests.append(request)
        return self.result


@pytest.mark.asyncio
async def test_heading_shadow_provider_uses_only_explicit_eval_diagnostic_path() -> None:
    supplemental = (_chunk(20),)
    retriever = _DiagnosticRetriever(supplemental)
    provider = HeadingShadowSupplementalProvider(retriever)  # type: ignore[arg-type]
    request = SupplementalCandidateRequest(UUID(int=1), "original question", candidate_k=25)

    result = await provider.candidates(request)

    assert result == supplemental
    assert len(retriever.calls) == 1
    query, mode, expansion = retriever.calls[0]
    assert query.query == "original question"
    assert query.top_k == 6
    assert query.candidate_k == 25
    assert mode is RetrievalExperimentMode.RRF_HEURISTIC
    assert expansion is CandidateExpansionStrategy.HEADING_SHADOW


@pytest.mark.asyncio
async def test_fixture_preserves_primary_and_reports_budget_decisions() -> None:
    primary = tuple(_chunk(index, content="p") for index in range(1, 7))
    supplemental = (
        primary[1],
        *(_chunk(index, content="s") for index in range(7, 15)),
    )
    provider = _FakeProvider(supplemental)
    clock = iter((10.0, 10.025))
    fixture = RetrievalExpansionExecutionFixture(
        provider,
        strategy="fixture-heading-shadow",
        clock=lambda: next(clock),
    )
    request = SupplementalCandidateRequest(UUID(int=100), "question")

    result = await fixture.execute(request, primary=primary)

    assert provider.requests == [request]
    assert result.plan.primary_chunks == primary
    assert result.plan.combined_chunks[:6] == primary
    assert result.trace.primary_chunk_ids == tuple(chunk.chunk_id for chunk in primary)
    assert result.trace.deduplicated_chunk_ids == (primary[1].chunk_id,)
    assert result.trace.consumed_supplemental_count == 7
    assert result.trace.combined_context_count == 13
    assert result.trace.budget_rejected_chunk_ids == (supplemental[-1].chunk_id,)
    assert result.trace.retrieval_latency_ms == pytest.approx(25.0)


def test_production_retrieve_defaults_remain_without_candidate_expansion() -> None:
    defaults = PostgresDefaultInspector.candidate_expansion_default()
    assert defaults is CandidateExpansionStrategy.NONE


class PostgresDefaultInspector:
    @staticmethod
    def candidate_expansion_default() -> CandidateExpansionStrategy:
        import inspect

        from agent_mentor.infrastructure.retriever import PostgresHybridRetriever

        parameter = inspect.signature(PostgresHybridRetriever.retrieve_with_diagnostics).parameters[
            "candidate_expansion"
        ]
        return parameter.default


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
