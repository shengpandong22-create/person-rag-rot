# Value/Relation Evidence-Presence Diagnostics

## Scope

This is an offline retrieval diagnostic over two frozen Development fixtures. It reads supplemental
chunk content from the database and records typed presence features without consuming candidates or
changing the primary Top-6. The Evidence Gate remains paused and unchanged.

Per supplemental candidate the report records:

- whether the question requires a numeric/value answer;
- explicit values requested and covered;
- requested units and covered aliases;
- whether any numeric value is present;
- core relations requested and covered;
- the candidate chunk id and whether it resolves to human-labeled evidence.

## First fixed interpretation

For diagnostic measurement only, a candidate is presence-positive when it contains the requested
value/unit signals and, when a known relation is requested, also contains that relation. Only the
first seven supplemental candidates are considered. No threshold sweep was performed.

| fixture | trigger rate | selected chunks | relevant chunks | candidate precision | combined recall |
|---|---:|---:|---:|---:|---:|
| Demand-binding Development | 0.3333 | 10 | 1 | 0.1000 | 0.7000 |
| Trigger Development | 0.5000 | 41 | 1 | 0.0244 | 0.2500 |

## Findings

The feature contract is now observable and provenance-backed, but the first deterministic
interpretation is not a viable trigger:

- technical chunks contain many incidental constants, ranks, percentages, and example values;
- exact relation words are brittle under paraphrase, while generic relations occur in unrelated
  sections;
- value presence alone cannot establish that a value answers the requested relation;
- combined recall falls below the heading-only fixed upper bound on both fixtures.

## Decision

Keep the value/relation presence fields as offline diagnostics, but do not add a consumption rule to
the eval runner and do not run regression. The next useful increment is typed local binding between
`requested relation -> value/unit` inside one table row, code statement, or bounded sentence span,
with the matched chunk id retained. That work should first receive its own independent Development
fixture; reinterpreting these same frozen rows repeatedly would become another form of tuning.

Regression, validation, acceptance, and holdout were not run.
