from evals.retrieval_trigger_features import structural_features, structural_trigger


def test_structural_features_measure_new_heading_concepts_without_scores() -> None:
    case = {
        "question": "低置信评分的复核阈值是多少？",
        "top_chunks": [
            {
                "document_logical_name": "评分",
                "heading_path": ["评分", "三种状态"],
            }
        ],
        "supplemental_chunks": [
            {
                "document_logical_name": "评分",
                "heading_path": ["评分", "复核阈值"],
            }
        ],
    }

    features = structural_features(case)

    assert features["same_document_new_heading"] is True
    assert "复核" in features["supplemental_new_terms"]
    assert features["supplemental_novelty_ratio"] > 0


def test_structural_features_do_not_use_labels_or_retrieval_scores() -> None:
    base = {
        "question": "复习任务需要几次验证？",
        "top_chunks": [{"document_logical_name": "画像", "heading_path": ["画像"]}],
        "supplemental_chunks": [
            {
                "document_logical_name": "画像",
                "heading_path": ["画像", "两次验证"],
            }
        ],
    }
    labeled = {
        **base,
        "answerability": "none",
        "first_relevant_rank": 99,
        "supplemental_chunks": [
            {**base["supplemental_chunks"][0], "heading_score": 100.0}
        ],
    }

    assert structural_features(base) == structural_features(labeled)


def test_structural_trigger_requires_missing_terms_added_by_new_heading() -> None:
    assert structural_trigger(
        {
            "primary_heading_coverage": 0.1,
            "supplemental_new_terms": ["复核"],
            "same_document_new_heading": True,
        }
    )
    assert not structural_trigger(
        {
            "primary_heading_coverage": 0.1,
            "supplemental_new_terms": [],
            "same_document_new_heading": True,
        }
    )
