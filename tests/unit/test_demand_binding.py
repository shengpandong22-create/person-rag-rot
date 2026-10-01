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
    assert result.matched_chunk_ids


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


def test_typed_v2_normalizes_round_alias() -> None:
    result = assess_demand_binding(
        "复习任务要连续几回可信高分才完成？",
        [_chunk("复习任务需要连续两次可信高分才完成。")],
        DemandBindingPolicy.TYPED_LOCAL_V2,
    )

    assert result.passed
    assert "unit_alias" in result.demand_types
    assert result.requested_units == ("次",)


def test_typed_v2_maps_decimal_fraction_to_cheng_unit() -> None:
    result = assess_demand_binding(
        "低置信更新权重会缩减到几成？",
        [_chunk("低置信更新权重为 0.5，即完整权重的一半。")],
        DemandBindingPolicy.TYPED_LOCAL_V2,
    )

    assert result.passed
    assert result.requested_units == ("成",)


def test_typed_v2_requires_a_real_range_for_range_demand() -> None:
    rejected = assess_demand_binding(
        "生产延迟目标在哪个毫秒区间？",
        [_chunk("生产延迟会被持续观测，示例编号为 12。")],
        DemandBindingPolicy.TYPED_LOCAL_V2,
    )
    accepted = assess_demand_binding(
        "余弦相似度的完整取值区间是什么？",
        [_chunk("余弦相似度范围是 [-1, 1]。")],
        DemandBindingPolicy.TYPED_LOCAL_V2,
    )

    assert not rejected.passed
    assert rejected.reasons == ("range_value_unbound",)
    assert accepted.passed
    assert accepted.matched_chunk_ids


def test_typed_v2_uses_only_bounded_windows_within_one_chunk() -> None:
    first = _chunk("学习率上限为 0.35。")
    second = _chunk("另一个章节给出实际值 0.18。")
    result = assess_demand_binding(
        "学习率先取 0.35 再得到 0.18 吗？",
        [first, second],
        DemandBindingPolicy.TYPED_LOCAL_V2,
    )

    assert not result.passed
