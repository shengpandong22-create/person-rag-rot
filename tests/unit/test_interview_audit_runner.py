from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


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
