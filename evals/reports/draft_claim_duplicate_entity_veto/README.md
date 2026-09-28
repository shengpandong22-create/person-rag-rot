# Typed entity-identity veto

## Scope

This eval-only experiment fixes the existing combined typed-feature candidate and adds exactly
one capability: a deterministic entity-identity veto. It does not change NLI, thresholds, the
five normalizers, the frozen 22-pair Development fixture, or production behavior.

- Dataset SHA-256: `927fe6d261e66e84b6b5e126787076f425bb4243b543648d848fa1666e3a09c2`
- Evaluated commit: `62dbbe25287bab983b52768c9c95a589f62b5f9c`
- Inference duration: 32.29 seconds

## Result

| Policy | Precision | Recall | F1 | Accuracy | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NLI baseline | 77.78% | 63.64% | 70.00% | 72.73% | 7 | 2 | 4 | 9 |
| Combined typed features | 84.62% | 100.00% | 91.67% | 90.91% | 11 | 2 | 0 | 9 |
| Combined plus entity veto | 100.00% | 100.00% | 100.00% | 100.00% | 11 | 0 | 0 | 11 |

Entity identity was equal for 15 pairs, different for 5 pairs, and unresolved for 2 pairs. The
veto changed only two positive predictions:

- `dup-019`: rejected `生产组装` versus `默认检索行为`.
- `dup-021`: rejected `Validation` versus `Holdout` despite the same date.

Both were labeled non-duplicates. All 11 duplicate pairs remained accepted, including aliases,
pronouns, negation, numeric equivalence, and date-format equivalence.

## Safety behavior

The veto fires only when both entity identities resolve and differ. An unresolved identity does
not reject an NLI result. This makes the layer conservative with respect to recall and prevents
the earlier strict-subject guard from discarding alias and pronoun positives.

## Decision

The fixed candidate passes the frozen duplicate-pair Development fixture, but this is not a
production acceptance result. The same fixture directly motivated the entity layer, so 100%
must be treated as an in-sample result. Do not integrate automatic deletion yet.

The next valid step is to construct and freeze a new, independently authored duplicate-pair
holdout without inspecting candidate failures during implementation. Run the fixed candidate on
that holdout once. If it passes predeclared precision and recall criteria, the feature can then be
considered for a shadow-mode production diagnostic before any automatic mutation.
