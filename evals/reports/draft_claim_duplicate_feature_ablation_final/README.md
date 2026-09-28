# Typed duplicate-feature ablation

## Scope

This eval-only experiment keeps the frozen 22-pair Development fixture, NLI model, labels, and
decision rule fixed. Each ablation changes only one deterministic input normalization feature:
alias, pronoun, negation, number, or date. The combined group applies all five. Production,
validation, and holdout are untouched.

- Dataset SHA-256: `927fe6d261e66e84b6b5e126787076f425bb4243b543648d848fa1666e3a09c2`
- Evaluated commit: `b1550a11f531d615446c3340a2f1a9e901957665`
- Inference duration: 24.37 seconds

## Results

| Policy | Precision | Recall | F1 | Accuracy | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| NLI baseline | 77.78% | 63.64% | 70.00% | 72.73% | 7 | 2 | 4 |
| Alias only | 80.00% | 72.73% | 76.19% | 77.27% | 8 | 2 | 3 |
| Pronoun only | 80.00% | 72.73% | 76.19% | 77.27% | 8 | 2 | 3 |
| Negation only | 77.78% | 63.64% | 70.00% | 72.73% | 7 | 2 | 4 |
| Number only | 80.00% | 72.73% | 76.19% | 77.27% | 8 | 2 | 3 |
| Date only | 80.00% | 72.73% | 76.19% | 77.27% | 8 | 2 | 3 |
| Combined typed features | 84.62% | 100.00% | 91.67% | 90.91% | 11 | 2 | 0 |

Single-capability corrections were isolated and additive:

- Alias fixed `dup-006` (`最终验收集` -> `Holdout`).
- Pronoun fixed `dup-001` (`它` -> `Evidence Gate`).
- Number fixed `dup-010` (`70%` -> `0.7`).
- Date fixed `dup-013` (Chinese date -> ISO date).
- Negation changed four inputs but did not change a prediction because baseline NLI already
  classified all negation fixtures correctly.

The number normalizer explicitly protects complete date spans, so number-only and date-only
results are not confounded.

## Remaining failures

The combined group recovered all four baseline false negatives and introduced no new errors, but
it retained both baseline false positives:

- `dup-019`: same predicate, different subjects (`生产组装` vs `默认检索行为`).
- `dup-021`: same date, different subjects (`Validation` vs `Holdout`).

This confirms that typed normalization improves semantic recall, while entity/subject identity is
still the precision bottleneck.

## Decision

The combined feature path is a strong eval-only candidate, improving F1 from 70.00% to 91.67%,
but 84.62% precision is insufficient for automatic claim deletion. Keep all five features and
their diagnostics out of production. The next experiment should add a typed entity-identity veto
on top of the fixed combined candidate, then measure whether it removes `dup-019` and `dup-021`
without losing alias and pronoun true positives. Do not tune NLI thresholds.
