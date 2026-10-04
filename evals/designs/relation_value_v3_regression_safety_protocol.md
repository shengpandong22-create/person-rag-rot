# Relation-Value V3 Regression Safety Protocol

## Purpose

This protocol is committed before running regression for the frozen eval-only V3 candidate. It
checks that introducing the candidate and its tooling has not changed the existing retrieval or
Evidence Gate defaults. It does not measure formal V3 binding quality because the 30-row regression
dataset has no human `requested_relation`, `canonical_unit`, or structural-span labels.

Generating such labels from question text during the run would mix an unqualified extractor into
the candidate and produce non-auditable metrics. V3 binding quality therefore remains supported by
its frozen Development evidence; regression is a production-path safety check only.

## Frozen inputs

- V3 candidate manifest:
  `evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json`
- Regression dataset: `evals/datasets/retrieval_regression_v1.jsonl`
- Regression dataset SHA-256:
  `dc980d953d62bf939c6b5c64e366897c1e78957df0f928e6381aeaeece592df2`
- Reference baseline:
  `evals/reports/regression_heading_candidate_ablation/vector_only/retrieval_eval.json`
- Reference baseline SHA-256:
  `883a8abe23c654ed8121bb776c717b7df7f8be84b8863a36f6dc22d54e9da8d9`

## Fixed run configuration

- experiment mode: `vector-only`;
- `top_k=6`, `candidate_k=20`;
- current adjacent filtering and per-document quota of 3;
- candidate expansion: none;
- supplemental consumption: none;
- demand binding policy: none;
- production Evidence Gate: `current_binary_v1`;
- no V3 production wiring and no query-derived V3 labels.

## Hard pass gates

The single safety run must satisfy all of the following:

- Recall@1 >= 0.20;
- Recall@3 >= 0.40;
- Recall@6 >= 0.45;
- MRR >= 0.3017;
- full answerability accuracy >= 0.8824;
- negative rejection accuracy >= 0.50;
- candidate recall@20 >= 0.60;
- average returned candidate count = 6.0;
- P95 retrieval latency <= 1000 ms;
- all 30 rows graded and all human source labels resolved;
- V3 candidate freeze intact before and after the run;
- no production source file imports `evals.relation_value_binding_v3`.

Any failed gate keeps V3 frozen but blocks further safety progression. Passing permits discussion of
a separately declared validation protocol; it does not authorize validation, acceptance, holdout,
or production integration.

## Execution discipline

The protocol and machine-readable thresholds must be committed before the run. The output must
record Git commit, dataset hash, knowledge-base fingerprint, retrieval configuration, latency, and
the before/after V3 freeze checks. Infrastructure failure before a report is produced may be retried;
a completed report is evaluated as-is and must not be tuned against regression failures.
