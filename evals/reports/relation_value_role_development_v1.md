# Relation-Value V3 Semantic-Role Development

## Scope

This non-blind Development fixture contains six paired semantic-confusion scenarios. Each pair keeps
the evidence and number pressure fixed while changing the requested relation:

- lexical coverage threshold vs retrieval-accuracy guarantee;
- RRF aggregate score vs retrieval latency;
- profile weight vs confidence threshold;
- derived mastery output vs claimed population average improvement;
- dimension score range vs total-score range;
- coverage priority vs retry count.

The fixture is intended for V3 design and unit-level diagnosis. It is not frozen acceptance data.

## Result

| metric | result |
|---|---:|
| Accuracy | 1.0000 |
| Positive value recall | 1.0000 |
| Negative rejection | 1.0000 |
| Average bindings per case | 1.0000 |
| Maximum bindings per case | 3 |

All six positive/contrast pairs pass. In particular, identical numeric evidence no longer succeeds
when the requested metric, predicate, output entity, or modality differs.

## Duplicate-binding reduction

On the original relation-value Development report:

| diagnostic | before | after |
|---|---:|---:|
| Average bindings per case | 4.1667 | 2.6667 |
| Maximum bindings in one case | 28 | 13 |
| Maximum bindings per chunk | unbounded | 3 |

V3 only merges bindings with the same provenance, role, semantic type, and value tuple. It no longer
discards a larger value set merely because a shorter overlapping span exists. Derived results use an
explicit `DERIVED_VALUE` role and prefer spans containing output markers and deeper assignment
chains, preventing inputs or intermediate values from replacing the final result.

## Cross-check on original Development

- Provenance-aware binding accuracy: 0.9167
- Human-labeled binding recall: 0.8750
- Negative rejection: 1.0000

The remaining miss is still the known candidate-recall failure `rv-t-002`.

## Decision

Do not freeze V3 yet. The semantic-role fixture and original Development now pass their intended
checks, but a candidate freeze should first declare explicit thresholds for duplicate volume,
per-role recall, and negative rejection. The spent independent blind fixture was not read or run.
