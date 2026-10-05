# Supplemental Consumption Selector Development Report

- Candidate: `rank-capped-3-v1`
- Qualification: **FAIL**
- Evaluated commit: `d8bd72ed43aab17275040f61339d1f0b188b7ae3`
- Scope: non-blind Development only

## Results

- Combined Recall: 1.0000
- Primary-miss incremental recovery rate: 1.0000
- Supplemental consumption precision: 0.2353 (required: 0.30)
- Average consumed supplemental chunks: 2.8333
- Consumption reduction versus fixed@7: 0.5678
- Negative average consumed chunks: 3.0000
- Negative consumption reduction versus fixed@7: 0.5610
- Primary order preservation rate: 1.0000
- Budget compliance rate: 1.0000

The rank cap preserves all observed retrieval gain and materially reduces context cost, but it still
consumes three irrelevant chunks for every hard negative. The candidate therefore fails the
predeclared precision gate. Do not lower the threshold or advance this selector to validation.
