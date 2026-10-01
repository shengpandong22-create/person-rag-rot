from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from evals.demand_binding import DemandBindingPolicy, assess_demand_binding


def _chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Guide",
        source_url=None,
        trust_level="curated",
        heading_path=("Limits",),
        page_number=None,
        block_type="paragraph",
        chunk_index=0,
        content=content,
        score=0.8,
        retrieval_explanation="test",
    )


def test_numeric_binding_rejects_incidental_section_number() -> None:
    result = assess_demand_binding(
        "审计日志要保留多少天？",
        [_chunk("第 3 节介绍审计日志格式，但没有规定保留期限。")],
        DemandBindingPolicy.NUMERIC_LOCAL_V1,
    )

    assert not result.passed
    assert result.reasons == ("implicit_numeric_demand_unbound:天",)


def test_numeric_binding_accepts_number_unit_and_predicate_in_same_sentence() -> None:
    result = assess_demand_binding(
        "审计日志要保留多少天？",
        [_chunk("审计日志必须保留 30 天，之后才可归档。")],
        DemandBindingPolicy.NUMERIC_LOCAL_V1,
    )

    assert result.passed
    assert result.matched_sentences == ("审计日志必须保留 30 天，之后才可归档",)


def test_numeric_binding_requires_all_core_predicates_in_same_sentence() -> None:
    result = assess_demand_binding(
        "RRF 每秒最多处理多少次查询？",
        [_chunk("RRF 每次评分都会更新；系统每秒处理 100 次写入。")],
        DemandBindingPolicy.NUMERIC_LOCAL_V1,
    )

    assert not result.passed


def test_numeric_binding_requires_explicit_value_to_bind_to_predicate() -> None:
    evidence = _chunk("采样率为 5%。告警阈值尚未规定。")
    result = assess_demand_binding(
        "告警阈值是否为 1%？",
        [evidence],
        DemandBindingPolicy.NUMERIC_LOCAL_V1,
    )

    assert not result.passed
    assert result.reasons == ("explicit_number_unbound:1%",)


def test_none_policy_preserves_existing_gate_decision() -> None:
    evidence = replace(_chunk("没有数值答案。"), heading_path=("Other",))
    result = assess_demand_binding(
        "最多支持多少名用户？", [evidence], DemandBindingPolicy.NONE
    )

    assert result.passed
