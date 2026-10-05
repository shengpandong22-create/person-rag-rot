from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.application.shadow_agent_service import ShadowAgentService, ShadowReadTools
from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.shadow_agent_repository import SqlAlchemyShadowTraceRepository


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _fingerprint(
    db: object, query: str, params: Mapping[str, object]
) -> str:
    result = await db.scalar(text(query), params)  # type: ignore[attr-defined]
    return _hash(str(result or "[]"))


async def snapshot(*, user_id: UUID, knowledge_base_id: UUID) -> dict[str, str]:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    queries = {
        "ability_profiles": """
            SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id)::text, '[]')
            FROM ability_profiles t
            WHERE t.user_id = :user_id AND t.knowledge_base_id = :knowledge_base_id
        """,
        "error_patterns": """
            SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id)::text, '[]')
            FROM error_patterns t
            WHERE t.user_id = :user_id AND t.knowledge_base_id = :knowledge_base_id
        """,
        "review_tasks": """
            SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id)::text, '[]')
            FROM review_tasks t
            WHERE t.user_id = :user_id AND t.knowledge_base_id = :knowledge_base_id
        """,
        "profile_update_events": """
            SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id)::text, '[]')
            FROM profile_update_events t
            WHERE t.user_id = :user_id AND t.knowledge_base_id = :knowledge_base_id
        """,
        "evaluations": """
            SELECT COALESCE(jsonb_agg(to_jsonb(e) ORDER BY e.id)::text, '[]')
            FROM evaluations e
            JOIN interview_questions q ON q.id = e.question_id
            JOIN interview_sessions s ON s.id = q.session_id
            WHERE s.user_id = :user_id AND s.knowledge_base_id = :knowledge_base_id
        """,
        "knowledge_catalog_points": """
            SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id)::text, '[]')
            FROM knowledge_catalog_points t
            WHERE t.knowledge_base_id = :knowledge_base_id
        """,
    }
    params = {"user_id": user_id, "knowledge_base_id": knowledge_base_id}
    try:
        async with sessions() as db:
            return {name: await _fingerprint(db, query, params) for name, query in queries.items()}
    finally:
        await engine.dispose()


async def audit(knowledge_base_id: UUID) -> dict[str, object]:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    before = await snapshot(user_id=DEFAULT_USER_ID, knowledge_base_id=knowledge_base_id)
    try:
        async with sessions() as db:
            before_count = int(
                await db.scalar(
                    text(
                        "SELECT count(*) FROM shadow_agent_runs "
                        "WHERE user_id = :user_id AND knowledge_base_id = :knowledge_base_id"
                    ),
                    {"user_id": DEFAULT_USER_ID, "knowledge_base_id": knowledge_base_id},
                )
                or 0
            )
        service = ShadowAgentService(
            ShadowReadTools(ProfileService(sessions)),
            None,
            SqlAlchemyShadowTraceRepository(sessions),
        )
        run = await service.recommend(
            user_id=DEFAULT_USER_ID,
            knowledge_base_id=knowledge_base_id,
        )
        after = await snapshot(user_id=DEFAULT_USER_ID, knowledge_base_id=knowledge_base_id)
        async with sessions() as db:
            after_count = int(
                await db.scalar(
                    text(
                        "SELECT count(*) FROM shadow_agent_runs "
                        "WHERE user_id = :user_id AND knowledge_base_id = :knowledge_base_id"
                    ),
                    {"user_id": DEFAULT_USER_ID, "knowledge_base_id": knowledge_base_id},
                )
                or 0
            )
        return {
            "knowledge_base_id": str(knowledge_base_id),
            "agent_status": run.status,
            "business_writes": run.business_writes,
            "protected_table_fingerprints_before": before,
            "protected_table_fingerprints_after": after,
            "protected_tables_identical": before == after,
            "shadow_audit_rows_before": before_count,
            "shadow_audit_rows_after": after_count,
            "shadow_audit_row_delta": after_count - before_count,
        }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Shadow Agent produces no learning-state writes."
    )
    parser.add_argument("--knowledge-base-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(audit(args.knowledge_base_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
