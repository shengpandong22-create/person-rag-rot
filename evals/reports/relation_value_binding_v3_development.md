# Relation-Value Binding V3 Development Result

## Result

| metric | V2 | V3 |
|---|---:|---:|
| Provenance-aware binding accuracy | 0.9167 | 0.9167 |
| Human-labeled binding recall | 0.8750 | 0.8750 |
| Negative rejection | 1.0000 | 1.0000 |

Correct positive bindings by declared span type:

- `sentence_span`: 2
- `table_row`: 1
- `code_statement`: 2
- `bounded_multi_span`: 2

The only unresolved positive remains `rv-t-002`, whose labeled evidence is absent from the fixed
candidate set. V3 therefore reaches the same candidate-limited ceiling as V2 on this Development
fixture.

## Incremental value

Although aggregate recall is unchanged, V3 makes the decision chain inspectable and independently
testable. It fixes two important representation errors:

- Markdown range `0-5` is represented as endpoints `0` and `5`;
- lexical coverage threshold evidence cannot satisfy an accuracy-guarantee demand.

Every result now retains the typed demand, local structural span, values/unit, and complete chunk
provenance.

## Decision

Keep V3 eval-only. Development parity plus deterministic semantic safety is sufficient to continue
V3 design work, but not sufficient for regression or a new blind acceptance run. The next step
should add non-blind Development cases for semantic-role confusion and reduce duplicate candidate
bindings before declaring a new candidate freeze.

The spent independent blind fixture was not run. Regression, validation, acceptance, and holdout
were not run.
