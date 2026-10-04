import pytest

from evals.relation_value_v3_adjudicate import adjudicate


def test_adjudication_requires_every_disagreement_decision() -> None:
    with pytest.raises(ValueError, match="coverage mismatch"):
        adjudicate(
            [],
            {"differences": {"rva3-001": []}},
            {"decisions": {}, "reviewer": "reviewer"},
        )
