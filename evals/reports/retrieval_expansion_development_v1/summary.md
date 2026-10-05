# Retrieval Expansion Development Report

- Qualified: **False**
- Dataset SHA-256: `4b63d99a95fe49d030138699ac917618c063ca54e1261c6d0ace73e61ee4835c`
- Primary recall: 0.5
- Combined recall: 0.6667
- Combined recall gain: 0.1667
- Primary-miss incremental recovery rate: 0.3333
- Supplemental consumption precision: 0.0649
- Average consumed supplemental chunks: 6.4167
- Supplemental latency P50/P95 ms: 59.2713 / 82.1844

## Qualification checks

- source_label_resolution: True
- primary_order_preservation: True
- duplicate_free_combined: True
- budget_compliance: True
- combined_recall_not_below_primary: True
- incremental_recovery: False
- consumption_precision: False
- combined_recall_gain: True
- average_consumed_count: True
- supplemental_latency_p95: True

This is non-blind Development evidence only. It does not authorize production, validation, or holdout.
