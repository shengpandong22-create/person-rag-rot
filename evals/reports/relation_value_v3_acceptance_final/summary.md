# Relation-Value V3 Acceptance Result

- Accepted for production integration design: `false`
- Demand accuracy: `0.3256`
- Positive demand recall: `0.0645`
- Positive all-demands row accuracy: `0.0833`
- Negative demand rejection: `1.0000`
- Binding precision: `0.2222`
- Candidate P95: `0.229100 ms`
- Failed gates: demand_accuracy, positive_demand_recall, positive_row_all_demands_accuracy, binding_precision, paired_discrimination, span_success_counts, role_success_counts, semantic_success_counts
- Failed cases: rva3-002, rva3-003, rva3-004, rva3-005, rva3-007, rva3-008, rva3-009, rva3-010, rva3-011, rva3-012, rva3-013, rva3-014, rva3-015, rva3-016, rva3-017, rva3-018, rva3-019, rva3-020, rva3-021, rva3-022, rva3-023, rva3-024
- Scope: eval-only; this result does not change the production default.
- Limitation: the fixture measures frozen labeled evidence binding, not retrieval recall or end-to-end answer quality.
