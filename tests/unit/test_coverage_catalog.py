from agent_mentor.application.coverage_catalog import catalog_point_key, catalog_title


def test_catalog_title_prefers_specific_deep_heading() -> None:
    assert catalog_title(["Java 并发", "知识点：volatile 可见性"], "正文") == "volatile 可见性"


def test_catalog_title_ignores_generic_heading_and_uses_content() -> None:
    assert catalog_title(["核心知识点"], "缓存穿透与布隆过滤器\n正文") == "缓存穿透与布隆过滤器"


def test_catalog_title_skips_numbered_generic_learning_headings() -> None:
    assert (
        catalog_title(
            ["第 2 课：知识入库链路", "2.1 先说结论"],
            "文档入库链路包含上传、解析、切分、向量化和索引。",
        )
        is None
    )


def test_catalog_title_skips_self_test_and_diagram_headings() -> None:
    assert catalog_title(["3.10 完整 RAG 链路", "2.9 核心链路图"], "正文") is None
    assert catalog_title(["三、自测结果"], "第 2 题需要加强。") is None


def test_catalog_title_skips_chinese_numbered_container_headings() -> None:
    assert catalog_title(["一、教案正文"], "项目通过 RAG 和面试评分形成训练闭环。") is None
    assert catalog_title(["二、学员疑问与讨论记录"], "Q1：为什么不使用 LangGraph？") is None


def test_catalog_title_falls_back_from_vague_modifier_to_parent_topic() -> None:
    assert (
        catalog_title(["2.6 Embedding 阶段：当前的真实实现", "它的价值"], "正文")
        == "Embedding 阶段：当前的真实实现"
    )


def test_catalog_key_is_stable_across_spacing_and_punctuation() -> None:
    assert catalog_point_key("Cache-Aside 模式") == catalog_point_key("cache aside模式")
