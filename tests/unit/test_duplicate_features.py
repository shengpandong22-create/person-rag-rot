from evals.duplicate_features import (
    entity_identities_compatible,
    extract_entity_identity,
    normalize_alias,
    normalize_date,
    normalize_negation,
    normalize_number,
    normalize_pronoun_pair,
    transform_pair,
)


def test_alias_normalization_uses_canonical_component_names() -> None:
    assert normalize_alias("Reciprocal Rank Fusion 融合排名") == "RRF 融合排名"
    assert normalize_alias("最终验收集不用于调参") == "Holdout 不用于调参"


def test_pronoun_normalization_uses_resolved_peer_subject() -> None:
    pair = normalize_pronoun_pair("Evidence Gate 会拒答。", "它会拒答。")

    assert pair.right == "Evidence Gate会拒答。"
    assert pair.applied is True


def test_negation_normalization_preserves_polarity_boundary() -> None:
    assert normalize_negation("Holdout 不能用于调参") == "Holdout 禁止用于调参"
    assert normalize_negation("Holdout 用于调参") == "Holdout 用于调参"


def test_number_normalization_handles_percent_and_chinese_tens() -> None:
    assert normalize_number("阈值为 70%") == "阈值为 0.7"
    assert normalize_number("RRF k 为六十") == "RRF k 为60"
    assert normalize_number("冻结于 2026-09-07") == "冻结于 2026-09-07"


def test_date_normalization_uses_iso_date() -> None:
    assert normalize_date("冻结于 2026 年 9 月 7 日") == "冻结于 2026-09-07"


def test_transform_pair_applies_only_requested_feature() -> None:
    pair = transform_pair(
        "最终验收集不用于参数选择。",
        "Holdout 不能用于参数选择。",
        ("alias", "negation"),
    )

    assert pair.left == pair.right


def test_entity_identity_distinguishes_same_predicate_different_subjects() -> None:
    production = extract_entity_identity("生产组装保持不变。")
    retrieval = extract_entity_identity("默认检索行为保持不变。")

    assert production.value == "生产组装"
    assert retrieval.value == "默认检索行为"
    assert entity_identities_compatible(production, retrieval) is False


def test_entity_identity_preserves_alias_and_value_subjects_after_normalization() -> None:
    alias_pair = transform_pair(
        "最终验收集不用于参数选择。",
        "Holdout 不能用于参数选择。",
        ("alias", "negation"),
    )
    left = extract_entity_identity(alias_pair.left)
    right = extract_entity_identity(alias_pair.right)
    value_left = extract_entity_identity("RRF k 是 60。")
    value_right = extract_entity_identity("RRF k 的取值为六十。")

    assert entity_identities_compatible(left, right) is True
    assert entity_identities_compatible(value_left, value_right) is True


def test_entity_identity_keeps_unresolved_pairs_non_destructive() -> None:
    assert extract_entity_identity("它会拒答。").resolved is False
    assert entity_identities_compatible(
        extract_entity_identity("它会拒答。"),
        extract_entity_identity("Evidence Gate 会拒答。"),
    ) is None
