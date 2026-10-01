# Relation-Value Binding V2

## Scope

This Development-only increment changes two isolated capabilities:

1. normalize bounded key/value records when the retrieved source is code-shaped rather than a
   literal Markdown table row;
2. normalize code identifiers and deterministic `min(...)` / `max(...)` bound semantics.

The frozen fixture, retrieval report, production Gate, production retrieval, and RRF configuration
remain unchanged.

## Results

| metric | V1 | V2 |
|---|---:|---:|
| Provenance-aware binding accuracy | 0.7500 | 0.9167 |
| Positive binding detection | 0.6250 | 0.8750 |
| Human-labeled binding recall | 0.6250 | 0.8750 |
| Negative rejection | 1.0000 | 1.0000 |

V2 recovers `rv-t-001` and `rv-c-002`. All four hard negatives remain rejected.

`rv-t-002` remains unresolved because its human-labeled evidence is absent from the frozen
retrieval candidate set. The binder now rejects superficially similar, wrong-provenance chunks
instead of counting them as success. This is a candidate-recall failure, not a binding failure.

## Metric correction

Binding accuracy is now provenance-aware: a positive is correct only when the binding belongs to a
human-labeled retrieved chunk and contains the expected labeled values. Raw presence on an
unrelated chunk is retained as a diagnostic but cannot count as a correct binding.

## Decision

V2 reaches the maximum labeled recall available from the unchanged frozen candidate set (7/8) and
keeps 100% negative rejection. It remains eval-only. Before regression safety validation, the next
step is to test the fixed binder on a new independent binding fixture or declare a qualification
threshold without further tuning on this fixture.

Validation, acceptance, and holdout were not run.
