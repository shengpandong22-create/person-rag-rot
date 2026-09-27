from evals.claim_normalization import normalize_claim


def test_normalizes_closed_yes_no_question_without_adding_an_answer() -> None:
    result = normalize_claim("当前 Embedding 是否已经具备企业级向量治理？")

    assert result.hypothesis == "当前 Embedding 已经具备企业级向量治理。"
    assert result.strategy == "closed_question_to_proposition"
    assert result.reason is None


def test_normalizes_capability_question_to_positive_proposition() -> None:
    result = normalize_claim("checkpoint 能否自动续跑？")

    assert result.hypothesis == "checkpoint 能够自动续跑。"


def test_open_value_question_is_not_filled_with_an_invented_answer() -> None:
    result = normalize_claim("HNSW ef_search 的精确值是多少？")

    assert result.hypothesis is None
    assert result.strategy == "requires_candidate_answer"
    assert result.reason == "open_question_has_no_proposition_without_an_answer"


def test_open_explanation_question_requires_candidate_answer() -> None:
    result = normalize_claim("为什么需要 ProfileUpdateEvent？")

    assert result.hypothesis is None
    assert result.strategy == "requires_candidate_answer"
