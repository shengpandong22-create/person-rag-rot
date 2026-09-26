# Development Hard-Negative Baseline

This is the first diagnostic baseline for
`retrieval_development_v1.jsonl`. It uses the validation-selected
`vector-only` retrieval mode and does not change retrieval, ranking, filtering,
or Evidence Gate behavior. Holdout was neither read for tuning nor rerun.

## Dataset contract

- 60 human-labelled cases: 15 full, 10 partial, and 35 none.
- The 35 negatives cover missing values, unsupported conclusions, unreleased
  versions, implementation details outside the documented range, false
  premises, and out-of-scope questions.
- Every negative records why the available material is insufficient.
- Every partial question deliberately combines a supported sub-question with
  a missing quantitative or operational claim.
- All 25 positive/partial source paths resolve against the current knowledge
  base.
- Question text and ground-truth signatures are disjoint from regression,
  validation, and holdout.
- Dataset SHA-256:
  `50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`.

No `conflicting_sources` row was manufactured: the current corpus did not
contain a verified contradiction suitable for a human-labelled negative.

## Vector-only baseline

| Metric | Value |
|---|---:|
| Recall@1 | 0.2400 |
| Recall@3 | 0.4400 |
| Recall@6 | 0.4800 |
| MRR | 0.3267 |
| Candidate Recall@20 | 0.7600 |
| Pre-filter Recall@6 | 0.6000 |
| Post-filter Recall@6 | 0.4800 |
| Diversity filter drop rate | 0.3383 |
| Full evidence acceptance | 0.9333 |
| Partial evidence acceptance | 1.0000 |
| Negative rejection accuracy | 0.2000 |
| P50 latency | 30.5777 ms |
| P95 latency | 35.2473 ms |
| Average returned candidates | 6.0000 |

`partial evidence acceptance` is not partial-answer correctness. The current
Evidence Gate makes a sufficient/insufficient decision, so this number only
shows that partial cases were accepted. It is useful here because accepting all
partial cases, together with rejecting only 20% of negatives, exposes an
over-acceptance problem.

## Negative rejection by reason

| Reason | Rejection rate |
|---|---:|
| false_premise | 0.1250 |
| in_domain_no_conclusion | 0.2000 |
| in_domain_value_missing | 0.1429 |
| out_of_range_implementation | 0.4000 |
| out_of_scope | 0.2000 |
| version_not_released | 0.2000 |

## Failure attribution

| Category | Count |
|---|---:|
| candidate_recall_miss | 6 |
| per_document_filter_miss | 5 |
| adjacent_filter_miss | 2 |
| false_acceptance | 28 |
| correct_rejection | 7 |
| partial_answer_boundary | 6 |

The baseline separates two problems. Positive retrieval still loses evidence
before final Top-6 (6 candidate misses and 7 diversity-filter misses), while
the dominant hard-negative failure is Evidence Gate over-acceptance (28 of 35
negatives). This report is diagnostic evidence for the next calibration phase;
it is not a parameter-selection result yet.

Per-case retrieved chunks, stage ranks and scores, evidence decisions, and
failure categories are in `vector-only/retrieval_eval.json`.
