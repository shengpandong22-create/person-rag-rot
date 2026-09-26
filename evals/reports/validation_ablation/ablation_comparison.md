# Validation Retrieval Ablation

| mode | recall_at_1 | recall_at_3 | recall_at_6 | mrr | full_answerability_accuracy | partial_answerability_accuracy | negative_rejection_accuracy | latency_p50_ms | latency_p95_ms | average_candidate_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| vector-only | 0.3529 | 0.5294 | 0.7059 | 0.4853 | 1.0 | 1.0 | 1.0 | 39.175 | 58.5544 | 6.0 |
| text-only | 0.1765 | 0.3529 | 0.4118 | 0.2667 | 1.0 | 1.0 | 1.0 | 30.8845 | 50.1426 | 6.0 |
| rrf | 0.2941 | 0.5294 | 0.7059 | 0.4461 | 1.0 | 1.0 | 1.0 | 82.2099 | 355.7632 | 6.0 |
| rrf-heuristic | 0.1765 | 0.5294 | 0.7059 | 0.3647 | 1.0 | 1.0 | 1.0 | 76.2197 | 95.7942 | 6.0 |
