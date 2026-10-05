# Retrieval Expansion Regression Safety Report

- Candidate: `primary-context-dedupe-v1`
- Qualification: **PASS**
- Evaluated commit: `46b7eceb017d3ac92325c58276970ccdbde61825`
- Scope: candidate-only retrieval and context budgeting; no Evidence Gate or generation

## Safety results

- Primary Top-6 identity rate: 1.0000
- Baseline/candidate Primary Recall: 0.5500 / 0.5500
- Primary Recall delta: 0.0000
- Combined Recall: 0.7000
- Combined Recall gain: 0.1500
- Negative decision mutations: 0
- Gate/generation invocations: 0 / 0
- Duplicate-free and budget compliance rates: 1.0000 / 1.0000
- Maximum supplemental/combined characters: 2262 / 4107
- Supplemental latency P50/P95: 63.9182 / 99.5186 ms

## Diagnostic-only results

- Primary misses recovered: 3 of 9 (0.3333)
- Supplemental consumption precision: 0.0190
- Average consumed supplemental chunks: 7.0000
- Supplemental candidates generated for 10 negative cases: 185

The candidate passes regression safety because the original retrieval result is unchanged and no
answerability decision or generated answer is produced. It does not yet demonstrate efficient or
safe end-to-end consumption: fixed consumption is noisy, especially for negative cases. This result
does not authorize Gate/generation integration, validation, holdout, API wiring, or production use.
