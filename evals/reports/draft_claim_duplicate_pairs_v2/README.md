# Frozen DraftClaim duplicate-pair evaluation

## Scope

This eval-only experiment measures semantic duplicate detection on a separately frozen,
balanced Development fixture. It does not modify production behavior and does not use retrieval
validation or holdout data.

- Cases: 22 (11 duplicate, 11 non-duplicate)
- Categories: pronoun, alias, nested subject, number, date, negation, near paraphrase
- Dataset SHA-256: `927fe6d261e66e84b6b5e126787076f425bb4243b543648d848fa1666e3a09c2`
- Evaluated commit: `62d59de4e28c3d4184a434913bd2eca91bac922a`
- Subject-signature unresolved rate: 31.82%

## Results

| Policy | Precision | Recall | F1 | Accuracy | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| Bidirectional NLI only | 77.78% | 63.64% | 70.00% | 72.73% | 2 | 4 |
| NLI plus explicit subject-conflict veto | 75.00% | 27.27% | 40.00% | 59.09% | 1 | 8 |
| NLI requiring resolved equal subjects | 100.00% | 18.18% | 30.77% | 59.09% | 0 | 9 |

NLI-only false positives were:

- `dup-019`: identical predicate but different subjects (`生产组装` versus `默认检索行为`).
- `dup-021`: identical date but different dataset subjects (`Validation` versus `Holdout`).

NLI-only false negatives covered pronoun resolution (`dup-001`), aliasing (`dup-006`), numeric
equivalence (`dup-010`), and date-format equivalence (`dup-013`).

## Interpretation

The strict subject guard eliminates observed false positives but destroys recall. The softer
conflict veto also reduces recall and even lowers precision because the current deterministic
parser mistakes aliases and negation forms for subject conflicts while leaving some unsupported
forms unresolved. Therefore neither subject policy is a viable duplicate classifier.

The previous 15-case extraction result remains valid as a narrow observation, but this balanced
fixture rejects the broader hypothesis that bidirectional NLI plus the current subject parser is
ready for automatic deduplication.

## Decision

No evaluated policy is approved for production or automatic claim removal. Keep the subject
signature and NLI outputs as diagnostics only. The next useful increment is not threshold tuning:
it is a typed parser that treats aliases, pronouns, negation, numbers, and dates as separate
features, followed by single-capability ablations on this unchanged frozen fixture.
