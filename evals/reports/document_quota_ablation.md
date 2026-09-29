# Per-document retrieval quota ablation

## Scope

This eval-only experiment keeps vector-only retrieval, BGE embedding, candidate_k=20, Top-K=6,
minimum evidence score, adjacency filtering, and the production Evidence Gate unchanged. Only
`max_chunks_per_document` varies between 3, 4, and unlimited. Production remains 3.

- Evaluated commit: `b791ef6bb39f`
- Regression dataset SHA-256: `dc980d953d62bf939c6b5c64e366897c1e78957df0f928e6381aeaeece592df2`
- Validation dataset SHA-256: `4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`
- Validation freeze-manifest SHA-256: `e04fd574249bc4cc72a7e7c8a5eb9e79cc3341d9e66bad5c78e0b4fbe82abd32`
- Holdout was not run.

Later runs report `git_dirty=true` only because earlier report directories from this same experiment
were untracked. All groups ran the same committed code and unchanged datasets.

## Regression safety comparison

| Quota | Recall@1 | Recall@3 | Recall@6 | MRR | Negative rejection | P95 ms | Avg unique documents |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | 20.00% | 40.00% | 45.00% | 30.17% | 50.00% | 43.11 | 3.60 |
| 4 | 20.00% | 40.00% | 50.00% | 31.42% | 50.00% | 80.19 | 3.43 |
| Unlimited | 20.00% | 40.00% | 50.00% | 31.42% | 50.00% | 45.99 | 3.40 |

Quota 4 and unlimited improve Recall@6 without changing answerability or rejection behavior. The
single-run latency difference is noisy because model initialization and Hugging Face cache checks
occurred during some groups; it is not used as the selection criterion.

## Validation comparison

| Quota | Recall@1 | Recall@3 | Recall@6 | MRR | Negative rejection | P95 ms | Avg unique documents | Filter drop rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 35.29% | 52.94% | 70.59% | 48.53% | 100.00% | 46.50 | 3.41 | 34.32% |
| 4 | 35.29% | 52.94% | 82.35% | 50.98% | 100.00% | 51.14 | 3.32 | 23.41% |
| Unlimited | 35.29% | 52.94% | 82.35% | 50.98% | 100.00% | 42.85 | 3.18 | 7.95% |

Quota 4 recovers `va-pos-002` at rank 4 and `va-pos-014` at rank 6. The remaining affected case,
`va-pos-003`, has its first relevant raw candidate at rank 8; quota 4 still filters it and unlimited
moves it to post-filter rank 9, outside Top-K. Removing the quota therefore cannot improve formal
Recall beyond quota 4 on this dataset.

## Decision

Recommend quota 4 as the fixed next candidate:

- matches unlimited Recall@6 and MRR on both Regression and Validation;
- preserves more source diversity than unlimited;
- keeps every Validation negative rejection correct;
- is the smallest change from the production default of 3.

Do not implement score-aware quota yet. Quota 4 already reaches the current pre-filter Recall@6
ceiling, so another policy would add algorithmic complexity without evidence of additional gain.

This is a candidate-selection result, not production acceptance. The old retrieval holdout must
not be rerun. A new acceptance set is required before changing the production default.
