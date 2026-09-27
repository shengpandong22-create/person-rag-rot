# DraftClaim NLI Fixture Evaluation

This evaluation verifies the architecture `concrete answer claim -> evidence
NLI` before any LLM is allowed to generate draft claims. The dataset contains
15 human-authored, balanced fixtures: five supported, five contradicted, and
five unknown.

## Contract

Each `DraftClaim` records:

- stable claim ID;
- concrete declarative text;
- whether the claim is required for the answer;
- origin (`human_fixture` or, in a future experiment, `model_draft`).

Each fixture stores the evidence premise, expected three-way status, and a
human explanation. Blank fields, invalid enums, and duplicate case IDs fail
loading.

## Result

| Metric | Value |
|---|---:|
| Total | 15 |
| Accuracy | 0.8667 |
| Macro accuracy | 0.8667 |
| Supported accuracy | 0.8000 |
| Contradicted accuracy | 0.8000 |
| Unknown accuracy | 1.0000 |
| CPU inference time | 42662.8049 ms |

Confusion matrix:

| Actual / predicted | supported | contradicted | unknown |
|---|---:|---:|---:|
| supported | 4 | 0 | 1 |
| contradicted | 0 | 4 | 1 |
| unknown | 0 | 0 | 5 |

The two errors are conservative neutral decisions:

- `dc-004`: the citation-whitelist paraphrase was expected supported;
- `dc-006`: modular monolith versus deployed microservices was expected
  contradicted.

The model did not convert an unknown claim into supported or contradicted in
this fixture set.

## Decision

The concrete DraftClaim-to-evidence NLI path is technically viable and is much
better posed than question-to-evidence NLI. This small fixture is not enough to
approve LLM claim extraction or production use. The next safe increment is an
eval-only claim extractor whose output must validate against the `DraftClaim`
contract, preserve origin metadata, and be scored against human fixtures for
claim completeness and unsupported-claim rate.

Production Evidence Gate, validation, and all holdout data were not used or
changed. Raw probabilities and per-case decisions are stored in
`draft_claim_nli_eval.json`.
