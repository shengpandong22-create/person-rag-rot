from agent_mentor.application.coverage_catalog import catalog_point_key, catalog_title


def test_catalog_title_prefers_specific_deep_heading() -> None:
    assert catalog_title(["Java 并发", "知识点：volatile 可见性"], "正文") == "volatile 可见性"


def test_catalog_title_ignores_generic_heading_and_uses_content() -> None:
    assert catalog_title(["核心知识点"], "缓存穿透与布隆过滤器\n正文") == "缓存穿透与布隆过滤器"


def test_catalog_key_is_stable_across_spacing_and_punctuation() -> None:
    assert catalog_point_key("Cache-Aside 模式") == catalog_point_key("cache aside模式")
