from evals.retrieval_evidence_presence import evidence_presence


def test_value_presence_requires_requested_value_unit_and_relation_signals() -> None:
    result = evidence_presence(
        "审计日志要保留多少天？",
        "审计日志必须保留 30 天。",
    )

    assert result["value_required"] is True
    assert result["value_present"] is True
    assert result["relation_present"] is True


def test_incidental_number_does_not_cover_requested_unit() -> None:
    result = evidence_presence(
        "系统最多支持多少名用户？",
        "第 3 节介绍系统架构，但没有容量结论。",
    )

    assert result["number_present"] is True
    assert result["value_present"] is False


def test_relation_presence_handles_code_identifier_alias() -> None:
    result = evidence_presence(
        "学习率如何计算？",
        "代码计算 learning_rate = min(0.35, 0.18 * weight)",
    )

    assert result["relation_present"] is True
