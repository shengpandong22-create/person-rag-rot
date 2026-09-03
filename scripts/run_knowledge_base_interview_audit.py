from __future__ import annotations

import argparse
import json
import re
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


def summarize_question_generation(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    distribution: dict[str, int] = {}
    fallback_reasons: dict[str, int] = {}
    missing_count = 0
    total_questions = 0
    for round_result in rounds:
        for question in round_result.get("questions", []):
            total_questions += 1
            rubric = question.get("rubric")
            if not isinstance(rubric, dict):
                missing_count += 1
                continue
            generation = rubric.get("generation")
            if not isinstance(generation, dict):
                missing_count += 1
                continue
            mode = generation.get("mode")
            if not isinstance(mode, str) or not mode:
                missing_count += 1
                continue
            distribution[mode] = distribution.get(mode, 0) + 1
            reason = generation.get("fallback_reason")
            if isinstance(reason, str) and reason:
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
    return {
        "total_questions": total_questions,
        "with_generation": total_questions - missing_count,
        "missing_generation": missing_count,
        "mode_distribution": dict(sorted(distribution.items())),
        "fallback_reasons": dict(sorted(fallback_reasons.items())),
    }


def summarize_question_cooldown(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    cooldown_counts: list[int] = []
    missing_count = 0
    total_questions = 0
    for round_result in rounds:
        for question in round_result.get("questions", []):
            total_questions += 1
            rubric = question.get("rubric")
            if not isinstance(rubric, dict):
                missing_count += 1
                continue
            generation = rubric.get("generation")
            if not isinstance(generation, dict):
                missing_count += 1
                continue
            cooldown_count = generation.get("recent_question_cooldown_count")
            if not isinstance(cooldown_count, int):
                missing_count += 1
                continue
            cooldown_counts.append(cooldown_count)
    active_counts = [count for count in cooldown_counts if count > 0]
    return {
        "total_questions": total_questions,
        "with_cooldown_trace": len(cooldown_counts),
        "missing_cooldown_trace": missing_count,
        "active_cooldown_questions": len(active_counts),
        "max_recent_question_cooldown_count": max(cooldown_counts, default=0),
        "average_recent_question_cooldown_count": round(
            sum(cooldown_counts) / max(1, len(cooldown_counts)), 4
        ),
    }


def summarize_question_similarity(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    for round_result in rounds:
        scenario = round_result.get("scenario", {})
        topic = scenario.get("topic") if isinstance(scenario, dict) else None
        for question in round_result.get("questions", []):
            text = question.get("text")
            if isinstance(text, str) and text:
                questions.append(
                    {
                        "round": round_result.get("round"),
                        "sequence": question.get("sequence"),
                        "topic": topic,
                        "text": text,
                    }
                )

    near_duplicates: list[dict[str, Any]] = []
    for left_index, left in enumerate(questions):
        for right in questions[left_index + 1 :]:
            similarity = _jaccard_similarity(
                _question_terms(left["text"]),
                _question_terms(right["text"]),
            )
            if similarity >= 0.72:
                near_duplicates.append(
                    {
                        "left": {
                            "round": left["round"],
                            "sequence": left["sequence"],
                            "topic": left["topic"],
                        },
                        "right": {
                            "round": right["round"],
                            "sequence": right["sequence"],
                            "topic": right["topic"],
                        },
                        "similarity": round(similarity, 4),
                    }
                )
    return {
        "total_questions": len(questions),
        "near_duplicate_count": len(near_duplicates),
        "near_duplicate_pairs": near_duplicates[:20],
    }


def summarize_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    total = _safe_int(coverage.get("total"))
    uncovered = _safe_int(coverage.get("uncovered"))
    attempted = _safe_int(coverage.get("attempted"))
    verified = _safe_int(coverage.get("verified"))
    points = coverage.get("points")
    if not isinstance(points, list):
        points = []

    status_distribution: dict[str, int] = {}
    normalized_points: list[dict[str, Any]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        status = point.get("status")
        if not isinstance(status, str) or not status:
            status = "unknown"
        status_distribution[status] = status_distribution.get(status, 0) + 1
        normalized_points.append(point)

    top_uncovered_points = _coverage_points_by_priority(
        normalized_points,
        allowed_statuses={"uncovered"},
    )
    weak_or_insufficient_points = _coverage_points_by_priority(
        normalized_points,
        allowed_statuses={"attempted", "insufficient_evidence", "weak"},
    )
    covered = max(total - uncovered, 0)
    return {
        "total": total,
        "uncovered": uncovered,
        "attempted": attempted,
        "verified": verified,
        "attempt_rate": _safe_rate(covered, total),
        "trusted_coverage_rate": _safe_rate(verified, total),
        "status_distribution": dict(sorted(status_distribution.items())),
        "top_uncovered_points": top_uncovered_points[:10],
        "weak_or_insufficient_points": weak_or_insufficient_points[:10],
    }


def summarize_coverage_progress(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    before_by_id = _coverage_points_by_id(before.get("points"))
    after_by_id = _coverage_points_by_id(after.get("points"))

    newly_attempted: list[dict[str, Any]] = []
    newly_verified: list[dict[str, Any]] = []
    for point_id, after_point in after_by_id.items():
        before_status = before_by_id.get(point_id, {}).get("status")
        after_status = after_point.get("status")
        if before_status == "uncovered" and after_status != "uncovered":
            newly_attempted.append(_coverage_point_brief(after_point))
        if before_status not in {"verified", "mastered"} and after_status in {
            "verified",
            "mastered",
        }:
            newly_verified.append(_coverage_point_brief(after_point))

    remaining_uncovered = _coverage_points_by_priority(
        list(after_by_id.values()),
        allowed_statuses={"uncovered"},
    )
    return {
        "delta_total": _safe_int(after.get("total")) - _safe_int(before.get("total")),
        "delta_uncovered": _safe_int(after.get("uncovered"))
        - _safe_int(before.get("uncovered")),
        "delta_attempted": _safe_int(after.get("attempted"))
        - _safe_int(before.get("attempted")),
        "delta_verified": _safe_int(after.get("verified")) - _safe_int(before.get("verified")),
        "newly_attempted_count": len(newly_attempted),
        "newly_attempted_points": newly_attempted[:10],
        "newly_verified_count": len(newly_verified),
        "newly_verified_points": newly_verified[:10],
        "remaining_uncovered_count": len(remaining_uncovered),
        "remaining_uncovered_points": remaining_uncovered[:10],
    }


def _coverage_points_by_priority(
    points: list[dict[str, Any]],
    *,
    allowed_statuses: set[str],
) -> list[dict[str, Any]]:
    selected = [
        _coverage_point_brief(point)
        for point in points
        if isinstance(point.get("status"), str) and point["status"] in allowed_statuses
    ]
    return sorted(selected, key=lambda item: (-_safe_int(item.get("source_count")), item["title"]))


def _coverage_points_by_id(points: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(points, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for point in points:
        if not isinstance(point, dict):
            continue
        point_id = point.get("id")
        if isinstance(point_id, str) and point_id:
            indexed[point_id] = point
    return indexed


def _coverage_point_brief(point: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": point.get("id"),
        "title": str(point.get("title") or point.get("id") or ""),
        "status": point.get("status"),
        "source_count": _safe_int(point.get("source_count")),
        "attempt_count": _safe_int(point.get("attempt_count")),
        "trusted_evaluation_count": _safe_int(point.get("trusted_evaluation_count")),
        "average_score": point.get("average_score"),
    }


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def resolve_knowledge_base_id(
    suite: str,
    base_url: str,
    configured_knowledge_base_id: str,
    override: UUID | None,
) -> str:
    if override is not None:
        return str(override)
    if _knowledge_base_has_documents(base_url, configured_knowledge_base_id):
        return configured_knowledge_base_id

    bases = request_json("GET", f"{base_url}/api/v1/knowledge-bases")
    if not isinstance(bases, list):
        return configured_knowledge_base_id
    candidates: list[dict[str, Any]] = []
    for base in bases:
        if not isinstance(base, dict):
            continue
        base_id = base.get("id")
        if not isinstance(base_id, str) or not _knowledge_base_has_documents(base_url, base_id):
            continue
        candidates.append(base)
    if not candidates:
        return configured_knowledge_base_id
    if len(candidates) == 1:
        return str(candidates[0]["id"])

    preferred_keywords = {
        "agent": ("agent", "ai", "面试", "知识库"),
        "java": ("java", "spring", "jvm", "并发"),
    }.get(suite, ())
    for keyword in preferred_keywords:
        for base in candidates:
            name = str(base.get("name") or "").lower()
            description = str(base.get("description") or "").lower()
            if keyword.lower() in name or keyword.lower() in description:
                return str(base["id"])
    return str(candidates[0]["id"])


def _knowledge_base_has_documents(base_url: str, knowledge_base_id: str) -> bool:
    try:
        documents = request_json(
            "GET",
            f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/documents",
            attempts=1,
        )
    except RuntimeError:
        return False
    return isinstance(documents, list) and len(documents) > 0


def _question_terms(text: str) -> set[str]:
    terms = set(re.findall(r"[a-z0-9_]{2,}", text.lower()))
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        terms.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return terms


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


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
    knowledge_base_id = resolve_knowledge_base_id(
        suite,
        base_url,
        configured_knowledge_base_id,
        knowledge_base_id_override,
    )
    if rounds is not None and rounds < 1:
        raise ValueError("rounds must be greater than 0.")
    planned_rounds = rounds or len(scenarios)
    result: dict[str, Any] = {
        "suite": suite,
        "configured_knowledge_base_id": configured_knowledge_base_id,
        "knowledge_base_id": knowledge_base_id,
        "planned_rounds": planned_rounds,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "rounds": [],
        "failures": [],
    }
    result["profile_before"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/profile/abilities"
    )
    result["runtime"] = request_json("GET", f"{base_url}/health/runtime")
    result["history_before"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/reports/history?limit=100"
    )
    result["coverage_before"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/coverage"
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
            coverage_after_round = request_json(
                "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/coverage"
            )
            round_result["report"] = report
            round_result["profile_after"] = profile
            round_result["coverage_after"] = summarize_coverage(coverage_after_round)
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
            f"coverage={round_result.get('coverage_after', {}).get('trusted_coverage_rate', '-')} "
            f"elapsed={round_result['elapsed_seconds']}s",
            flush=True,
        )

    result["question_angle_summary"] = summarize_question_angles(result["rounds"])
    result["question_generation_summary"] = summarize_question_generation(result["rounds"])
    result["question_cooldown_summary"] = summarize_question_cooldown(result["rounds"])
    result["question_similarity_summary"] = summarize_question_similarity(result["rounds"])
    result["coverage_after"] = request_json(
        "GET", f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/coverage"
    )
    result["coverage_summary_before"] = summarize_coverage(result["coverage_before"])
    result["coverage_summary_after"] = summarize_coverage(result["coverage_after"])
    result["coverage_progress_summary"] = summarize_coverage_progress(
        result["coverage_before"],
        result["coverage_after"],
    )
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
        f"question_angles={result['question_angle_summary']['distribution']} "
        f"generation={result['question_generation_summary']['mode_distribution']} "
        f"cooldown_active={result['question_cooldown_summary']['active_cooldown_questions']} "
        f"near_duplicates={result['question_similarity_summary']['near_duplicate_count']} "
        f"coverage={result['coverage_summary_after']['trusted_coverage_rate']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
