# Duplicate-pair holdout acceptance protocol

## Fixed candidate

Candidate commit: `62dbbe25287bab983b52768c9c95a589f62b5f9c`

Policy: `combined_with_entity_veto` using the existing five typed normalizers, unchanged
bidirectional NLI decision, and conservative entity-identity veto.

## One-shot protocol

The holdout is authored and frozen before candidate execution. It may be run once for this fixed
candidate. Failures must not be used to edit the candidate and rerun the same holdout. A changed
dataset hash invalidates the result.

## Acceptance criteria

All criteria must pass:

- Precision >= 95%.
- Recall >= 90%.
- F1 >= 92%.
- No false positive in the `entity_identity` category.
- Dataset and freeze-manifest hashes must match at execution time.

Passing permits only a shadow-mode diagnostic recommendation. It does not authorize production
claim deletion or a production Evidence Gate change.
