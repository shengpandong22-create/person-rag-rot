# interview_question_v1

Purpose: generate interview questions from bounded retrieval evidence.

Rules:

- Use only chunks supplied by Phase 2 retrieval as references.
- Store referenced chunks as `question_references`.
- Do not claim the Phase 3 placeholder feedback is a real ability score.
- If retrieval evidence is weak, generate a broader question and mark the reference answer as placeholder.

Output fields:

- question text
- question type
- difficulty
- reference answer
- rubric draft
- reference chunk IDs
