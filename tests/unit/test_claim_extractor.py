from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.claim_extractor import (
    DraftClaimExtractionOutput,
    compute_extractor_metrics,
    load_extraction_fixtures,
    mark_semantic_duplicates,
)
from evals.nli_gate import NLIPairScore

DATASET = Path("evals/datasets/draft_claim_extraction_development_v1.jsonl")
FROZEN_DATASET = Path("evals/datasets/draft_claim_extraction_development_v2.jsonl")


def test_extraction_output_enforces_strict_draft_claim_schema() -> None:
    output = DraftClaimExtractionOutput.model_validate(
        {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "text": "这是一个声明。",
                    "required": True,
                    "origin": "model_draft",
                }
            ]
        }
    )

    assert output.claims[0].origin == "model_draft"
    with pytest.raises(ValidationError):
        DraftClaimExtractionOutput.model_validate(
            {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "text": "这是一个声明。",
                        "required": True,
                        "origin": "human_fixture",
                        "unexpected": "rejected",
                    }
                ]
            }
        )


def test_load_extraction_fixtures_validates_development_dataset() -> None:
    fixtures = load_extraction_fixtures(DATASET)

    assert len(fixtures) == 5
    assert sum(claim.required for fixture in fixtures for claim in fixture.expected_claims) == 10


def test_frozen_development_dataset_covers_adversarial_categories() -> None:
    fixtures = load_extraction_fixtures(FROZEN_DATASET)

    assert len(fixtures) == 15
    assert {
        "long_answer",
        "compound_sentence",
        "duplicate_claim",
        "implicit_paraphrase",
        "format_anomaly",
    } <= {fixture.category for fixture in fixtures}


def test_compute_extractor_metrics() -> None:
    rows = [
        {
            "schema_valid": True,
            "required_count": 2,
            "required_hit_count": 1,
            "extra_count": 1,
            "extracted_claims": [
                {"text": "supported", "nli_status": "supported"},
                {"text": "unknown", "nli_status": "unknown"},
            ],
        },
        {
            "schema_valid": False,
            "required_count": 2,
            "required_hit_count": 2,
            "extra_count": 0,
            "extracted_claims": [],
        },
    ]

    assert compute_extractor_metrics(rows) == {
        "schema_valid_rate": 0.5,
        "required_claim_recall": 0.75,
        "extra_claim_rate": 0.5,
        "unsupported_claim_rate": 0.5,
        "nli_retained_claim_rate": 0.5,
        "semantic_duplicate_rate": 0.0,
        "total_extracted_claims": 2,
    }


class _FakeNLI:
    def score(
        self, pairs: list[tuple[str, str, str]], batch_size: int
    ) -> list[NLIPairScore]:
        del batch_size
        return [
            NLIPairScore(pair_id, 0.9, 0.05, 0.05, "entailment")
            for pair_id, _premise, _hypothesis in pairs
        ]


def test_mark_semantic_duplicates_requires_bidirectional_entailment() -> None:
    rows = [
        {
            "id": "case-1",
            "extracted_claims": [
                {"claim_id": "c1", "text": "默认行为保持不变。"},
                {"claim_id": "c2", "text": "默认行为没有改变。"},
            ],
        }
    ]

    mark_semantic_duplicates(rows, _FakeNLI(), 8)

    assert rows[0]["semantic_duplicate_count"] == 1
    assert rows[0]["extracted_claims"][1]["semantic_duplicate_of"] == "c1"
