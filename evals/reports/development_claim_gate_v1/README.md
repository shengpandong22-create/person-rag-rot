# Development Claim-Level Gate v1

This phase introduces auditable claim-level diagnostics without changing the
production Evidence Gate. Each question is decomposed into claims carrying:

- requirement type (`fact`, exact value, date, guarantee, future version, or
  comparison);
- status (`supported`, `unsupported`, `contradicted`, or `unknown`);
- supporting chunk IDs;
- explicit decision reasons.

`contradicted` is part of the contract but is not guessed by v1 deterministic
rules. Emitting it requires reliable entailment/contradiction evidence.

## Aggregate result

| Metric | Current binary | clause_demand_v1 | claim_gate_v1 |
|---|---:|---:|---:|
| Full acceptance | 0.9333 | 0.9333 | 0.9333 |
| Partial boundary detection | 0.0000 | 0.9000 | 0.9000 |
| None rejection | 0.2000 | 0.4571 | 0.4571 |
| Macro accuracy | 0.3778 | 0.6778 | 0.7349 |

Claim-level aggregation improves macro accuracy because cases with no
supported claim become `none` rather than an undifferentiated `partial`. It
does not improve the absolute none rejection rate beyond the earlier
clause/demand candidate.

## Single-capability ablation

| Deterministic capability only | Full accept | Partial boundary | None reject | Macro accuracy |
|---|---:|---:|---:|---:|
| exact value | 0.9333 | 0.9000 | 0.2571 | 0.6800 |
| date | 0.9333 | 0.0000 | 0.2286 | 0.3778 |
| guarantee | 0.9333 | 0.2000 | 0.2571 | 0.4444 |
| future version | 0.9333 | 0.0000 | 0.2857 | 0.3778 |
| comparison | 0.9333 | 0.1000 | 0.2286 | 0.4111 |

The exact-value check explains most partial-boundary gains, but none of the
individual deterministic capabilities produces adequate hard-negative
rejection.

## Why deterministic matching is insufficient

Across 79 extracted claims, 52 are marked supported, 21 unknown, and six
unsupported. Eighteen `fact` claims from `none` cases still look supported to
the lexical checker. Six exact-value claims from `none` cases also look
supported because an unrelated number anywhere in related evidence is not the
same as the requested value.

This is the boundary of deterministic signal matching: it can detect missing
surface forms, but it cannot reliably determine whether evidence entails the
specific claim, contradicts its premise, or merely discusses the same topic.

## Decision

Do not promote `claim_gate_v1` to regression/validation selection as a new
production candidate: its 0.4571 none rejection rate is below the 0.70 target.
The claim data contract and reports are retained as the input/output boundary
for the next experiment.

The evidence supports evaluating a semantic entailment layer (NLI or a
Cross-Encoder-style claim/evidence classifier) behind an eval-only interface.
That experiment must compare deterministic-only versus semantic-only versus
combined policies on Development before any regression or validation run. The
old holdout must not be reused for tuning or acceptance.
