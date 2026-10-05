import json
from pathlib import Path
from uuid import UUID

import pytest

from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from evals.retrieval_expansion_selector import select_rank_capped_supplemental
from evals.retrieval_expansion_selector_development import judge_selector
from evals.schema import load_dataset

NEGATIVES = Path("evals/datasets/retrieval_expansion_selector_negatives_v1.jsonl")
THRESHOLDS = Path("evals/datasets/RETRIEVAL_EXPANSION_SELECTOR_DEVELOPMENT_THRESHOLDS.json")


def test_rank_capped_selector_preserves_order_and_caps_at_three() -> None:
    chunks = tuple(_chunk(index) for index in range(5))
    assert select_rank_capped_supplemental(chunks) == chunks[:3]


def test_rank_capped_selector_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        select_rank_capped_supplemental((), max_chunks=-1)


def test_selector_negative_fixture_and_thresholds_are_fixed() -> None:
    cases = load_dataset(NEGATIVES, require_graded=True).cases
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    assert len(cases) == 6
    assert all(not case.answerable for case in cases)
    assert thresholds["candidate"] == "rank-capped-3-v1"
    assert thresholds["configuration"]["max_consumed_supplemental"] == 3


def test_selector_judge_requires_recall_precision_and_cost_gates() -> None:
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    metrics = {
        "primary_order_preservation_rate": 1.0,
        "combined_recall": 1.0,
        "primary_miss_incremental_recovery_rate": 1.0,
        "supplemental_consumption_precision": 0.35,
        "average_consumed_supplemental_count": 3.0,
        "consumption_reduction_vs_fixed7": 0.55,
        "negative_average_consumed_count": 3.0,
        "negative_consumption_reduction_vs_fixed7": 0.55,
        "budget_compliance_rate": 1.0,
    }
    assert judge_selector(metrics, thresholds)["qualified"] is True
    metrics["combined_recall"] = 0.9
    assert judge_selector(metrics, thresholds)["qualified"] is False


def _chunk(index: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID(int=index + 1),
        document_id=UUID(int=index + 20),
        document_title="doc",
        source_url=None,
        trust_level="official",
        heading_path=("heading",),
        page_number=None,
        block_type="paragraph",
        chunk_index=index,
        content="content",
        score=1.0,
        retrieval_explanation="test",
    )
