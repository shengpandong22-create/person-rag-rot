# Development Retrieval Loss Funnel

This is a diagnostic-only decomposition of one unchanged retrieval run.
Counterfactual stage losses may overlap; terminal outcomes are mutually exclusive.

## Reproducibility

- Dataset: `evals\datasets\retrieval_development_v1.jsonl`
- Dataset SHA-256: `50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- Git commit: `f65ee4a960e1d025f59c07f33424577bf45b30a9`
- Mode: `vector-only`
- Top-K / candidate-K: `6` / `20`
- Per-document quota: `3`
- Population: 60 graded; 25 answerable; 35 negative

## Counterfactual funnel

| Stage | Hits | Rate |
| --- | ---: | ---: |
| candidate_hit_at_20 | 19 | 76.00% |
| raw_rank_hit_at_6 | 15 | 60.00% |
| survived_diversity_filters_any_rank | 12 | 48.00% |
| final_hit_at_6 | 12 | 48.00% |
| gate_accept_after_final_hit | 12 | 100.00% |

## Counterfactual losses

These counts answer separate what-if questions and therefore may overlap.

| Loss | Cases |
| --- | ---: |
| outside_candidate_pool | 6 |
| candidate_hit_but_raw_rank_below_top_k | 4 |
| candidate_hit_but_removed_by_filters | 7 |
| survived_filters_but_below_final_top_k | 0 |
| final_hit_but_gate_rejected | 0 |

## Mutually exclusive terminal outcomes

| Outcome | Cases |
| --- | ---: |
| adjacent_filter_miss | 2 |
| candidate_recall_miss | 6 |
| per_document_filter_miss | 5 |
| success | 12 |

## Ground-truth filter exposure

| Filter reason | Any relevant chunk exposed | Terminal losses |
| --- | ---: | ---: |
| adjacent_chunk | 3 | 2 |
| per_document_limit | 6 | 5 |

## Evidence Gate after a relevant retrieval hit

| Answerability | Retrieval hits | Accepted | Acceptance rate |
| --- | ---: | ---: | ---: |
| full | 6 | 6 | 100.00% |
| partial | 6 | 6 | 100.00% |

## Negative rejection by reason

| Reason | Rejected / Total | Rate |
| --- | ---: | ---: |
| false_premise | 1 / 8 | 12.50% |
| in_domain_no_conclusion | 1 / 5 | 20.00% |
| in_domain_value_missing | 1 / 7 | 14.29% |
| out_of_range_implementation | 2 / 5 | 40.00% |
| out_of_scope | 1 / 5 | 20.00% |
| version_not_released | 1 / 5 | 20.00% |
