# Relation-Value Binding V3 Design

## Scope

V3 is an eval-only typed binding candidate. It does not replace the production Evidence Gate or
retriever and does not modify V2. Development uses only the original non-blind relation-value
fixture and its existing frozen retrieval report.

## Typed intermediate representation

V3 separates five concerns that V2 mixed into lexical matching:

1. `RelationRole`: exact value, derived value, range, upper bound, lower bound, or sequence;
2. `ValueSemantic`: ratio, score, count, duration, rate, accuracy, coverage, weight, or generic;
3. canonical unit and unit aliases;
4. `EvidenceProvenance`: chunk id, document logical name, and heading path;
5. structural span: table row, code statement, bounded record, sentence, or bounded multi-span.

A binding is emitted only when role shape, value semantic, unit, relation terms, and a local span
agree. Values from separate chunks are never joined.

`DERIVED_VALUE` distinguishes formula inputs and intermediate values from the requested aggregate or
output. Equivalent overlapping spans are collapsed by provenance, role, semantic type, and value
tuple. Different value tuples are preserved, and each chunk contributes at most three diagnostic
bindings.

## Safety boundary

Guarantee claims require explicit guarantee language in the evidence. An evidence span describing
an 18% lexical coverage threshold therefore cannot support an 18% retrieval-accuracy guarantee.
Range parsing also treats `0-5` as two positive endpoints rather than a positive and negative value.

## Evaluation discipline

- Development dataset: `retrieval_relation_value_development_v1.jsonl` only;
- candidate input: existing frozen retrieval output;
- independent blind fixture: not run and not used for tuning;
- regression, validation, acceptance, and holdout: not run.
