# Relation-Value Binding V1

## Protocol

The new frozen relation-value Development fixture was not used to implement the earlier presence
baseline. The sequence was:

1. run unchanged vector-only + heading-shadow + consumption=none retrieval;
2. run the existing value/relation presence diagnostic as a blind baseline;
3. implement a fixture-backed binder whose runtime inputs are only normalized relation, unit, and
   evidence span type;
4. keep `expected_values` and human relevant sources exclusively for scoring.

No production Gate or retrieval behavior was changed.

## Blind presence baseline

The existing presence interpretation selected nine supplemental chunks but none was human-labeled
evidence. Candidate precision was 0 and combined retrieval recall remained 0.7500.

## Typed binder result

| metric | result |
|---|---:|
| Binding accuracy | 0.7500 |
| Human-labeled binding recall | 0.6250 |
| Negative rejection | 1.0000 |

The binder rejects all four hard negatives and correctly binds five of eight positives. It keeps
relation terms, values/units, chunk provenance, and the declared structural span together.

Three positive failures remain:

- `rv-t-001`: low-confidence profile weight table row;
- `rv-t-002`: review score-boundary table row;
- `rv-c-002`: learning-rate hard-limit code statement.

The two table failures show that Markdown table structure is not preserved uniformly in retrieved
chunk text. The code failure shows that lexical relation normalization is still incomplete.

## Decision

Keep the binder eval-only and do not run regression. The 100% negative rejection is encouraging, but
62.5% labeled binding recall is below qualification. The next increment should diagnose structural
normalization for table rows and code identifiers on this fixture without weakening the negative
contract or changing retrieval.

Validation, acceptance, and holdout were not run.
