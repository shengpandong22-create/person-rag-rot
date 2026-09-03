from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from uuid import UUID


def _load_audit_runner() -> ModuleType:
    module_path = Path(__file__).parents[2] / "scripts" / "run_knowledge_base_interview_audit.py"
    spec = importlib.util.spec_from_file_location("run_knowledge_base_interview_audit", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_summarize_question_angles_counts_distribution_and_missing_items() -> None:
    runner = _load_audit_runner()
    summarize_question_angles = cast(Any, runner).summarize_question_angles

    summary = summarize_question_angles(
        [
            {
                "questions": [
                    {
                        "rubric": {
                            "question_angle": {
                                "key": "concept_boundary",
                                "title": "概念边界",
                            }
                        }
                    },
                    {
                        "rubric": {
                            "question_angle": {
                                "key": "failure_handling",
                                "title": "异常与降级",
                            }
                        }
                    },
                    {"rubric": {"items": []}},
                ]
            },
            {
                "questions": [
                    {
                        "rubric": {
                            "question_angle": {
                                "key": "concept_boundary",
                                "title": "概念边界",
                            }
                        }
                    }
                ]
            },
        ]
    )

    assert summary == {
        "total_questions": 4,
        "with_question_angle": 3,
        "missing_question_angle": 1,
        "distribution": {
            "concept_boundary:概念边界": 2,
            "failure_handling:异常与降级": 1,
        },
    }


def test_summarize_question_generation_counts_fallback_modes() -> None:
    runner = _load_audit_runner()
    summarize_question_generation = cast(Any, runner).summarize_question_generation

    summary = summarize_question_generation(
        [
            {
                "questions": [
                    {"rubric": {"generation": {"mode": "llm", "fallback_reason": None}}},
                    {
                        "rubric": {
                            "generation": {
                                "mode": "deterministic_similarity_fallback",
                                "fallback_reason": "similar_to_prior_question",
                            }
                        }
                    },
                    {"rubric": {"items": []}},
                ]
            }
        ]
    )

    assert summary == {
        "total_questions": 3,
        "with_generation": 2,
        "missing_generation": 1,
        "mode_distribution": {
            "deterministic_similarity_fallback": 1,
            "llm": 1,
        },
        "fallback_reasons": {"similar_to_prior_question": 1},
    }


def test_summarize_question_cooldown_reports_trace_coverage() -> None:
    runner = _load_audit_runner()
    summarize_question_cooldown = cast(Any, runner).summarize_question_cooldown

    summary = summarize_question_cooldown(
        [
            {
                "questions": [
                    {"rubric": {"generation": {"recent_question_cooldown_count": 0}}},
                    {"rubric": {"generation": {"recent_question_cooldown_count": 3}}},
                    {"rubric": {"generation": {"recent_question_cooldown_count": 6}}},
                    {"rubric": {"generation": {"mode": "llm"}}},
                ]
            }
        ]
    )

    assert summary == {
        "total_questions": 4,
        "with_cooldown_trace": 3,
        "missing_cooldown_trace": 1,
        "active_cooldown_questions": 2,
        "max_recent_question_cooldown_count": 6,
        "average_recent_question_cooldown_count": 3.0,
    }


def test_summarize_question_similarity_reports_near_duplicate_pairs() -> None:
    runner = _load_audit_runner()
    summarize_question_similarity = cast(Any, runner).summarize_question_similarity

    summary = summarize_question_similarity(
        [
            {
                "round": 1,
                "scenario": {"topic": "RAG"},
                "questions": [
                    {
                        "sequence": 1,
                        "text": "请说明 RAG 检索增强生成的核心概念和主要流程。",
                    },
                ],
            },
            {
                "round": 2,
                "scenario": {"topic": "RAG"},
                "questions": [
                    {
                        "sequence": 1,
                        "text": "请说明 RAG 检索增强生成的核心概念以及主要流程。",
                    },
                    {
                        "sequence": 2,
                        "text": "请设计 RAG 服务超时时的降级、监控和故障恢复方案。",
                    },
                ],
            },
        ]
    )

    assert summary["total_questions"] == 3
    assert summary["near_duplicate_count"] == 1
    assert summary["near_duplicate_pairs"][0]["left"] == {
        "round": 1,
        "sequence": 1,
        "topic": "RAG",
    }


def test_summarize_coverage_reports_rates_and_priority_points() -> None:
    runner = _load_audit_runner()
    summarize_coverage = cast(Any, runner).summarize_coverage

    summary = summarize_coverage(
        {
            "total": 5,
            "uncovered": 2,
            "attempted": 1,
            "verified": 2,
            "points": [
                {
                    "id": "rag_boundary",
                    "title": "RAG 知识边界",
                    "status": "uncovered",
                    "source_count": 6,
                    "attempt_count": 0,
                    "trusted_evaluation_count": 0,
                    "average_score": None,
                },
                {
                    "id": "chunking",
                    "title": "分块策略",
                    "status": "uncovered",
                    "source_count": 2,
                    "attempt_count": 0,
                    "trusted_evaluation_count": 0,
                    "average_score": None,
                },
                {
                    "id": "checkpoint",
                    "title": "Checkpoint 恢复",
                    "status": "weak",
                    "source_count": 4,
                    "attempt_count": 2,
                    "trusted_evaluation_count": 2,
                    "average_score": 0.55,
                },
                {
                    "id": "rubric",
                    "title": "Rubric 评分",
                    "status": "verified",
                    "source_count": 3,
                    "attempt_count": 1,
                    "trusted_evaluation_count": 1,
                    "average_score": 0.82,
                },
            ],
        }
    )

    assert summary["attempt_rate"] == 0.6
    assert summary["trusted_coverage_rate"] == 0.4
    assert summary["status_distribution"] == {"uncovered": 2, "verified": 1, "weak": 1}
    assert summary["top_uncovered_points"][0]["id"] == "rag_boundary"
    assert summary["weak_or_insufficient_points"] == [
        {
            "id": "checkpoint",
            "title": "Checkpoint 恢复",
            "status": "weak",
            "source_count": 4,
            "attempt_count": 2,
            "trusted_evaluation_count": 2,
            "average_score": 0.55,
        }
    ]


def test_summarize_coverage_progress_reports_newly_covered_points() -> None:
    runner = _load_audit_runner()
    summarize_coverage_progress = cast(Any, runner).summarize_coverage_progress

    progress = summarize_coverage_progress(
        {
            "total": 3,
            "uncovered": 2,
            "attempted": 1,
            "verified": 0,
            "points": [
                {"id": "rag", "title": "RAG", "status": "uncovered", "source_count": 5},
                {
                    "id": "memory",
                    "title": "Memory",
                    "status": "attempted",
                    "source_count": 3,
                },
                {"id": "tool", "title": "Tool", "status": "uncovered", "source_count": 1},
            ],
        },
        {
            "total": 4,
            "uncovered": 1,
            "attempted": 1,
            "verified": 2,
            "points": [
                {
                    "id": "rag",
                    "title": "RAG",
                    "status": "mastered",
                    "source_count": 5,
                    "attempt_count": 1,
                    "trusted_evaluation_count": 1,
                    "average_score": 0.9,
                },
                {
                    "id": "memory",
                    "title": "Memory",
                    "status": "verified",
                    "source_count": 3,
                    "attempt_count": 2,
                    "trusted_evaluation_count": 1,
                    "average_score": 0.75,
                },
                {"id": "tool", "title": "Tool", "status": "uncovered", "source_count": 1},
                {"id": "mcp", "title": "MCP", "status": "uncovered", "source_count": 2},
            ],
        },
    )

    assert progress["delta_total"] == 1
    assert progress["delta_uncovered"] == -1
    assert progress["delta_verified"] == 2
    assert progress["newly_attempted_count"] == 1
    assert progress["newly_attempted_points"][0]["id"] == "rag"
    assert progress["newly_verified_count"] == 2
    assert {point["id"] for point in progress["newly_verified_points"]} == {"rag", "memory"}
    assert progress["remaining_uncovered_count"] == 2


def test_resolve_knowledge_base_id_prefers_override() -> None:
    runner = _load_audit_runner()
    resolve_knowledge_base_id = cast(Any, runner).resolve_knowledge_base_id

    resolved = resolve_knowledge_base_id(
        "agent",
        "http://localhost:8000",
        "46691546-593a-4d21-bcfc-0d16986c20a7",
        UUID("b2d70e40-02d1-4a78-af5a-22df85a82693"),
    )

    assert resolved == "b2d70e40-02d1-4a78-af5a-22df85a82693"


def test_resolve_knowledge_base_id_falls_back_to_available_agent_base() -> None:
    runner = _load_audit_runner()
    resolve_knowledge_base_id = cast(Any, runner).resolve_knowledge_base_id

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        *,
        attempts: int = 3,
    ) -> Any:
        assert method == "GET"
        assert payload is None
        assert headers is None
        if url.endswith("/knowledge-bases"):
            return [
                {"id": "empty-base", "name": "空知识库", "description": ""},
                {"id": "agent-base", "name": "AgentMentor BGE 面试知识库", "description": ""},
            ]
        if url.endswith("/old-base/documents") or url.endswith("/empty-base/documents"):
            raise RuntimeError("not found")
        if url.endswith("/agent-base/documents"):
            return [{"id": "doc-1", "status": "ready"}]
        raise AssertionError(url)

    cast(Any, runner).request_json = fake_request_json

    resolved = resolve_knowledge_base_id(
        "agent",
        "http://localhost:8000",
        "old-base",
        None,
    )

    assert resolved == "agent-base"
