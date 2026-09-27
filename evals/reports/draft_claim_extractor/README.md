# Eval-only LLM DraftClaim extractor

## Scope

This Development-only experiment asks the configured LLM to split an internal draft answer
into strict `DraftClaim` JSON. It does not change the production Evidence Gate, retrieval,
answer generation, validation, or holdout behavior.

The extractor is instructed to copy explicit statements without rewriting, supplementation,
or inference. Exact normalized text matching is therefore used to measure extraction fidelity.
Each extracted claim is subsequently evaluated against its evidence by the frozen local NLI
model.

## Reproduction

```powershell
.venv\Scripts\python.exe -m evals.claim_extractor `
  --dataset evals\datasets\draft_claim_extraction_development_v1.jsonl `
  --output-dir evals\reports\draft_claim_extractor `
  --batch-size 8
```

## Result

Run commit: `dcfcf26f9b9912be4d54afbb26444b877cc9f7c8` (clean worktree)

- Schema-valid output: 100% (5/5 cases)
- Required-claim recall: 100% (10/10 required claims)
- Extra-claim rate: 0% (0/11 extracted claims)
- Unsupported-claim rate: 9.09% (1/11 extracted claims)
- NLI-retained claim rate: 90.91% (10/11 extracted claims)
- Runtime: 26.21 seconds

The only unsupported claim was the intentionally ungrounded statement that checkpoint
guarantees recovery within 30 seconds. NLI classified it as `unknown`; all ten grounded claims
were retained as `supported`.

## Interpretation and limits

This proves the end-to-end fixture path: draft answer -> strict JSON claims -> evidence-level
NLI filtering. It is not yet evidence that the extractor generalizes. The fixture contains only
five hand-built Chinese cases, the structured-output gateway retries once, and exact matching
rewards verbatim copying rather than semantic equivalence. A broader frozen Development set,
repeated-run stability measurement, and explicit malformed-output tests are required before
considering any production integration.
