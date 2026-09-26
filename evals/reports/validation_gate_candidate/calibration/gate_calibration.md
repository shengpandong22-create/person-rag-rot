# Evidence Gate Offline Calibration

- source report: `evals\reports\validation_gate_candidate\vector-only\retrieval_eval.json`
- source SHA-256: `b2fe8c86a9e1b86adb164b91805d0f1288046c3f8a11fa7f5cb94bd7266361c6`
- retrieval rerun: no

| policy | parameters | full accept | partial boundary | none reject | macro accuracy |
|---|---|---:|---:|---:|---:|
| current_binary_v1 | `{}` | 1.0 | 0.0 | 1.0 | 0.6667 |
| specific_coverage_ratio | `{"minimum": 0.15}` | 1.0 | 0.0 | 1.0 | 0.6667 |
| specific_coverage_ratio | `{"minimum": 0.2}` | 0.9333 | 0.0 | 1.0 | 0.6444 |
| specific_coverage_ratio | `{"minimum": 0.25}` | 0.9333 | 0.5 | 1.0 | 0.8111 |
| specific_coverage_ratio | `{"minimum": 0.3}` | 0.9333 | 0.5 | 1.0 | 0.8111 |
| specific_coverage_ratio | `{"minimum": 0.35}` | 0.8667 | 0.5 | 1.0 | 0.7889 |
| specific_coverage_ratio | `{"minimum": 0.4}` | 0.8 | 0.5 | 1.0 | 0.7667 |
| specific_coverage_ratio | `{"minimum": 0.45}` | 0.6667 | 1.0 | 1.0 | 0.8889 |
| specific_coverage_ratio | `{"minimum": 0.5}` | 0.6 | 1.0 | 1.0 | 0.8667 |
| specific_covered_terms | `{"minimum": 2}` | 1.0 | 0.0 | 1.0 | 0.6667 |
| specific_covered_terms | `{"minimum": 3}` | 0.8 | 0.0 | 1.0 | 0.6 |
| specific_covered_terms | `{"minimum": 4}` | 0.8 | 0.5 | 1.0 | 0.7667 |
| specific_covered_terms | `{"minimum": 5}` | 0.7333 | 0.5 | 1.0 | 0.7444 |
| specific_covered_terms | `{"minimum": 6}` | 0.6667 | 0.5 | 1.0 | 0.7222 |
| specific_covered_terms | `{"minimum": 7}` | 0.6 | 0.5 | 1.0 | 0.7 |
| specific_covered_terms | `{"minimum": 8}` | 0.6 | 0.5 | 1.0 | 0.7 |
| numeric_demand_coverage | `{}` | 1.0 | 0.0 | 1.0 | 0.6667 |

## Eligible candidates

No candidate passed the safety constraints.
