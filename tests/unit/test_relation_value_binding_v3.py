from evals.relation_value_binding_v3 import (
    EvidenceProvenance,
    RelationRole,
    ValueSemantic,
    bind_typed_relation_value,
    normalize_demand,
)


def test_normalize_demand_separates_role_semantic_and_unit() -> None:
    demand = normalize_demand("learning_rate硬上限", "比例", "code_statement")

    assert demand.role is RelationRole.UPPER_BOUND
    assert demand.value_semantic is ValueSemantic.RATIO
    assert demand.canonical_unit == "比例"


def test_output_entity_controls_semantic_when_inputs_include_score() -> None:
    demand = normalize_demand(
        "0.40起点与0.80得分对应的新掌握度", "比例", "bounded_multi_span"
    )

    assert demand.value_semantic is ValueSemantic.RATIO
    assert demand.role is RelationRole.DERIVED_VALUE


def test_table_range_keeps_positive_values_and_provenance() -> None:
    provenance = EvidenceProvenance("chunk-1", "评分文档", ("评分", "四维评分"))
    bindings = bind_typed_relation_value(
        normalize_demand("correctness单项分数范围", "分", "table_row"),
        provenance=provenance,
        content="| correctness | 结论与核心事实 | 0-5 | 概念混淆 |",
    )

    assert bindings
    assert bindings[0].values == ("0", "5")
    assert bindings[0].provenance == provenance


def test_coverage_threshold_does_not_satisfy_accuracy_guarantee() -> None:
    bindings = bind_typed_relation_value(
        normalize_demand("中文词汇门禁召回准确率保证", "比例", "bounded_multi_span"),
        provenance=EvidenceProvenance("chunk-1", "检索文档", ("证据门禁",)),
        content="中文至少 2 个 bigram 重叠，且词汇覆盖比例 ≥ 18% 才通过粗筛。",
    )

    assert bindings == ()


def test_code_record_binds_alias_relation_with_local_value() -> None:
    bindings = bind_typed_relation_value(
        normalize_demand("低置信final的画像更新权重", "比例", "table_row"),
        provenance=EvidenceProvenance("chunk-1", "画像文档", ("画像更新",)),
        content=(
            "if confidence < 0.70:\n"
            "    return ProfileUpdateDecision(\n"
            '        reason="low_confidence_final",\n'
            "        confidence_weight=0.5,\n"
            "    )"
        ),
    )

    assert any(binding.values == ("0.5",) for binding in bindings)
    assert len(bindings) <= 3


def test_overlapping_spans_with_same_values_are_deduplicated() -> None:
    bindings = bind_typed_relation_value(
        normalize_demand("learning_rate硬上限", "比例", "code_statement"),
        provenance=EvidenceProvenance("chunk-1", "画像文档", ("渐进更新",)),
        content=(
            "def update():\n"
            "    learning_rate = min(0.35, base_rate)\n"
            "    return learning_rate"
        ),
    )

    assert len(bindings) == 1
    assert bindings[0].values == ("0.35",)


def test_bounded_span_does_not_join_distant_relation_and_value() -> None:
    bindings = bind_typed_relation_value(
        normalize_demand("画像更新权重", "比例", "bounded_multi_span"),
        provenance=EvidenceProvenance("chunk-1", "画像文档", ("画像更新",)),
        content="画像更新权重如下\n无关一\n无关二\n无关三\n无关四\n最终值 0.5",
    )

    assert bindings == ()
