# Relation-Value V3 Validation Safety Protocol

## Purpose

This protocol is committed before any validation run for the frozen eval-only V3 candidate. It
checks that the candidate and its evaluation tooling remain safe across the frozen validation
split without changing the existing retrieval or Evidence Gate path.

The validation rows do not contain human `requested_relation`, `canonical_unit`, expected value,
or structural-span labels. Therefore this protocol does not claim to measure formal V3 binding
quality. Query-derived or model-generated labels are prohibited during the run because they would
introduce an unqualified evaluator after candidate freeze.

## Authorization boundary

This protocol authorizes one completed validation safety report only after this protocol and its
machine-readable thresholds are committed. It does not authorize:

- production integration or a production default change;
- acceptance, holdout, or independent blind-fixture execution;
- reuse of an earlier blind fixture;
- V3 implementation, threshold, or dataset changes after observing validation;
- generation of proxy relation/value labels from validation questions.

An infrastructure failure before a report is created may be retried with the identical committed
configuration. A completed report is final for this candidate and must be evaluated as-is.

## Frozen inputs

- Candidate manifest: `evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json`.
- Validation manifest: `evals/datasets/VALIDATION_FREEZE.json`.
- Validation dataset: `evals/datasets/retrieval_validation_v1.jsonl`.
- Validation dataset SHA-256:
  `4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`.
- Validation freeze manifest SHA-256:
  `e04fd574249bc4cc72a7e7c8a5eb9e79cc3341d9e66bad5c78e0b4fbe82abd32`.
- Reference report:
  `evals/reports/validation_heading_candidate_ablation/vector_only/retrieval_eval.json`.
- Reference report SHA-256:
  `87452f123fc0a78182cde56bf6432648c777f83a34d3051e32c2ef40e1a31fcf`.

## Fixed run configuration

- experiment mode: `vector-only`;
- `top_k=6`, `candidate_k=20`;
- current adjacent filtering and per-document quota of 3;
- query strategy: original;
- candidate expansion: none;
- supplemental consumption: none;
- demand binding policy: none;
- production Evidence Gate: `current_binary_v1`;
- no V3 production wiring and no query-derived V3 labels.

This deliberately matches the regression safety path. Enabling V3 on unlabeled validation rows
would produce output without an auditable correctness target and is outside this protocol.

## Hard pass gates

The completed safety report must satisfy every gate below:

- Recall@1 >= 0.3529;
- Recall@3 >= 0.5294;
- Recall@6 >= 0.7059;
- MRR >= 0.4853;
- full answerability accuracy = 1.0;
- partial answerability accuracy = 1.0;
- negative rejection accuracy = 1.0;
- candidate recall@20 >= 0.8824;
- average returned candidate count = 6.0;
- P95 retrieval latency <= 1000 ms;
- all 22 rows graded and all 17 human relevant-source labels resolved;
- validation dataset and validation freeze manifest hashes unchanged;
- V3 candidate freeze intact before and after the run;
- no production source file imports `evals.relation_value_binding_v3`.

## Decision rule

All gates passing yields `safe_for_next_protocol=true`. That result only permits drafting a new,
separately committed acceptance protocol backed by appropriately labeled independent data. It does
not itself qualify V3 for production.

Any failed gate yields `safe_for_next_protocol=false`. The V3 candidate remains frozen, and the
failure may be diagnosed but must not be used to tune V3 against validation. A changed candidate
must receive a new identity, repeat Development qualification and regression safety, and obtain a
new validation protocol before another validation run.

## Required report metadata

The report and qualification decision must record the evaluated Git commit, dataset and manifest
hashes, knowledge-base fingerprint and document hashes, embedding provider/model/dimension, exact
retrieval and Gate configuration, runtime, latency, candidate counts, candidate-freeze checks, and
production-isolation result.
