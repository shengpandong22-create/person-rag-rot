# Frozen Development DraftClaim extraction stability

## Scope

This is an eval-only, three-run stability experiment. It does not modify or invoke the
production Evidence Gate and does not use retrieval validation or holdout data.

The frozen v2 Development set contains 15 cases covering baseline behavior, long answers,
compound sentences, duplicate claims, implicit paraphrases, formatting anomalies, and an
intentionally unsupported claim.

- Dataset SHA-256: `35db5be33aedcc35122f2cdc4138ee72bb7505d480978996f56f92f1e967aa69`
- Freeze manifest SHA-256: `2d8d0d46f923e7eaed16f622d90d71dffd225e5249d4093226bf3b7410838378`
- Evaluated commit: `783cceab31a62c615f7f4c5d08cf503fb2bc56e4`
- LLM: `deepseek-chat`, temperature `0.2`
- NLI: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`

## Results

| Metric | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| JSON/schema valid rate | 100% | 100% | 100% |
| Required-claim recall | 84.85% | 81.82% | 81.82% |
| Extra-claim rate | 22.73% | 32.65% | 34.00% |
| Unsupported-claim rate | 4.55% | 10.20% | 10.00% |
| NLI-retained claim rate | 95.45% | 89.80% | 90.00% |
| Extracted claims | 44 | 49 | 50 |
| Runtime | 35.23 s | 17.76 s | 20.07 s |

Across runs, exact per-case claim-set stability was 73.33% (11/15), and mean pairwise claim
Jaccard was 86.63%.

## Failure analysis

The four unstable cases were:

- `ce-007` compound sentence: optional wording such as `会拒答` versus `拒答` changed.
- `ce-008` compound sentence: the extractor alternated between keeping and dropping `既`.
- `ce-014` JSON formatting: one run merged two JSON fields into one claim; other runs rewrote
  them into two different statement forms.
- `ce-015` long answer: one run preserved five sentence-level claims, while two runs split the
  same content into eleven field-level claims.

Duplicate cases also produced semantically repeated claims (`ce-009`, `ce-010`). Exact matching
counts rewritten or duplicated statements as extras by design, so the metric exposes failure to
follow the verbatim-copy contract; it should not be read as a pure semantic hallucination rate.

## Decision

The strict JSON transport is stable, and NLI removes most unsupported output, but claim boundary
selection is not stable enough for production. The candidate is therefore **not approved for
production integration**. The next experiment should fix claim-boundary policy for compound
sentences and structured content, add semantic duplicate detection as a separate diagnostic, and
rerun this same frozen set without changing its fixtures.
