from __future__ import annotations

from evals.query_variants import (
    QueryVariantStrategy,
    build_query_variants,
    cjk_normalize_query,
    keyword_preserve_query,
)


def test_cjk_normalization_preserves_identifiers_numbers_and_semantics() -> None:
    assert cjk_normalize_query("请说明：RRF k=60，为什么不能直接加分？") == (
        "RRF k=60 为什么不能直接加分"
    )


def test_keyword_view_removes_question_framing_without_using_labels() -> None:
    assert keyword_preserve_query("本项目当前有哪些 Evidence Gate 规则？") == (
        "Evidence Gate 规则"
    )


def test_multi_query_is_deterministic_and_deduplicated() -> None:
    variants = build_query_variants(
        "请解释 RRF。",
        QueryVariantStrategy.MULTI_QUERY,
    )

    assert variants == ("请解释 RRF。", "RRF")
    assert build_query_variants("请解释 RRF。", QueryVariantStrategy.MULTI_QUERY) == variants
