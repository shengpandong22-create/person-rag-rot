# Relation-Value V3 Independent Acceptance Protocol

## Purpose

This protocol is committed before the only completed run of the frozen Relation-Value V3
candidate on the independently reviewed acceptance set. It measures whether V3 binds the requested
relation to the correct value, unit, provenance, and structural span while rejecting evidence that
contains tempting but inapplicable numbers.

Passing is necessary, but not sufficient, for production integration. The candidate remains
eval-only throughout this protocol.

## Authorization boundary

Once this protocol and `RELATION_VALUE_V3_ACCEPTANCE_THRESHOLDS.json` are committed, they authorize
one completed acceptance run with the exact frozen inputs. They do not authorize:

- changing V3, the dataset, labels, thresholds, or evaluator after the run starts;
- retrieval, database lookup, LLM/NLI inference, or Evidence Gate changes;
- production wiring, a default-policy change, or a feature flag rollout;
- tuning from acceptance failures or rerunning the same candidate after a completed report.

An attempt ledger must be written before evaluation begins. A retry is permitted only for an
infrastructure failure where no per-case candidate output was persisted or observed. Once any
readable per-case output exists, the run is considered exposed; a completed raw report and
qualification decision are final for this candidate.

## Frozen identity

- Candidate: `relation-value-binding-v3`, implementation identity `d55d2c7`.
- Candidate freeze manifest:
  `evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json`.
- Candidate freeze SHA-256:
  `4c274e604bdd369e01d276398b15cd625fa18ac35d1265054d1fd99665a75e81`.
- Acceptance dataset source commit: `acf89f3`.
- Acceptance dataset:
  `evals/datasets/relation_value_v3_acceptance_v1.jsonl`.
- Acceptance dataset SHA-256:
  `21f8bc5d87d30dea8941172b184a7a9cff6c6124709611419e661f4212297601`.
- Acceptance freeze manifest:
  `evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_FREEZE.json`.
- Acceptance freeze SHA-256:
  `38a7def2ddd2716286262168b1b9d4d037646519b55b0bd7c6e91170844f52b3`.

Both freeze verifiers must pass immediately before and after the run. Any mismatch aborts before
candidate evaluation and does not permit silently refreshing a hash.

## Fixed evaluation path

The evaluator reads the 36 frozen rows and supplies each demand only with its labeled evidence
`span_text` and labeled provenance. It calls the frozen V3 normalization and binding functions
directly. It must not retrieve chunks, read the knowledge-base database, expand the evidence, or
call a model.

There are 43 demands: 31 positive and 12 negative. Six rows contain multiple independent demands.
For a positive demand, a binding is correct only when a single emitted binding matches:

- one complete accepted value set; sequence values preserve order, while other roles compare as
  normalized unordered sets;
- the human relation role and value semantic;
- the canonical unit after only the aliases declared by the dataset;
- the labeled chunk, document logical name, and heading path;
- the labeled structural span type.

A binding that matches only some requested values is incorrect. Every emitted binding that does
not satisfy all fields is spurious. A negative demand passes only when V3 emits no binding. A
positive row passes only when all of its demands pass; this prevents a compound question from
receiving credit for partial coverage.

## Formal metrics

- **Demand accuracy:** correct positive demands plus correctly rejected negative demands divided
  by all 43 demands.
- **Positive demand recall:** positive demands with at least one fully correct binding divided by
  31.
- **Positive row all-demands accuracy:** positive rows whose every demand has a correct binding
  divided by 24.
- **Negative rejection:** reported at demand, row, and each of the six confusion-category levels.
- **Binding precision:** fully correct bindings divided by all emitted bindings. Duplicate correct
  bindings count once after exact canonical deduplication; other duplicates remain spurious.
- **Paired discrimination:** positive/negative pair groups where the positive side is fully correct
  and the negative side emits no binding, divided by 11.
- **Span and role success counts:** number of positive demands with a fully correct binding, grouped
  by the human span type, relation role, and value semantic.
- **Binding volume:** average and maximum emitted bindings per demand.
- **Latency:** per-demand wall-clock candidate time; setup, JSON I/O, and report writing are
  excluded. P50 and P95 are reported, while P95 is gated.

## Hard pass gates

Every machine-readable gate must pass:

- demand accuracy >= 0.9000;
- positive demand recall >= 0.8710 (at least 27/31);
- positive row all-demands accuracy >= 0.8333 (at least 20/24);
- negative demand and negative row rejection = 1.0000 (12/12);
- every negative confusion category rejection = 1.0000 (2/2 each);
- binding precision >= 0.9000;
- paired discrimination >= 0.9091 (at least 10/11);
- average bindings per demand <= 1.5 and maximum <= 3;
- span successes: sentence >= 2/3, table >= 6/7, code >= 9/11, bounded multi-span >= 2/3;
- role successes: exact >= 14/16, derived >= 3/4, range = 2/2, upper-bound >= 3/4,
  lower-bound >= 3/4, sequence = 1/1;
- semantic successes: count >= 9/11, generic >= 8/9, ratio = 1/1, score >= 7/8,
  weight = 2/2;
- 36 rows and 43 demands evaluated, with zero unresolved labels and zero case errors;
- candidate P95 <= 50 ms per demand;
- both freeze manifests intact before and after, and production code does not import V3.

The asymmetric gates are intentional: a small number of conservative misses is tolerated, but a
false binding on any deliberately adversarial negative is not. This matches the safety purpose of
an Evidence Gate component.

## Required outputs

The single run must atomically produce:

1. an attempt ledger containing start time, Git commit, frozen hashes, and terminal status;
2. a raw per-demand report with normalized demand, emitted bindings, latency, exact field-level
   matches, and failure category;
3. a machine-readable qualification result containing every hard-gate check;
4. a short human summary with aggregate metrics, failed cases, limitations, and the final decision.

The report metadata must include the evaluated Git commit, Python and dependency versions,
platform, candidate and acceptance freeze hashes, dataset hash, exact command, start/end time, and
confirmation that retrieval/database/model calls were disabled.

## Decision rule

All hard gates passing yields `accepted_for_production_integration_design=true`. This permits only a
separate production-integration design covering a default-off feature flag, fallback, observability,
and integration tests. It does not switch the production default.

Any failed gate yields `accepted_for_production_integration_design=false`. The candidate and this
acceptance set remain frozen and must not be rerun or tuned from the failures. A successor requires
a new candidate identity, non-blind Development work, safety validation, and a newly constructed
independent acceptance set.
