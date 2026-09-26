# Evidence Gate Calibration Design

## Scope

This phase calibrates evidence sufficiency on the human-labelled development
set. It does not alter retrieval, ranking, chunking, embeddings, production
assembly, or the current production default. Regression remains a safety
check, validation remains the later selection set, and holdout is not opened or
run during calibration.

## Current decision and observed failure

`AnswerService.assess_evidence()` currently:

1. keeps every returned chunk that independently passes lexical support;
2. accepts the question when at least one supported chunk remains and the
   first supported chunk score is at least `retrieval_min_score`.

On the 60-case development baseline this accepts 28 of 35 `none` cases. The
failure is expected from the decision shape: topical or lexical relatedness is
treated as answer sufficiency. It does not represent missing requested values,
unsupported conclusions, future-version claims, false premises, or a question
whose second clause is not covered.

Raising only `retrieval_min_score` is not a sound first calibration method.
Under vector-only retrieval, returned scores are cosine-like vector scores,
while the production default mode uses a different composite score. A single
threshold sweep across those score domains would conflate retrieval-mode score
semantics with evidence quality.

## Metric correction required before selection

The dataset has three answerability classes but the production Gate returns a
boolean. The existing `partial_answerability_accuracy` reports acceptance of a
partial case as correct. That is only an acceptance rate; it does not prove
that the uncovered part was detected or bounded.

Calibration reports will therefore keep the legacy field for compatibility
and add these explicit metrics:

- `full_acceptance_rate`: full cases accepted;
- `none_rejection_rate`: none cases rejected;
- `partial_acceptance_rate`: partial cases accepted by the binary Gate;
- `partial_boundary_detection_rate`: partial cases classified as partial by
  an evaluation-only three-way decision;
- macro accuracy and confusion matrix for `full / partial / none`;
- rejection rate grouped by `negative_reason`;
- false-acceptance and false-rejection case lists.

Until production supports a bounded partial-answer path, the safe binary
mapping is `full -> accept`, `partial|none -> reject`. A later product decision
may map `partial` to a bounded answer that explicitly identifies missing
claims, but that behavior is outside this calibration phase.

## Evaluation-only interface

Introduce an immutable diagnostic result without changing the existing public
return value:

```python
EvidenceAssessment(
    decision: full | partial | none,
    production_sufficient: bool,
    supported_chunk_ids: tuple[UUID, ...],
    top_supported_score: float | None,
    query_terms: tuple[str, ...],
    specific_query_terms: tuple[str, ...],
    covered_terms: tuple[str, ...],
    uncovered_terms: tuple[str, ...],
    coverage_ratio: float,
    candidate_assessments: tuple[CandidateEvidenceAssessment, ...],
    rejection_reasons: tuple[str, ...],
)
```

`assess_evidence()` must continue delegating to the current policy and return
exactly `(supported_candidates, sufficient)`. The richer method is used only
by the eval runner. A behavioral-equivalence unit test will compare both paths
over representative English, Chinese, mixed-language, numeric, false-premise,
and multi-clause questions.

## Features to record before changing a rule

For each question and each of the first three chunks, record:

- raw and specific query terms;
- covered and uncovered terms;
- specific-term coverage count and ratio;
- heading-only versus content coverage;
- numeric tokens requested and matched;
- interrogative demand markers such as exact value, date, quantity, guarantee,
  comparison, future version, and implementation detail;
- clause-level coverage for coordinated questions;
- retrieval score and score type;
- the current lexical-support verdict and reason.

These are diagnostics, not new production heuristics. Their distributions must
first be compared across full, partial, and none labels.

## Calibration experiment sequence

### E0: frozen current behavior

Reproduce the existing vector-only development baseline. No parameter changes.

### E1: diagnostic replay

Capture the features above while asserting byte-for-byte equivalent production
decisions. Use this to identify separable signals and failure clusters.

### E2: one-variable rule ablations

Replay saved diagnostics without retrieving again. Evaluate independently:

1. minimum specific-term count;
2. minimum specific-term coverage ratio;
3. numeric/value-demand coverage;
4. clause coverage;
5. score threshold within one fixed retrieval mode.

Each row changes exactly one rule relative to E0. This avoids crediting a
compound heuristic without knowing which part helped.

### E3: constrained combinations

Combine only E2 rules that improve hard-negative rejection without violating
the full-case safety floor. Record the entire candidate set, not only the
winner.

### E4: regression and validation

Run the chosen development candidate on regression first. If it passes the
safety gates, run it once on validation for selection. Do not run holdout.

## Selection gates

A candidate is eligible only when all conditions hold:

- development none rejection improves materially over 0.20;
- development full acceptance is at least 0.90;
- no negative-reason group regresses below the E0 baseline;
- regression Recall@6 and MRR do not regress (the Gate must not change
  retrieval results);
- regression full acceptance loses at most one case and every loss is listed;
- partial boundary detection is reported separately and is not disguised as
  ordinary acceptance;
- production-default equivalence tests pass unless a later, explicit change is
  approved.

The first target is diagnostic discrimination, not an arbitrary universal
threshold. With only 15 full and 35 negative development cases, metric changes
must always include raw counts and case IDs.

## Reproducibility

Every calibration result records:

- git commit and dirty state;
- dataset path and SHA-256;
- knowledge-base fingerprint and document hashes;
- embedding provider, model, and dimension;
- retrieval mode, top-k, candidate-k, and score type;
- policy name and all policy parameters;
- confusion matrix, group metrics, latency, and run time;
- source report SHA-256 when using offline replay.

The development set is versioned but not frozen: intentional label changes
must change its hash and invalidate prior calibration runs. Validation and
holdout freeze rules remain unchanged.

## Implementation boundary

The first implementation increment consists only of diagnostic assessment,
explicit three-way evaluation metrics, offline replay input/output, and unit
tests proving current production behavior is unchanged. It must not modify
`retrieval_min_score`, lexical thresholds, Evidence Gate behavior, or service
wiring. Rule candidates are implemented as evaluation policies only. A
production policy change requires a separate review after development and
validation evidence is available.
