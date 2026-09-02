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
