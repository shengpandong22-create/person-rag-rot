"""Run a repeatable, isolated real-model acceptance check for coverage provenance.

The runner creates a new acceptance-only knowledge base.  It never reindexes,
archives, or edits an existing knowledge base.  Each run selects the same
catalog point and verifies the generated question persisted a citation to one
of that point's catalog source chunks.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from sqlalchemy import select

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.models import KnowledgeCatalogSourceModel
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)

FIXTURE = Path("evals/fixtures/coverage-loop-acceptance-v1.md")


def request_json(
    method: str, url: str, payload: dict[str, object] | None = None
) -> dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    with urlopen(Request(url, data=body, headers=headers, method=method), timeout=180) as response:
        return json.loads(response.read().decode())


def upload(url: str, path: Path) -> dict[str, object]:
    boundary = f"----agentmentor{uuid.uuid4().hex}"
    body = bytearray()

    def field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode())
        body.extend(b"\r\n")

    field("trust_level", "curated")
    field("author", "coverage-loop-acceptance")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode()
    )
    body.extend(b"Content-Type: text/markdown\r\n\r\n")
    body.extend(path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    request = Request(
        url,
        data=bytes(body),
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


async def catalog_source_ids(point_id: uuid.UUID) -> set[str]:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as db:
            return {
                str(value)
                for value in (
                    await db.scalars(
                        select(KnowledgeCatalogSourceModel.chunk_id).where(
                            KnowledgeCatalogSourceModel.knowledge_point_id == point_id
                        )
                    )
                ).all()
            }
    finally:
        await engine.dispose()


def wait_until_ready(base_url: str, document_id: str) -> None:
    for _ in range(45):
        document = request_json("GET", f"{base_url}/api/v1/documents/{document_id}")
        if document["status"] == "ready":
            return
        if document["status"] == "failed":
            raise RuntimeError(f"ingestion failed: {document.get('error_message')}")
        time.sleep(2)
    raise TimeoutError("timed out waiting for acceptance document ingestion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 3:
        raise ValueError("--runs must be at least 3 for a repeatability claim")

    fixture_bytes = FIXTURE.read_bytes()
    runtime = request_json("GET", f"{args.base_url}/health/runtime")
    created = request_json(
        "POST",
        f"{args.base_url}/api/v1/knowledge-bases",
        {
            "name": f"coverage-loop-acceptance-{datetime.now(UTC):%Y%m%d%H%M%S}",
            "description": "isolated provenance acceptance fixture; safe to retain",
        },
    )
    base_id = str(created["id"])
    document = upload(f"{args.base_url}/api/v1/knowledge-bases/{base_id}/documents", FIXTURE)
    wait_until_ready(args.base_url, str(document["id"]))
    coverage = request_json("GET", f"{args.base_url}/api/v1/knowledge-bases/{base_id}/coverage")
    target = next(item for item in coverage["points"] if item["title"] == "RRF 公式")
    target_id = uuid.UUID(str(target["id"]))
    source_ids = asyncio.run(catalog_source_ids(target_id))
    if not source_ids:
        raise RuntimeError("acceptance target has no catalog source chunk")

    runs: list[dict[str, object]] = []
    for run_number in range(1, args.runs + 1):
        interview = request_json(
            "POST",
            f"{args.base_url}/api/v1/interviews",
            {
                "knowledge_base_id": base_id,
                "topic": "RRF 公式",
                "coverage_catalog_point_id": str(target_id),
                "difficulty": "medium",
                "question_count": 1,
            },
        )
        started = request_json(
            "POST", f"{args.base_url}/api/v1/interviews/{interview['id']}/start", {}
        )
        question = started["current_question"]
        if not isinstance(question, dict):
            raise RuntimeError("acceptance run did not create a question")
        citation_ids = {str(item) for item in question["reference_chunk_ids"]}
        runs.append(
            {
                "run": run_number,
                "session_id": interview["id"],
                "question_id": question["id"],
                "generation_mode": question["rubric"]["generation"]["mode"],
                "question_text": question["question_text"],
                "citation_ids": sorted(citation_ids),
                "target_source_citation_present": bool(citation_ids & source_ids),
            }
        )

    result = {
        "protocol": "coverage-loop-acceptance-v1",
        "executed_at": datetime.now(UTC).isoformat(),
        "runtime": runtime,
        "fixture": str(FIXTURE),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "knowledge_base_id": base_id,
        "target": {
            "id": str(target_id),
            "title": target["title"],
            "source_chunk_ids": sorted(source_ids),
        },
        "runs": runs,
        "run_count": len(runs),
        "pass": all(item["target_source_citation_present"] for item in runs),
        "criterion": "every selected-target question must cite an exact catalog source chunk",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"pass": result["pass"], "run_count": result["run_count"]}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
