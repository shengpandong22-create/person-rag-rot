from scripts.audit_catalog_reindex_plan import document_diff

from agent_mentor.application.coverage_catalog import CatalogCandidate


def test_document_diff_does_not_treat_rejected_heading_as_catalog_candidate() -> None:
    result = document_diff(
        existing_titles={"旧知识点"},
        candidates=[
            CatalogCandidate("可靠知识点", "accepted_heading"),
            CatalogCandidate(None, "rejected_non_knowledge_leaf"),
        ],
    )

    assert result["candidate_titles"] == ["可靠知识点"]
    assert result["would_add_titles"] == ["可靠知识点"]
    assert result["would_unlink_titles"] == ["旧知识点"]
    assert result["candidate_decisions"] == {
        "accepted_heading": 1,
        "rejected_non_knowledge_leaf": 1,
    }
