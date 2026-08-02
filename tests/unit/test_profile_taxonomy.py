from agent_mentor.domain.profile_taxonomy import canonical_subtopics, canonical_topic


def test_rag_variants_share_one_stable_topic() -> None:
    assert canonical_topic("RAG").topic_key == "rag"
    assert canonical_topic("RAG 包含检索和生成两个阶段").topic_key == "rag"
    assert canonical_topic("向量检索与引用溯源").topic_key == "rag"


def test_dynamic_required_points_are_collapsed_into_diagnostic_subtopics() -> None:
    topic = canonical_topic("RAG")

    subtopics = canonical_subtopics(
        topic,
        [
            "检索阶段使用 Query 与 Key 的相似度召回",
            "Query 改写能够提升 retrieval recall",
            "生成阶段必须携带证据引用",
        ],
        question_type="concept",
    )

    assert {item.subtopic_key for item in subtopics} == {
        "retrieval",
        "citation",
        "generation",
    }
    assert all(item.topic_key == "rag" for item in subtopics)


def test_routed_training_topic_preserves_parent_and_subtopic() -> None:
    routed_topic = "RAG · 评估与可靠性"
    topic = canonical_topic(routed_topic)
    subtopics = canonical_subtopics(
        topic,
        [routed_topic, "State 支持 checkpoint 和故障恢复"],
        question_type="concept",
    )

    assert topic.topic_key == "rag"
    assert {item.subtopic_key for item in subtopics} == {"evaluation"}


def test_unmatched_details_fall_back_to_stable_question_dimension() -> None:
    topic = canonical_topic("LangGraph")

    first = canonical_subtopics(
        topic,
        ["模型临时生成的一段不稳定描述"],
        question_type="tradeoff",
    )
    second = canonical_subtopics(
        topic,
        ["另一段完全不同的模型描述"],
        question_type="tradeoff",
    )

    assert first[0].subtopic_key == second[0].subtopic_key == "tradeoff"
    assert first[0].storage_key == "subtopic::langgraph::tradeoff"


def test_langchain_and_evaluation_have_independent_stable_topics() -> None:
    assert canonical_topic("LangChain create_agent 与 middleware").topic_key == "langchain"
    assert canonical_topic("Agent Eval 与 LLM-as-Judge").topic_key == "evaluation"


def test_java_backend_has_stable_topic_and_diagnostic_subtopics() -> None:
    topic = canonical_topic("Java 后端 JVM 与 Spring 事务")
    assert topic.topic_key == "java_backend"

    subtopics = canonical_subtopics(
        topic,
        ["分析 Full GC", "解释 happens-before", "排查 @Transactional 失效"],
        question_type="scenario",
    )
    assert {item.subtopic_key for item in subtopics} == {
        "jvm",
        "concurrency",
        "transaction",
    }


def test_evaluation_details_are_collapsed_into_diagnostic_subtopics() -> None:
    topic = canonical_topic("评估与可靠性")
    subtopics = canonical_subtopics(
        topic,
        ["构造离线评测数据集", "设计 Rubric 指标", "LLM-as-Judge 偏差治理"],
        question_type="scenario",
    )

    assert {item.subtopic_key for item in subtopics} == {"dataset", "metrics", "judge"}
