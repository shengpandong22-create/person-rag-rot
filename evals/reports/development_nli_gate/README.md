# Development NLI Gate Comparison

This experiment compares deterministic-only, semantic-only, and combined
claim/evidence policies over the exact same saved Development retrieval result.
It does not change production behavior and does not read validation or any
holdout.

## Runtime

- model: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
- labels: entailment / neutral / contradiction
- Transformers: 4.57.6
- device: CPU
- batch size: 8
- evidence contexts: each Top-3 chunk plus concatenated Top-3
- NLI pairs: 316
- inference time: 278014.4511 ms

## Comparison

| Policy | Full accept | Partial boundary | None reject | Macro accuracy |
|---|---:|---:|---:|---:|
| deterministic-only | 0.9333 | 0.9000 | 0.4571 | 0.7349 |
| semantic-only | 0.8000 | 0.7000 | 0.7714 | 0.7190 |
| combined | 0.8000 | 0.7000 | 0.8000 | 0.7286 |

The semantic model materially improves hard-negative rejection, especially for
missing values and unreleased versions. The combined policy reaches 0.80 none
rejection but fails the 0.90 full-acceptance safety floor, rejecting three
additional full cases (`dev-pos-004`, `dev-pos-008`, and `dev-pos-015`). It is
therefore not eligible for regression or validation.

## Negative rejection by reason (combined)

| Reason | Rejection rate |
|---|---:|
| false_premise | 0.7500 |
| in_domain_no_conclusion | 0.8000 |
| in_domain_value_missing | 1.0000 |
| out_of_range_implementation | 0.6000 |
| out_of_scope | 0.6000 |
| version_not_released | 1.0000 |

## Important limitation

The current deterministic splitter produces interrogative requirement text,
not a normalized declarative hypothesis. Generic NLI models are trained on
premise/hypothesis statements. Passing questions directly as hypotheses is a
likely source of false neutral/contradiction decisions. Concatenating Top-3
evidence did not recover full acceptance and reduced none rejection, so merely
adding more context is not the solution.

## Decision

The experiment proves that semantic entailment adds useful discrimination, but
this implementation is not production-ready and must not proceed to
regression/validation. The next Development-only increment should introduce a
separately testable claim-normalization step that converts each question
requirement into a declarative proposition without inventing an answer.

No probability threshold was tuned. The raw probability for every
claim/evidence pair, selected evidence, model metadata, source-report hash, and
all three policy predictions are stored in `nli_gate_eval.json`.
