from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID


@dataclass(frozen=True)
class Scenario:
    topic: str
    topic_key: str
    topic_title: str
    subtopic_key: str | None = None
    subtopic_title: str | None = None
    difficulty: str = "medium"


SUITES: dict[str, tuple[str, list[Scenario]]] = {
    "agent": (
        "46691546-593a-4d21-bcfc-0d16986c20a7",
        [
            Scenario("RAG 工程化", "rag", "RAG"),
            Scenario("RAG 工程化", "rag", "RAG"),
            Scenario("LangGraph 工作流", "langgraph", "LangGraph"),
            Scenario("LangGraph 工作流", "langgraph", "LangGraph"),
            Scenario("LangChain Agent", "langchain", "LangChain"),
            Scenario("上下文与记忆管理", "context_memory", "上下文与记忆管理"),
            Scenario("工具调用与 MCP", "tool_calling", "Agent 工具调用"),
            Scenario("评估与可靠性", "evaluation", "评估与可靠性"),
            Scenario("AI Agent 工程化", "agent_engineering", "AI Agent 工程化"),
            Scenario("AI Agent 工程化", "agent_engineering", "AI Agent 工程化"),
        ],
    ),
    "java": (
        "2c6f2730-852e-4d94-8bc8-3de1b840ed95",
        [
            Scenario("JVM 与 GC", "java_backend", "Java 后端", "jvm", "JVM 与 GC"),
            Scenario("JVM 与 GC", "java_backend", "Java 后端", "jvm", "JVM 与 GC"),
            Scenario("JVM 与 GC", "java_backend", "Java 后端", "jvm", "JVM 与 GC"),
            Scenario("Java 并发", "java_backend", "Java 后端", "concurrency", "Java 并发"),
            Scenario("Java 并发", "java_backend", "Java 后端", "concurrency", "Java 并发"),
            Scenario("Java 并发", "java_backend", "Java 后端", "concurrency", "Java 并发"),
            Scenario("Spring 事务", "java_backend", "Java 后端", "transaction", "事务与一致性"),
            Scenario("Spring 事务", "java_backend", "Java 后端", "transaction", "事务与一致性"),
            Scenario(
                "Java 服务生产化", "java_backend", "Java 后端", "production", "Java 服务生产化"
            ),
            Scenario(
                "Java 服务生产化", "java_backend", "Java 后端", "production", "Java 服务生产化"
            ),
        ],
    ),
}


def summarize_question_angles(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    distribution: dict[str, int] = {}
    missing_count = 0
    total_questions = 0
    for round_result in rounds:
        for question in round_result.get("questions", []):
            total_questions += 1
            rubric = question.get("rubric")
            if not isinstance(rubric, dict):
                missing_count += 1
                continue
            angle = rubric.get("question_angle")
            if not isinstance(angle, dict):
                missing_count += 1
                continue
            key = angle.get("key")
            title = angle.get("title")
            if not isinstance(key, str) or not key:
                missing_count += 1
                continue
            label = key if not isinstance(title, str) or not title else f"{key}:{title}"
            distribution[label] = distribution.get(label, 0) + 1
    return {
        "total_questions": total_questions,
        "with_question_angle": total_questions - missing_count,
        "missing_question_angle": missing_count,
        "distribution": dict(sorted(distribution.items())),
    }


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    *,
    attempts: int = 3,
) -> Any:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(
                Request(url, data=body, headers=request_headers, method=method), timeout=180
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"request failed after {attempts} attempts: {method} {url}") from last_error


