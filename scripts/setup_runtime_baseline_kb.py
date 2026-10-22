"""Create one isolated, fixture-backed knowledge base for the runtime baseline."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def create_benchmark_knowledge_base(
    *, base_url: str, fixture: Path, timeout_seconds: float
) -> dict[str, str]:
    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        runtime = client.get(f"{base_url}/health/runtime")
        runtime.raise_for_status()
        if runtime.json().get("llm_enabled") is not False:
            raise RuntimeError(
                "setup must use the fallback instance so fixture ingestion never calls an LLM"
            )
        created = client.post(
            f"{base_url}/api/v1/knowledge-bases",
            json={
                "name": "runtime-baseline-fixture-v1",
                "description": "isolated sequential runtime benchmark fixture",
            },
        )
        created.raise_for_status()
        knowledge_base_id = str(created.json()["id"])
        with fixture.open("rb") as file:
            uploaded = client.post(
                f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/documents",
                files={"file": (fixture.name, file, "text/markdown")},
                data={"trust_level": "curated"},
            )
        uploaded.raise_for_status()
        document_id = str(uploaded.json()["id"])
        deadline = time.monotonic() + timeout_seconds
        latest: dict[str, Any] = {}
        while time.monotonic() < deadline:
            response = client.get(f"{base_url}/api/v1/documents/{document_id}")
            response.raise_for_status()
            latest = response.json()
            if latest.get("status") == "ready":
                return {"knowledge_base_id": knowledge_base_id, "document_id": document_id}
            if latest.get("status") == "failed":
                raise RuntimeError(f"fixture ingestion failed: {latest.get('error_message')}")
            time.sleep(1)
    raise TimeoutError(f"fixture ingestion did not reach ready state: {latest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("evals/fixtures/runtime_baseline_knowledge_v1.md"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    result = create_benchmark_knowledge_base(
        base_url=args.base_url.rstrip("/"),
        fixture=args.fixture,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
