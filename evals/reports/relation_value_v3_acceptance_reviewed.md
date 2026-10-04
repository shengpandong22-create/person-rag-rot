# Relation-Value V3 Acceptance Review and Adjudication

## Decision

The 36-row independent acceptance dataset completed strict label-blind review, source-grounded
adjudication, and the freeze-stage static audit. All 36 rows now have a distinct reviewer and
`review_state=agreed`. The dataset is qualified to be frozen, but is not yet frozen and is not
authorized for candidate execution.

V3, retrieval, and model inference were not run during construction, blind review, comparison,
adjudication, or audit.

## Review chain

1. The author draft was repaired after a candidate-blind source review rejected its first version.
2. A worksheet was generated with author answerability, roles, semantics, units, values, pair IDs,
   tags, and author metadata removed.
3. A fresh reviewer used only that worksheet, the annotation contract, and original source
   documents to annotate all 36 rows.
4. Hard-label comparison found 19 rows with direct agreement and 17 rows needing adjudication.
5. Every disagreement received a source-grounded decision. Three decisions changed the author
   record: `rva3-006` span type and unsupported percentage aliases, `rva3-025` canonical unit, and
   `rva3-026` modality.
6. The resulting dataset passed the freeze-stage audit with no errors.

## Final composition

- 36 rows: 24 positive and 12 hard-negative;
- 30 single-demand and 6 independent multi-demand rows;
- positive spans: 3 sentence, 7 table, 11 code, 3 genuine bounded multi-span;
- primary roles: 10 exact, 4 derived, 2 range, 3 upper-bound, 4 lower-bound, 1 sequence;
- two negatives for each of relation role, value semantic, subject/predicate, unit binding,
  provenance/structure, and missing-value/false-premise;
- seven source documents represented, with no document contributing more than six positives;
- positive/negative pairs validated as one full and one none row sharing the exact chunk and span
  hash;
- no normalized-question or relation/value-target overlap with existing JSONL datasets.

## Artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| Reviewed dataset | `21f8bc5d87d30dea8941172b184a7a9cff6c6124709611419e661f4212297601` |
| Blind worksheet | `1806d459bac6d527a0d976eabe53f76000656d2693823b136b7724ca28c33676` |
| Blind response | `031f97f6bd1130ad18928038f7467375a4be9609c7ed9906c7a9c9f969c46463` |
| Author/reviewer comparison | `e58deae7a8a85a1e5d58686bc386f9ebbc9e7691046b5dadb7d1e64c3b6258b3` |
| Adjudication decisions | `dbb4292f07b8f221d330e00985ea9b09a5f10a08a83b09b716852a91b008fa29` |
| Freeze-stage audit | `ac6738aa5511ac86f61eae0dcc228e4e8e2a1eb051080bad317dcecdfbb9dabb` |

## Authorization boundary

Passing the freeze-stage audit does not create a freeze manifest and does not authorize acceptance
execution. The next step is a separate commit that creates an immutable dataset/review manifest.
After that, acceptance metrics, thresholds, and the single-run protocol must be declared and
committed before V3 can run once. Production integration remains unauthorized.
