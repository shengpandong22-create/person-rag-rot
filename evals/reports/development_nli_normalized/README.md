# Development NLI with Safe Claim Normalization

This experiment adds a deterministic, independently tested normalization step
before NLI. It converts only closed yes/no questions (`是否`, `能否`, etc.) to
positive declarative hypotheses. Open questions (`多少`, `为什么`, `如何`,
etc.) remain unresolved rather than receiving an invented answer.

## Normalization coverage

- total extracted claims: 79
- safely normalized claims: 3
- unresolved open claims: 76
- normalization coverage: 3.8%
- NLI pairs: 12
- CPU inference time: 29998.3177 ms

Only three Development requirements are closed propositions. The rest request
an answer value, explanation, list, comparison, or procedure. Those questions
cannot become concrete truth-valued hypotheses until a candidate answer exists.

## Result

| Policy | Full accept | Partial boundary | None reject | Macro accuracy |
|---|---:|---:|---:|---:|
| deterministic-only | 0.9333 | 0.9000 | 0.4571 | 0.7349 |
| semantic-only | 0.0000 | 0.0000 | 1.0000 | 0.3333 |
| combined with safe fallback | 0.9333 | 0.9000 | 0.4571 | 0.7349 |

The semantic-only row is coverage-limited, not a useful candidate: unresolved
claims become `unknown`, so it rejects every answer. The combined policy safely
falls back to deterministic decisions for unresolved claims and therefore
matches the deterministic baseline exactly.

## Architectural conclusion

For open-domain and open-ended RAG questions, query normalization is not enough
to create NLI hypotheses. The system must first produce candidate answer claims,
then verify each concrete assertion against retrieved evidence:

```text
question + evidence
  -> draft answer / structured candidate claims
  -> claim-to-evidence NLI
  -> supported / contradicted / unknown
  -> bounded answer or rejection
```

This is not permission to let an unverified draft reach the user. The draft is
an internal intermediate representation, and only verified claims may enter
the final response.

## Decision

Do not run regression or validation for this normalization approach; it adds no
Development improvement. The next eval-only increment should define a typed
`DraftClaim` contract and a deterministic fixture-backed evaluator before
introducing any LLM-based claim extraction. Production defaults and the old
holdout remain untouched.

Raw normalization decisions, hypotheses, NLI probabilities, source-report
hash, and policy outputs are stored in `nli_gate_eval.json`.
