from __future__ import annotations

from pathlib import Path


def test_domain_does_not_depend_on_frameworks() -> None:
    domain_path = Path("src/agent_mentor/domain")
    forbidden = ("fastapi", "sqlalchemy", "langgraph", "langchain", "openai")

    for source_file in domain_path.glob("*.py"):
        source = source_file.read_text(encoding="utf-8").lower()
        has_forbidden_import = any(
            f"import {module}" in source or f"from {module}" in source for module in forbidden
        )
        assert not has_forbidden_import
