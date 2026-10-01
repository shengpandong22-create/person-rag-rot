# Semantic Recall and Demand-Binding Development Evaluation

## Scope

- Dataset: `retrieval_trigger_development_v1.jsonl` (frozen)
- Production retrieval and Evidence Gate defaults: unchanged
- Regression, validation, and holdout: not run
- Retrieval baseline: `vector-only`, `top_k=6`, `candidate_k=20`
- Retrieval candidate: independent `semantic-query-shadow`, consumption=`none`
- Gate candidate: `heading-shadow`, consumption=`none`, demand binding=`numeric-local-v1`

## Retrieval result

The semantic query view used the fixed BGE query instruction
`为这个句子生成表示以用于检索相关文章：{query}`. Its candidates were recorded in an
independent shadow channel and were excluded from RRF, heuristic reranking, diversity filtering,
and the primary Top-6.

| metric | prior heading-shadow reference | semantic shadow |
|---|---:|---:|
| Recall@6 | 0.1667 | 0.1667 |
| candidate recall@20 | 0.5833 | 0.5833 |
| primary@6 + supplemental@20 | 0.4167 | 0.1667 |
| average semantic supplemental candidates | n/a | 2.5833 |

The primary Top-6 metrics are identical, confirming monotonic safety. The semantic shadow did not
recover a new labeled source, including the low-overlap paraphrase cases. This fixed semantic query
view is therefore **not qualified** for further datasets. Its first-run P95 contains embedding model
warm-up and is not used as a comparative latency conclusion.

## Gate result

`numeric-local-v1` requires an explicit requested value, or an implicit numeric answer, to occur in
the same evidence sentence as the requested unit and all recognized core predicates. Section
numbers, formula constants, and values attached to another predicate do not satisfy the demand.

| metric | baseline | demand binding |
|---|---:|---:|
| negative rejection accuracy | 0.0000 | 1.0000 |
| false-premise rejection | 0.0000 | 1.0000 |
| in-domain-value-missing rejection | 0.0000 | 1.0000 |
| full answerability accuracy | 0.5000 | 0.5000 |
| overall evidence accuracy | 0.3750 | 0.6250 |

All four hard negatives were rejected. No currently accepted full sample was demoted. The fixture is
small and deliberately concentrated, so this is a Development qualification signal, not production
evidence. The candidate must next be tested on a broader, independently frozen demand-binding
Development fixture containing true positive values, unit aliases, tables, ranges, and multi-sentence
bindings before any regression or validation run is justified.

## Decision

- Semantic query shadow: reject this candidate; keep only the reusable monotonic shadow interface.
- Deterministic demand binding: retain as an eval-only candidate and expand its independent
  Development coverage.
- Production defaults remain unchanged. No acceptance or holdout dataset was run.
