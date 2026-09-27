from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DraftClaimOrigin(StrEnum):
    HUMAN_FIXTURE = "human_fixture"
    MODEL_DRAFT = "model_draft"


class ExpectedClaimStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DraftClaim:
    claim_id: str
    text: str
    required: bool
    origin: DraftClaimOrigin


@dataclass(frozen=True, slots=True)
class DraftClaimFixture:
    case_id: str
    evidence: str
    claim: DraftClaim
    expected_status: ExpectedClaimStatus
    note: str


def load_draft_claim_fixtures(path: Path) -> tuple[DraftClaimFixture, ...]:
    fixtures: list[DraftClaimFixture] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        case_id = str(data["id"])
        if case_id in seen:
            raise ValueError(f"duplicate fixture id at line {line_number}: {case_id}")
        seen.add(case_id)
        claim_data = data["claim"]
        fixture = DraftClaimFixture(
            case_id=case_id,
            evidence=str(data["evidence"]).strip(),
            claim=DraftClaim(
                claim_id=str(claim_data["id"]),
                text=str(claim_data["text"]).strip(),
                required=bool(claim_data["required"]),
                origin=DraftClaimOrigin(claim_data["origin"]),
            ),
            expected_status=ExpectedClaimStatus(data["expected_status"]),
            note=str(data["note"]).strip(),
        )
        if not fixture.evidence or not fixture.claim.text or not fixture.note:
            raise ValueError(f"blank required field at line {line_number}")
        fixtures.append(fixture)
    if not fixtures:
        raise ValueError("draft claim fixture dataset must not be empty")
    return tuple(fixtures)
