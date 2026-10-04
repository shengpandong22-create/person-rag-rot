# Relation-Value V3 Acceptance Independent Review

## Decision

The first-pass 36-row annotation draft is not approved. Rows must remain `review_state=draft`, and
the freeze-stage audit must not be run as a qualification claim.

The reviewer inspected only the annotation contract, draft JSONL, and original `docs/learning`
sources. V3 implementation, candidate output, retrieval/model execution, and experiment reports
were excluded. However, the draft exposed the author's labels, so this was a candidate-blind source
review rather than a strict label-blind reannotation. It cannot by itself authorize `agreed` labels.

## Blocking findings

1. `rva3-019`, `rva3-020`, and `rva3-021` have shifted RRF evidence. The first two cite the next
   formula row, while the third contains only a code fence.
2. The six multi-demand positives repeat an endpoint already contained in a sequence or range.
   They do not test independent clauses or all-or-nothing multi-demand binding.
3. The six `bounded_multi_span` positives are single formulas or contiguous code blocks. Their
   structural labels do not satisfy the contract's bounded cross-structure definition.
4. Most `pair_id` assignments do not connect the positive row to a hard negative using the same
   evidence and a meaningful relation contrast.
5. `rva3-012` omits the table header needed to bind vector and text rank columns.
6. `rva3-018` treats version identifiers as `count` rather than `generic`.
7. `rva3-033` and `rva3-034` are subject/predicate or semantic mismatches, not
   `provenance_structure` negatives under the current definition.

## Rows accepted without label correction

The reviewer accepted the core source binding for `rva3-013`, `rva3-014`, `rva3-015`,
`rva3-016`, `rva3-017`, `rva3-031`, and `rva3-035`. Some still require pair metadata changes.

The remaining rows require evidence, structural, multi-demand, pair, wording, or taxonomy repair.
No partial acceptance is applied to the JSONL because freeze requires a coherent reviewed dataset.

## Required repair sequence

1. Repair the three fatal evidence mismatches.
2. Replace redundant multi-demand annotations with genuinely independent requested clauses.
3. Rebuild structural quotas around true sentence, table-with-header, code, and bounded multi-span
   evidence.
4. Reassign pairs only when positive and negative rows form an auditable same-evidence contrast.
5. Correct version semantics and the two negative confusion categories.
6. Re-run the draft static audit only.
7. Generate a worksheet containing questions and evidence but hiding all author labels.
8. Conduct a fresh strict blind reannotation, then adjudicate differences from source evidence.

Only after that process may rows be changed to `review_state=agreed` and evaluated by the
freeze-stage static audit. V3 remains unexecuted and the dataset remains unfrozen.
