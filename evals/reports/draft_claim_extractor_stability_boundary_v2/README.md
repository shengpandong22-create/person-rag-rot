# Claim-boundary v2 and semantic-duplicate diagnostic

## Scope

This experiment changes only the eval-only extraction prompt and adds a non-mutating semantic
duplicate diagnostic. The frozen 15-case Development dataset and its manifest are unchanged.
Production Evidence Gate behavior, validation, and holdout are untouched.

- Dataset SHA-256: `35db5be33aedcc35122f2cdc4138ee72bb7505d480978996f56f92f1e967aa69`
- Freeze manifest SHA-256: `2d8d0d46f923e7eaed16f622d90d71dffd225e5249d4093226bf3b7410838378`
- Evaluated commit: `1ad927998d350805b942b4e5976277f60910b050`
- Prompt: `draft_claim_extractor_boundary_v2`
- Duplicate rule: bidirectional NLI entailment; diagnostic only, no claim is removed

## Comparison

| Metric | Previous three-run range | Boundary v2 three-run range |
|---|---:|---:|
| JSON/schema valid rate | 100% | 100% |
| Required-claim recall | 81.82%-84.85% | 96.97% |
| Extra-claim rate | 22.73%-34.00% | 11.63% |
| Unsupported-claim rate | 4.55%-10.20% | 4.65% |
| NLI-retained claim rate | 89.80%-95.45% | 95.35% |
| Exact claim-set stability | 73.33% | 93.33% |
| Mean pairwise claim Jaccard | 86.63% | 96.44% |

All three v2 runs produced 43 claims and identical aggregate quality metrics. The only claim-set
variation was `ce-008`: one run kept the compound-clause prefixes without repeating `RRF`, while
the other two restored the subject despite the prompt's verbatim-clause rule.

## Remaining failures

- `ce-007`: adding `Evidence Gate` to a split clause caused one exact required-claim miss and two
  exact-match extras.
- `ce-008`: subject restoration caused two exact-match extras and one cross-run wording change.
- `ce-010`: the extractor retained one genuine semantic duplicate.

The semantic duplicate diagnostic marked two claims in `ce-010`. One is correct (`默认检索行为
保持不变` versus `默认检索行为没有改变`); one is a false positive (`生产组装保持不变` versus
`默认检索行为保持不变`). Its observed precision on the marked pairs is therefore 50% (1/2).
Bidirectional entailment alone does not preserve the claim subject reliably enough to drive
automatic deletion.

## Decision

Claim-boundary v2 is a substantial and repeatable improvement on the frozen Development set, but
the extractor remains eval-only. The semantic duplicate result must remain diagnostic-only. The
next safe increment is a typed subject/predicate/value representation or a deterministic subject
compatibility check before NLI duplicate classification; do not tune NLI thresholds from these
two examples and do not integrate automatic deduplication into production.
