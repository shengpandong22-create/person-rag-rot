# Relation-Value V3 Acceptance First-Pass Annotation

> Historical note: this first-pass report has been superseded by the independently reviewed and
> adjudicated result in `evals/reports/relation_value_v3_acceptance_reviewed.md`. Its original draft
> hash is retained here only as audit history and must not be treated as the current dataset hash.

## Status

The first-pass human annotation draft contains 36 rows and passes the static draft audit. It is not
reviewed, adjudicated, frozen, or authorized for candidate execution.

- Dataset: `evals/datasets/relation_value_v3_acceptance_v1.jsonl`.
- Dataset SHA-256:
  `978a90c5f5f91e8c01609cd2a00d71704574dacaeaa8ed64645df493f275f3f7`.
- Audit: `evals/reports/relation_value_v3_acceptance_draft/audit.json`.
- Annotation state: every row has `author=author-pass-1`, `reviewer=null`, and
  `review_state=draft`.
- Candidate execution: false.

## Static audit result

All draft-stage structural checks passed:

- 36 total rows: 24 positives and 12 hard negatives;
- 30 single-demand and 6 multi-demand rows;
- 6 positive rows for each structural span type;
- role distribution: 6 exact, 4 derived, 4 range, 3 upper-bound, 3 lower-bound, 4 sequence;
- two hard negatives for each of the six declared confusion types;
- seven source documents represented, with no more than six positives from one document;
- unit, unitless, alias/conversion, multi-value, numeric-distractor, and paired-negative quotas met;
- question and relation/value targets do not overlap the repository's existing JSONL datasets;
- evidence spans exist in source files and all span/file hashes match;
- every row resolves to a real knowledge-base chunk, heading path, and database document hash.

## Remaining work

An independent reviewer must assign role, value semantics, units, values, provenance, and span
boundaries without seeing candidate output. Disagreements must be adjudicated from source evidence.
Only rows with a distinct reviewer and `review_state=agreed` may pass the freeze-stage audit.

Do not run V3, create a freeze manifest, declare acceptance thresholds, or execute acceptance while
this report remains a first-pass draft.
