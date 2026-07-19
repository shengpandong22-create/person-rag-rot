# Phase 2 Acceptance Report

Status: passed on 2026-07-19.

## Scope Completed

- PostgreSQL + pgvector hybrid retriever.
- PostgreSQL full-text retrieval over chunk `tsvector`.
- RRF fusion with deterministic unit coverage.
- Single-document chunk cap and adjacent chunk de-duplication.
- Evidence-aware answer service.
- Citation validation restricted to current retrieval context.
- Chat session, message, and citation persistence.
- REST APIs for retrieval and grounded ask.
- Basic SSE events for ask streaming.
- Initial retrieval evaluation dataset and baseline report scaffold.

## Changed Files

- `src/agent_mentor/ports/knowledge_retriever.py`
- `src/agent_mentor/infrastructure/retriever.py`
- `src/agent_mentor/application/answer_service.py`
- `src/agent_mentor/api/chat.py`
- `src/agent_mentor/infrastructure/database/models.py`
- `migrations/versions/20260719_0003_chat_rag.py`
- `src/agent_mentor/rag/retrieval.py`
- `src/agent_mentor/prompts/answer_generation_v1.md`
- `evals/datasets/retrieval_v1.jsonl`
- `docs/evaluations/retrieval-baseline-v1.md`

## Validation

- `pyright`: 0 errors.
- `pytest`: 13 passed.
- `ruff check`: passed in Docker.
- `ruff format --check`: passed in Docker.
- `docker compose up -d --build api`: passed.
- Alembic migration `20260719_0003`: applied successfully.
- `GET /health/ready`: returned `ok`.
- Uploaded acceptance Markdown document: final status `ready`.
- Retrieval API returned candidate with score `0.03252247488101534`.
- Grounded ask returned `evidence_sufficient=true` and 1 valid citation.
- Unanswerable ask returned `evidence_sufficient=false` and 0 citations.
- SSE success path emitted `retrieval.started`, `retrieval.completed`, `answer.delta`, `answer.references`, and `answer.completed`.
- Database persistence confirmed: chat sessions, messages, and citations were written.
- Docker resource snapshot: API `73.5MiB / 2GiB`, DB `42.71MiB / 2GiB`.

## Known Limits

- Local Windows execution of Ruff is still blocked by application control policy with OS error
  `4551`; the project quality gate now runs Ruff successfully through Docker.
- The current answer generator is deterministic and extractive for local development; cloud LLM integration remains a later gateway concern.
- Retrieval evaluation has the dataset and report scaffold, but numeric Recall/MRR/NDCG automation should be expanded when a seeded benchmark knowledge base is added.
- SSE failure-path terminal event is implemented inside the answer event generator, but only the success path was manually verified through HTTP in this phase.

## Exit Condition

Phase 2 exits with a working evidence-backed RAG question-answering path, real citation persistence, and honest no-evidence behavior. Phase 3 is unlocked.
