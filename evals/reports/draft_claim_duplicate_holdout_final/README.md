# Duplicate-pair holdout final acceptance

## Protocol

- Fixed candidate: `62dbbe25287bab983b52768c9c95a589f62b5f9c`
- Holdout freeze commit: `f6187a5e857f0ffdd9e942956cfa74f0eaecf93f`
- Dataset SHA-256: `0a264306d2cf3712147115ad8f45a347e1047246070dd58fc3544b3ebfa63a92`
- Cases: 24 (12 duplicate, 12 non-duplicate), disjoint from Development claims
- Candidate runs: 1 of 1
- Runtime: 38.94 seconds

Predeclared requirements were precision >= 95%, recall >= 90%, F1 >= 92%, and no false
positive in `entity_identity`. Passing would permit only a shadow-mode recommendation.

## Fixed-candidate result

Policy: `combined_with_entity_veto`

| Metric | Required | Actual | Result |
|---|---:|---:|---|
| Precision | >= 95% | 100.00% | PASS |
| Recall | >= 90% | 66.67% | **FAIL** |
| F1 | >= 92% | 80.00% | **FAIL** |
| Entity-identity false positives | 0 | 0 | PASS |

Confusion counts: TP 8, FP 0, FN 4, TN 12. Overall acceptance: **FAIL**.

## Missed positive pairs

- `duph-001` (`alias`): after alias normalization, NLI did not equate `不读取` with `不使用`.
- `duph-005` (`pronoun`): the predicate parser could not resolve the subject of `检索器返回...`,
  so `它` was not replaced.
- `duph-006` (`pronoun`): `其职责是...` remained unresolved against `冻结清单保存...`.
- `duph-009` (`negation`): Combined NLI accepted the pair, but entity parsing interpreted
  `Development 不能作为...` as a different subject and vetoed a true duplicate.

These are generalization failures in predicate coverage, pronoun resolution, and entity boundary
parsing. Precision remained conservative, but recall is too low for reliable deduplication.

## Decision

The fixed candidate is rejected. It must not enter shadow mode, production diagnostics, or
automatic claim deletion on the strength of the Development result. This holdout must not be
rerun for a modified candidate and its failures must not be used for iterative tuning against the
same set.

Future work requires a new Development cycle with independently expanded linguistic coverage.
After a materially new candidate is fixed, a new holdout must be authored and frozen before any
further final acceptance.
