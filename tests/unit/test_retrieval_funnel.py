from __future__ import annotations

from evals.retrieval_funnel import build_retrieval_funnel


def _case(
    case_id: str,
    *,
    answerability: str = "full",
    raw_rank: int | None = 1,
    post_rank: int | None = 1,
    final_rank: int | None = 1,
    accepted: bool = True,
    failure: str | None = None,
    filtered: list[dict[str, object]] | None = None,
    negative_reason: str | None = None,
) -> dict[str, object]:
    return {
        "id": case_id,
        "graded": True,
        "answerability": answerability,
        "first_raw_candidate_rank": raw_rank,
        "first_post_filter_rank": post_rank,
        "first_relevant_rank": final_rank,
        "evidence_sufficient": accepted,
        "failure_category": failure,
        "negative_reason": negative_reason,
        "retrieval_stages": {"filtered_out": filtered or []},
    }


def test_funnel_separates_overlapping_stage_loss_from_terminal_cause() -> None:
    report = {
        "dataset": "development.jsonl",
        "metadata": {
            "dataset_sha256": "abc",
            "git_commit": "123",
            "experiment_mode": "vector-only",
            "retrieval_top_k": 6,
            "retrieval_candidate_k": 20,
            "retrieval_max_chunks_per_document": 3,
        },
        "cases": [
            _case("ok"),
            _case(
                "filtered",
                raw_rank=3,
                post_rank=None,
                final_rank=None,
                failure="adjacent_filter_miss",
                filtered=[
                    {
                        "reason": "adjacent_chunk",
                        "matched_ground_truth": True,
                    }
                ],
            ),
            _case(
                "candidate-miss",
                raw_rank=None,
                post_rank=None,
                final_rank=None,
                failure="candidate_recall_miss",
            ),
            _case(
                "negative",
                answerability="none",
                raw_rank=None,
                post_rank=None,
                final_rank=None,
                accepted=False,
                failure="correct_rejection",
                negative_reason="false_premise",
            ),
        ],
    }

    funnel = build_retrieval_funnel(report)

    assert funnel["counterfactual_funnel"]["candidate_hit_at_20"]["hits"] == 2
    assert funnel["counterfactual_losses"]["candidate_hit_but_removed_by_filters"] == 1
    assert funnel["mutually_exclusive_terminal_outcomes"] == {
        "adjacent_filter_miss": 1,
        "candidate_recall_miss": 1,
        "success": 1,
    }
    assert funnel["filter_ground_truth_exposure"] == {"adjacent_chunk": 1}
    assert funnel["filter_terminal_losses"] == {"adjacent_chunk": 1}
    assert funnel["terminal_case_ids"] == {
        "adjacent_filter_miss": ["filtered"],
        "candidate_recall_miss": ["candidate-miss"],
        "success": ["ok"],
    }


def test_gate_metrics_condition_on_relevant_hit_and_group_negatives() -> None:
    report = {
        "dataset": "development.jsonl",
        "metadata": {
            "dataset_sha256": "abc",
            "git_commit": "123",
            "experiment_mode": "vector-only",
            "retrieval_top_k": 6,
            "retrieval_candidate_k": 20,
            "retrieval_max_chunks_per_document": 3,
        },
        "cases": [
            _case("full-hit", accepted=True),
            _case(
                "partial-hit",
                answerability="partial",
                accepted=False,
                failure="evidence_gate_rejection",
            ),
            _case(
                "full-miss",
                raw_rank=None,
                post_rank=None,
                final_rank=None,
                accepted=True,
                failure="candidate_recall_miss",
            ),
            _case(
                "negative-accepted",
                answerability="none",
                raw_rank=None,
                post_rank=None,
                final_rank=None,
                accepted=True,
                failure="false_acceptance",
                negative_reason="false_premise",
            ),
        ],
    }

    funnel = build_retrieval_funnel(report)

    assert funnel["gate_after_retrieval_hit"]["full"] == {
        "retrieval_hits": 1,
        "accepted_after_hit": 1,
        "acceptance_rate_after_hit": 1.0,
    }
    assert funnel["gate_after_retrieval_hit"]["partial"]["acceptance_rate_after_hit"] == 0.0
    assert funnel["negative_rejection_by_reason"]["false_premise"] == {
        "total": 1,
        "rejected": 0,
        "rejection_rate": 0.0,
        "false_acceptance_ids": ["negative-accepted"],
    }
