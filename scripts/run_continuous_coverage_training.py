"""Run the fixed, isolated continuous-coverage evidence protocol v1.

It creates a new acceptance-only knowledge base and never alters a user's
existing knowledge base, profile, or historical coverage records.
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

FIXTURE = Path("evals/fixtures/continuous-coverage-training-v1.md")
TARGET_TITLES = (
    "RRF 公式",
    "引用白名单",
    "checkpoint 恢复",
    "幂等提交",
    "Rubric 重算",
    "低置信复核路由",
)


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
    for name, value in (("trust_level", "curated"), ("author", "continuous-coverage-v1")):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode())
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


async def source_ids(point_id: uuid.UUID) -> set[str]:
    engine = create_database_engine(get_settings().database_url)
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
    raise TimeoutError("timed out waiting for fixture ingestion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture_bytes = FIXTURE.read_bytes()
    runtime = request_json("GET", f"{args.base_url}/health/runtime")
    created = request_json(
        "POST",
        f"{args.base_url}/api/v1/knowledge-bases",
        {
            "name": f"continuous-coverage-v1-{datetime.now(UTC):%Y%m%d%H%M%S}",
            "description": "isolated continuous coverage acceptance fixture",
        },
    )
    base_id = str(created["id"])
    document = upload(f"{args.base_url}/api/v1/knowledge-bases/{base_id}/documents", FIXTURE)
    wait_until_ready(args.base_url, str(document["id"]))
    initial_coverage = request_json(
        "GET", f"{args.base_url}/api/v1/knowledge-bases/{base_id}/coverage"
    )
    points_by_title = {str(item["title"]): item for item in initial_coverage["points"]}
    missing = [title for title in TARGET_TITLES if title not in points_by_title]
    if missing:
        raise RuntimeError(f"fixture targets absent from catalog: {missing}")

    runs: list[dict[str, object]] = []
    for sequence, title in enumerate(TARGET_TITLES, start=1):
        point = points_by_title[title]
        point_id = uuid.UUID(str(point["id"]))
        catalog_sources = asyncio.run(source_ids(point_id))
        if not catalog_sources:
            raise RuntimeError(f"target {title} has no catalog source")
        interview = request_json(
            "POST",
            f"{args.base_url}/api/v1/interviews",
            {
                "knowledge_base_id": base_id,
                "topic": title,
                "coverage_catalog_point_id": str(point_id),
                "difficulty": "medium",
                "question_count": 1,
            },
        )
        started_at = time.perf_counter()
        snapshot = request_json(
            "POST", f"{args.base_url}/api/v1/interviews/{interview['id']}/start", {}
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        question = snapshot["current_question"]
        if not isinstance(question, dict):
            raise RuntimeError(f"target {title} did not produce a question")
        cited_ids = {str(item) for item in question["reference_chunk_ids"]}
        runs.append(
            {
                "sequence": sequence,
                "target_title": title,
                "target_id": str(point_id),
                "session_id": interview["id"],
                "question_id": question["id"],
                "generation_mode": question["rubric"]["generation"]["mode"],
                "question_text": question["question_text"],
                "latency_ms": latency_ms,
                "citation_ids": sorted(cited_ids),
                "target_source_citation_present": bool(cited_ids & catalog_sources),
            }
        )
    final_coverage = request_json(
        "GET", f"{args.base_url}/api/v1/knowledge-bases/{base_id}/coverage"
    )
    final_points = {str(item["title"]): item for item in final_coverage["points"]}
    mode_requirement = runtime.get("llm", {}).get("configured") is not True
    all_llm = all(row["generation_mode"] == "llm" for row in runs)
    unique_target_count = len({str(row["target_id"]) for row in runs})
    attempted_all = all(
        int(final_points[title].get("attempt_count", 0)) >= 1 for title in TARGET_TITLES
    )
    passed = (
        len(runs) == len(TARGET_TITLES)
        and all(row["target_source_citation_present"] for row in runs)
        and (all_llm or mode_requirement)
        and unique_target_count == len(TARGET_TITLES)
        and attempted_all
    )
    result = {
        "protocol": "continuous-coverage-training-v1",
        "executed_at": datetime.now(UTC).isoformat(),
        "runtime": runtime,
        "fixture": str(FIXTURE),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "knowledge_base_id": base_id,
        "initial_coverage": initial_coverage,
        "final_coverage": final_coverage,
        "runs": runs,
        "metrics": {
            "run_count": len(runs),
            "unique_target_count": unique_target_count,
            "duplicate_target_count": len(runs) - unique_target_count,
            "all_llm": all_llm,
            "all_target_sources_cited": all(row["target_source_citation_present"] for row in runs),
            "all_targets_attempted": attempted_all,
            "p50_latency_ms": sorted(row["latency_ms"] for row in runs)[len(runs) // 2],
            "p95_latency_ms": sorted(row["latency_ms"] for row in runs)[
                max(0, int(len(runs) * 0.95) - 1)
            ],
        },
        "pass": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"pass": passed, **result["metrics"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
