# Relation-Value V3 Independent Acceptance Dataset Design

## Status and boundary

This document defines the annotation contract and planned composition for a new independent V3
acceptance dataset. It does not create, freeze, score, or authorize execution of that dataset.

Until the completed dataset and review record are frozen, the following are prohibited:

- running V3 on any proposed acceptance row or evidence text;
- using V3 output to select, rewrite, remove, or relabel a row;
- copying questions or relation/value targets from Development, regression, validation, holdout, or
  previous acceptance/blind fixtures;
- setting acceptance thresholds after observing candidate output;
- changing the frozen V3 candidate implementation.

Human annotators may inspect the knowledge source and existing datasets for overlap prevention, but
must derive every acceptance label directly from the cited source evidence.

## Dataset purpose

The dataset must answer one question: given a human-specified relation demand and human-cited
evidence, does frozen V3 bind the correct relation role, value semantics, value set, unit,
provenance, and structural span while rejecting plausible but incorrect bindings?

Retrieval quality is outside the primary score. Acceptance evidence is supplied as a fixed,
human-labeled chunk or bounded text record so that candidate recall cannot mask binding quality.
Retrieval remains covered by the frozen regression and validation safety runs.

## Row contract

The planned file is `evals/datasets/relation_value_v3_acceptance_v1.jsonl`. Comment lines may begin
with `//`; every other line must be one JSON object with these fields:

| Field | Type | Rule |
| --- | --- | --- |
| `id` | string | Unique `rva3-###`; IDs carry no expected label. |
| `split` | string | Must be `acceptance`. |
| `label_origin` | string | Must be `human`. |
| `question` | string | Natural user request; must not disclose expected values artificially. |
| `answerability` | string | `full` when every required demand is supported; otherwise `none`. |
| `confusion_type` | string or null | Required for hard negatives; null for ordinary positives. |
| `demands` | array | One or more typed demand annotations defined below. |
| `evidence` | array | One or more immutable human-cited evidence records defined below. |
| `relevant_sources` | array | Stable logical document and heading labels for overlap/audit checks. |
| `negative_reason` | string or null | Required when all demands have `expected_binding=false`. |
| `annotation` | object | Author/reviewer identity aliases, review state, and rationale. |
| `tags` | array | Composition facets only; never used as runtime labels. |

### Typed demand annotation

Each `demands` item must contain:

- `demand_id`: row-local stable identifier;
- `requested_relation`: concise statement of the requested subject and predicate;
- `relation_role`: one of `exact`, `derived_value`, `range`, `upper_bound`, `lower_bound`,
  `sequence`;
- `value_semantic`: one of `generic`, `ratio`, `score`, `count`, `duration`, `rate`, `accuracy`,
  `coverage`, `weight`;
- `canonical_unit`: normalized unit or null when the source quantity is unitless;
- `expected_binding`: boolean;
- `accepted_value_sets`: a non-empty array of equivalent ordered string arrays for a positive;
  an empty array for a negative;
- `evidence_ids`: exact evidence records that support the binding; empty for an unsupported demand;
- `required_relation_terms`: human-selected subject/predicate terms that must be represented in the
  bounded evidence;
- `modality`: `fact` or `guarantee`;
- `rationale`: a short source-grounded explanation of why the binding is valid or invalid.

`accepted_value_sets` distinguishes equivalent renderings without accepting a semantically
different number. For example, `["18%"]` and `["0.18"]` may both be allowed only if the source and
unit normalization make that equivalence explicit. Ordered values are required for `sequence`;
range endpoints must be stored low then high. Derived results must contain the final output only,
not every intermediate operand.

### Evidence annotation

Each `evidence` item must contain:

- `evidence_id`: row-local stable identifier;
- `chunk_id`: database chunk identifier captured at freeze time;
- `document_logical_name` and full `heading_path`;
- `span_type`: one of `sentence_span`, `table_row`, `code_statement`, `bounded_multi_span`;
- `span_text`: the minimal sufficient verbatim evidence, including required headers or neighboring
  clauses when necessary for meaning;
- `span_sha256`: SHA-256 of UTF-8 `span_text` after line endings are normalized to LF;
- `source_content_hash`: frozen document content hash;
- `supports_demand_ids`: demand IDs actually supported by this evidence.

The span must be bounded structurally, not merely shortened. A table row includes the header when
the header determines column semantics. A code statement includes the controlling condition when
the value depends on it. A cross-sentence record includes only the adjacent sentences required to
bind subject, predicate, value, and unit.

## Annotation rules

1. Label the requested relation before recording any value. This prevents choosing a relation to
   fit a nearby number.
2. Record the semantic role independently from surface operators. A threshold is not an accuracy
   guarantee; an input operand is not a derived output; a per-dimension score is not a total score.
