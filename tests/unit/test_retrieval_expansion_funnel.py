import pytest

from evals.retrieval_expansion_funnel import classify_funnel_loss


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"supplemental_rank": 8}, "supplemental_budget_cutoff"),
        ({"supplemental_rank": 3}, "supplemental_should_have_recovered"),
        (
            {"heading_rank": 2, "vector_rank": 9},
            "heading_candidate_suppressed_by_vector_membership",
        ),
        ({"semantic_rank": 4}, "heading_lexical_gap_semantic_available"),
        ({"text_rank": 12}, "primary_ranking_miss_without_supplemental_route"),
        ({}, "candidate_recall_miss_all_routes"),
    ],
)
def test_classify_funnel_loss(overrides: dict[str, int], expected: str) -> None:
    ranks: dict[str, int | None] = {
        "vector_rank": None,
        "text_rank": None,
        "heading_rank": None,
        "semantic_rank": None,
        "supplemental_rank": None,
    }
    ranks.update(overrides)
    assert classify_funnel_loss(ranks) == expected
