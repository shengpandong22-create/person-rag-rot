# Scoring Eval Report

- dataset: `evals\datasets\evaluation_discrimination_v1.jsonl`
- generated_at: 2026-09-03T13:45:19.431473+00:00
- app_version: 0.1.0
- dataset_sha256: `91361bd24fd42baafec2a338f4d8fe53f6b753f84f5916d9b6c6ef0d6ee06571`
- use_llm: False
- llm_enabled: False
- llm_model: None
- total: 12
- MAE: 7.1667
- Pearson correlation: 0.8735
- Reviewer routing accuracy: 0.4167
- Band order accuracy: 1.0
- Predicted average by band: {'high': 11.25, 'low': 2.25, 'mid': 2.5}
- Human average by band: {'high': 19.5, 'low': 6.0, 'mid': 12.0}

## High Error Cases

### disc-rag-boundary-mid

- topic: RAG 知识边界
- expected_band: mid
- human_total: 12
- predicted_total: 4
- absolute_error: 8
- status: final

### disc-rag-boundary-high

- topic: RAG 知识边界
- expected_band: high
- human_total: 19
- predicted_total: 13
- absolute_error: 6
- status: final

### disc-checkpoint-mid

- topic: LangGraph / 工作流恢复
- expected_band: mid
- human_total: 11
- predicted_total: 1
- absolute_error: 10
- status: final

### disc-checkpoint-high

- topic: LangGraph / 工作流恢复
- expected_band: high
- human_total: 20
- predicted_total: 10
- absolute_error: 10
- status: final

### disc-evaluation-mid

- topic: 可信评分
- expected_band: mid
- human_total: 13
- predicted_total: 3
- absolute_error: 10
- status: final

### disc-evaluation-high

- topic: 可信评分
- expected_band: high
- human_total: 20
- predicted_total: 10
- absolute_error: 10
- status: final

### disc-profile-mid

- topic: 能力画像
- expected_band: mid
- human_total: 12
- predicted_total: 2
- absolute_error: 10
- status: final

### disc-profile-high

- topic: 能力画像
- expected_band: high
- human_total: 19
- predicted_total: 12
- absolute_error: 7
- status: final

## Review Routing Mismatches

### disc-rag-boundary-mid

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['severe_quality_gap']

### disc-checkpoint-mid

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['severe_quality_gap']

### disc-checkpoint-high

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['boundary_with_dispute', 'dimension_conflict']

### disc-evaluation-mid

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['severe_quality_gap']

### disc-evaluation-high

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['boundary_with_dispute', 'dimension_conflict']

### disc-profile-mid

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['severe_quality_gap']

### disc-profile-high

- expected_review: False
- predicted_review: True
- confidence: 0.72
- review_reasons: ['boundary_with_dispute', 'dimension_conflict']