3. Bind value and unit to the same subject/predicate within the annotated structural boundary.
4. For positives, every expected value must be present or unambiguously derivable inside the cited
   evidence. External arithmetic is allowed only for a source-explicit derived formula and must be
   documented in `rationale`.
5. For negatives, `accepted_value_sets` and `evidence_ids` are empty even when the evidence contains
   tempting numbers. The rationale names the exact role, subject, predicate, unit, provenance, or
   modality mismatch.
6. `guarantee` is valid only when the source makes an explicit guarantee/commitment. Observations,
   examples, thresholds, and configuration defaults are `fact` and cannot satisfy it.
7. Unit aliases are accepted only through a pre-recorded equivalence such as `秒` and `1000毫秒`;
   dimensional changes or missing units are not aliases.
8. A multi-demand row is `full` only when all mandatory demands bind correctly. Unsupported mixed
   rows are represented as hard negatives with separate positive and negative demands, not by
   silently dropping the unsupported clause.
9. Diagnostic keywords, candidate output, retrieval scores, and case IDs must never determine a
   label.

## Planned composition

The dataset contains exactly 36 rows: 24 positive rows and 12 hard-negative rows. It includes 30
single-demand rows and 6 multi-demand rows. No row is copied or paraphrased from an existing split.

### Positive coverage: 24 rows

| Dimension | Required distribution |
| --- | --- |
| Structural span | 6 sentence, 6 table, 6 code, 6 bounded multi-span |
| Relation role | 6 exact, 4 derived, 4 range, 3 upper bound, 3 lower bound, 4 sequence |
| Unit behavior | at least 8 explicit units, 4 unitless values, 4 accepted unit-alias/conversion cases |
| Binding complexity | at least 6 multi-value and all 6 planned multi-demand rows |
| Provenance | at least 6 documents; no document contributes more than 6 positive rows |

Each positive row contributes to exactly one primary structural-span bucket and one primary
relation-role bucket. Secondary tags may describe additional properties but do not alter counts.

### Hard-negative coverage: 12 rows

| Confusion type | Rows | Required construction |
| --- | ---: | --- |
| `relation_role` | 2 | Same or nearby value, wrong threshold/range/guarantee role |
| `value_semantic` | 2 | Same numeric form, wrong metric meaning |
| `subject_predicate` | 2 | Correct-looking value attached to the wrong entity or predicate |
| `unit_binding` | 2 | Incompatible or missing unit; not a valid alias conversion |
| `provenance_structure` | 2 | Value exists outside the valid row/condition/bounded span |
| `missing_value_false_premise` | 2 | In-domain request whose claimed value is absent or unsupported |

At least 10 of the 12 negatives must contain one or more plausible numeric distractors. At least 8
must be paired with a positive row that uses the same evidence but asks for a different valid
relation. Pair membership is metadata for auditing only and must not be visible to the candidate.

## Independence and leakage checks

Before review, an offline validator must reject:

- exact or normalized-question overlap with every existing Development, regression, validation,
  holdout, blind, and acceptance dataset;
- duplicate `(document_logical_name, heading_path, requested_relation, accepted_value_sets)` tuples;
- reuse of a prior relation/value target under a superficial question rewrite;
- duplicate acceptance rows or duplicated positive/negative pair members;
- missing or unresolved document paths, heading paths, content hashes, or span hashes.

Heading reuse alone is allowed only when the new relation/value target is distinct and the reviewer
documents why this is not target leakage. Existing holdout contents must not be inspected or changed
beyond the repository's automated overlap checks.

## Human review workflow

1. An author creates each row from source evidence without running V3.
2. A reviewer independently assigns relation role, value semantics, unit, expected values,
   provenance, and structural span before seeing the author's completed labels.
3. A comparison tool reports disagreements without revealing V3 output.
4. Author and reviewer adjudicate from the source. The final record stores `review_state=agreed` and
   a concise adjudication note; unresolved rows are removed before freeze.
5. A separate audit verifies all composition quotas, hashes, path resolution, overlap checks, and
   positive/negative counts.
6. The reviewed dataset and audit report are committed while V3 execution remains prohibited.

## Freeze and later authorization sequence

After review, create a manifest that fixes the dataset path/hash, case IDs, counts, composition
matrix, evidence span hashes, source document hashes, annotation-contract version, and audit-report
hash. Freezing the data still does not authorize execution.

Next, predeclare and commit acceptance metrics and pass thresholds. At minimum they must separately
score exact binding accuracy, positive value recall, hard-negative rejection, role accuracy, unit
accuracy, provenance accuracy, structural-span accuracy, multi-demand all-or-nothing accuracy, and
binding-count limits. Then commit a single-run protocol referencing the frozen candidate and frozen
dataset. Only that later protocol can authorize one completed acceptance run.

Passing acceptance may permit production-integration design; it does not directly switch the
production default. Failure freezes the result and returns work to a newly identified Development
candidate rather than tuning V3 on acceptance cases.
