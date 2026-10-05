# Supplemental Trigger Feature Diagnostics V2

This report is read-only. It defines no trigger rule and consumes no supplemental context.

## Group comparison

| Feature | Recoverable positive | Hard negative |
|---|---:|---:|
| New heading path ratio | 1.0000 | 1.0000 |
| Same-document new-heading ratio | 0.8889 | 0.8889 |
| New-document ratio | 0.1111 | 0.1111 |
| Heading concept redundancy | 0.4430 | 0.4630 |
| Heading concept novelty | 0.5569 | 0.5370 |
| Question-heading novelty | 0.2217 | 0.1800 |
| Primary heading coverage | 0.1139 | 0.1439 |

The structural distributions overlap heavily. In particular, every recoverable positive and every
hard negative adds a new heading path, and both groups usually add a new heading inside an already
retrieved document. Hard negatives deliberately ask for unsupported values or guarantees under the
correct topic, so heading novelty and relation-term overlap cannot distinguish evidence existence
from topical similarity.

No boolean trigger should be frozen from these features. The missing signal is demand-to-evidence
support (for example whether the requested value, guarantee, or relation is actually present), not
another heading, document, score, or rank threshold.
