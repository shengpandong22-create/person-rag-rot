from dataclasses import replace
from uuid import UUID

from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from evals.retrieval_expansion_trigger_features_v2 import expansion_trigger_features


def test_features_measure_heading_novelty_relation_overlap_and_redundancy() -> None:
    primary = (_chunk(1, "评分", ("评分", "状态")),)
    supplemental = (_chunk(2, "评分", ("评分", "复核关系")),)
    features = expansion_trigger_features("复核关系是什么", primary, supplemental)
    assert features["new_heading_path_ratio"] == 1.0
    assert features["same_document_new_heading_ratio"] == 1.0
    assert features["new_document_ratio"] == 0.0
    assert features["question_heading_novelty"] > 0


def test_features_do_not_read_labels_scores_or_case_ids() -> None:
    primary = (_chunk(1, "主文档", ("主文档", "主题")),)
    supplemental = (_chunk(2, "新文档", ("新文档", "关系")),)
    changed_scores = (
        replace(supplemental[0], score=-100.0, heading_score=-100.0, vector_score=-100.0),
    )
    assert expansion_trigger_features("关系是什么", primary, supplemental) == (
        expansion_trigger_features("关系是什么", primary, changed_scores)
    )


def _chunk(index: int, document: str, heading: tuple[str, ...]) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID(int=index),
        document_id=UUID(int=index + 10),
        document_title=document,
        document_logical_name=document,
        source_url=None,
        trust_level="official",
        heading_path=heading,
        page_number=None,
        block_type="paragraph",
        chunk_index=index,
        content="content",
        score=999.0,
        retrieval_explanation="ignored",
    )
