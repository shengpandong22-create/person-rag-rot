from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8000"
KNOWLEDGE_BASE_ID = "2c6f2730-852e-4d94-8bc8-3de1b840ed95"
OUTPUT = Path("docs/evaluations/results/java-redis-incremental-coverage-20260802.json")


def call(method: str, path: str, payload: dict[str, Any] | None = None, **headers: str) -> Any:
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request_headers = {"Accept": "application/json", **headers}
    if body is not None:
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    with urlopen(
        Request(f"{BASE_URL}{path}", data=body, headers=request_headers, method=method),
        timeout=180,
    ) as response:
        return json.loads(response.read().decode())


def main() -> None:
    result: dict[str, Any] = {
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "topic": "Redis 缓存工程化",
        "coverage_before_rounds": call(
            "GET", f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/coverage"
        ),
        "profile_before_rounds": call(
            "GET", f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/profile/abilities"
        ),
        "rounds": [],
    }
    for round_number in range(1, 4):
        interview = call(
            "POST",
            "/api/v1/interviews",
            {
                "knowledge_base_id": KNOWLEDGE_BASE_ID,
                "topic": "Redis 缓存工程化",
                "profile_topic_key": "java_backend",
                "profile_topic_title": "Java 后端",
                "profile_subtopic_key": "production",
                "profile_subtopic_title": "Java 服务生产化",
                "difficulty": "medium",
                "question_count": 3,
            },
        )
        snapshot = call("POST", f"/api/v1/interviews/{interview['id']}/start", {})
        questions = []
        for question_number in range(1, 4):
            question = snapshot["current_question"]
            questions.append(
                {
                    "text": question["question_text"],
                    "reference_chunk_ids": question["reference_chunk_ids"],
                }
            )
            snapshot = call(
                "POST",
                f"/api/v1/interviews/{interview['id']}/answers",
                {"question_id": question["id"], "answer": question["reference_answer"]},
                **{"Idempotency-Key": f"redis-coverage-{round_number}-{question_number}"},
            )
        report = call(
            "POST", f"/api/v1/interviews/{interview['id']}/report", {"reviewer_available": True}
        )
        call("POST", f"/api/v1/interviews/{interview['id']}/profile-updates", {})
        coverage = call("GET", f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/coverage")
        result["rounds"].append(
            {
                "round": round_number,
                "session_id": interview["id"],
                "score": report["total_score"],
                "max_score": report["max_score"],
                "questions": questions,
                "coverage_after": coverage,
            }
        )
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"round={round_number}/3 score={report['total_score']}/{report['max_score']} "
            f"uncovered={coverage['uncovered']} attempted={coverage['attempted']} "
            f"verified={coverage['verified']}",
            flush=True,
        )
        time.sleep(1)
    result["profile_after_rounds"] = call(
        "GET", f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/profile/abilities"
    )
    result["plan_after_rounds"] = call(
        "GET", f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/interview-plan"
    )
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
