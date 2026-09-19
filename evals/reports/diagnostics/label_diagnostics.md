# Retrieval Label Diagnostics

- source_report: `evals\reports\retrieval_current\retrieval_eval.json`
- scope: answerable rows carrying diagnostic keywords
- chunk_content_available: False
- NOTE: A/B/C are diagnostic only and are NOT valid Recall/MRR.
  They show how much of the old metric came from public-term matching
  or from the document title field. Human labels remain the only
  acceptable ground truth.

| variant | rule | cases | hit@1 | hit@3 | hit@6 | misses |
| --- | --- | --- | --- | --- | --- | --- |
| A | any keyword, title+heading+content (v1, from recorded matched_keywords) | 26 | 0.5 | 0.6538 | 0.7308 | ret-009, ret-013, ret-014, ret-015, ret-017, ret-018, ret-020 |
| B | any keyword, heading+content | n/a | n/a | n/a | n/a | not computable from this report |
| C | >=2 keywords, heading+content | n/a | n/a | n/a | n/a | not computable from this report |
| D | all keywords, heading+content | n/a | n/a | n/a | n/a | not computable from this report |

## Why only variant A is reported

This report was produced before ``content`` was persisted into
``top_chunks``.  Only ``document_title`` and the run-time
``matched_keywords`` survive, so variants B/C/D cannot be
recomputed.  They are marked *not computable* rather than zero,
because a zero would be read as a retrieval failure instead of a
missing field.

Variant A above is reconstructed from ``matched_keywords``, which
is the original v1 verdict recorded at run time — so it is exact,
not an approximation.

To obtain B/C/D, re-run the retrieval evaluation with a dataset
whose positive rows carry human ``relevant_sources`` labels.