def run_suite(
    suite: str,
    base_url: str,
    output: Path,
    *,
    knowledge_base_id_override: UUID | None = None,
    rounds: int | None = None,
) -> dict[str, Any]:
    configured_knowledge_base_id, scenarios = SUITES[suite]
    knowledge_base_id = str(knowledge_base_id_override or configured_knowledge_base_id)
    if rounds is not None and rounds < 1:
        raise ValueError("rounds must be greater than 0.")
    planned_rounds = rounds or len(scenarios)
    result: dict[str, Any] = {
        "suite": suite,
        "knowledge_base_id": knowledge_base_id,
        "planned_rounds": planned_rounds,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "rounds": [],
        "failures": [],
    }
    result["profile_before"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/profile/abilities"
    )
    result["history_before"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/reports/history?limit=100"
    )

    for round_number in range(1, planned_rounds + 1):
        scenario = scenarios[(round_number - 1) % len(scenarios)]
        started = time.monotonic()
        round_result: dict[str, Any] = {
            "round": round_number,
            "scenario": scenario.__dict__,
            "questions": [],
        }
        try:
            interview = request_json(
                "POST",
                f"{base_url}/api/v1/interviews",
                {
                    "knowledge_base_id": knowledge_base_id,
                    "topic": scenario.topic,
                    "profile_topic_key": scenario.topic_key,
                    "profile_topic_title": scenario.topic_title,
                    "profile_subtopic_key": scenario.subtopic_key,
                    "profile_subtopic_title": scenario.subtopic_title,
                    "difficulty": scenario.difficulty,
                    "question_count": 3,
                },
            )
            round_result["session_id"] = interview["id"]
            snapshot = request_json(
                "POST", f"{base_url}/api/v1/interviews/{interview['id']}/start", {}
            )
            for question_number in range(1, 4):
                question = snapshot.get("current_question")
                if not question:
                    raise RuntimeError(f"round {round_number}: question {question_number} missing")
                round_result["questions"].append(
                    {
                        "id": question["id"],
                        "sequence": question["sequence"],
                        "text": question["question_text"],
                        "type": question["question_type"],
                        "reference_answer": question["reference_answer"],
                        "rubric": question["rubric"],
                        "reference_chunk_ids": question["reference_chunk_ids"],
                    }
                )
                snapshot = request_json(
                    "POST",
                    f"{base_url}/api/v1/interviews/{interview['id']}/answers",
                    {"question_id": question["id"], "answer": question["reference_answer"]},
                    {"Idempotency-Key": f"audit-{suite}-{round_number}-{question_number}"},
                )
            report = request_json(
                "POST",
                f"{base_url}/api/v1/interviews/{interview['id']}/report",
                {"reviewer_available": True},
            )
            profile = request_json(
                "POST", f"{base_url}/api/v1/interviews/{interview['id']}/profile-updates", {}
            )
            round_result["report"] = report
            round_result["profile_after"] = profile
            round_result["status"] = snapshot["status"]
        except Exception as error:  # noqa: BLE001 - acceptance runner must preserve later rounds
            round_result["error"] = f"{type(error).__name__}: {error}"
            result["failures"].append(round_result["error"])
        round_result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["rounds"].append(round_result)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"[{suite}] round={round_number}/{planned_rounds} topic={scenario.topic} "
            f"status={round_result.get('status', 'failed')} "
            f"score={round_result.get('report', {}).get('total_score', '-')} "
            f"elapsed={round_result['elapsed_seconds']}s",
            flush=True,
        )

    result["question_angle_summary"] = summarize_question_angles(result["rounds"])
    result["profile_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/profile/abilities"
    )
    result["errors_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/profile/error-patterns"
    )
    result["tasks_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/review-tasks"
    )
    result["history_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/reports/history?limit=100"
    )
    result["trends_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/reports/trends?limit=100"
    )
    result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", choices=sorted(SUITES))
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--knowledge-base-id", type=UUID)
    parser.add_argument("--rounds", type=int)
    args = parser.parse_args()
    result = run_suite(
        args.suite,
        args.base_url.rstrip("/"),
        args.output,
        knowledge_base_id_override=args.knowledge_base_id,
        rounds=args.rounds,
    )
    print(
        f"[{args.suite}] complete rounds={len(result['rounds'])} "
        f"failures={len(result['failures'])} "
        f"question_angles={result['question_angle_summary']['distribution']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
