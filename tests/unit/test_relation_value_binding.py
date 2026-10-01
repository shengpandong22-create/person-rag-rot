from evals.relation_value_binding import RelationValueDemand, bind_relation_value


def test_table_binding_keeps_relation_value_and_unit_in_one_row() -> None:
    bindings = bind_relation_value(
        RelationValueDemand("低置信final画像更新权重", "比例", "table_row"),
        chunk_id="one",
        content="| 条件 | 权重 |\n| 低置信 final 画像更新 | 0.5 |",
    )

    assert bindings
    assert bindings[0].values == ("0.5",)


def test_code_binding_rejects_value_on_unrelated_statement() -> None:
    bindings = bind_relation_value(
        RelationValueDemand("learning_rate硬上限", "比例", "code_statement"),
        chunk_id="one",
        content="retry_limit = 3\nlearning_rate = adaptive_value",
    )

    assert bindings == ()


def test_bounded_binding_does_not_join_distant_lines() -> None:
    content = "掌握度起点 0.40\n说明一\n说明二\n说明三\n新掌握度 0.472"
    bindings = bind_relation_value(
        RelationValueDemand("掌握度起点对应的新掌握度", "比例", "bounded_multi_span"),
        chunk_id="one",
        content=content,
    )

    assert all(not ({"0.40", "0.472"} <= set(item.values)) for item in bindings)
