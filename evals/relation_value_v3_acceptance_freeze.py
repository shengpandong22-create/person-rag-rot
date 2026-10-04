"""Create and verify the reviewed Relation-Value V3 acceptance-set freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ACCEPTANCE_SOURCE_COMMIT = "acf89f3"
ARTIFACTS = {
    "dataset": Path("evals/datasets/relation_value_v3_acceptance_v1.jsonl"),
    "composition_contract": Path(
        "evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_COMPOSITION.json"
    ),
    "annotation_contract": Path(
        "evals/designs/relation_value_v3_acceptance_dataset_design.md"
    ),
    "blind_worksheet": Path(
        "evals/reviews/relation_value_v3_acceptance_blind_worksheet_v1.jsonl"
    ),
    "blind_response": Path(
        "evals/reviews/relation_value_v3_acceptance_blind_response_v1.jsonl"
    ),
    "blind_review_summary": Path(
        "evals/reviews/relation_value_v3_acceptance_blind_response_v1_summary.md"
    ),
    "review_comparison": Path(
        "evals/reviews/relation_value_v3_acceptance_review_comparison_v1.json"
    ),
    "adjudication": Path(
        "evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_ADJUDICATION.json"
    ),
    "freeze_stage_audit": Path(
        "evals/reports/relation_value_v3_acceptance_reviewed/audit.json"
    ),
    "review_report": Path("evals/reports/relation_value_v3_acceptance_reviewed.md"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, dict[str, str]]:
    return {
        name: {"path": path.as_posix(), "sha256": _sha256(path)}
        for name, path in ARTIFACTS.items()
    }


def build_manifest() -> dict[str, Any]:
    audit = json.loads(ARTIFACTS["freeze_stage_audit"].read_text(encoding="utf-8"))
    if not audit.get("audit_passed"):
        raise ValueError("freeze-stage audit has not passed")
    if audit.get("candidate_executed") is not False:
        raise ValueError("acceptance candidate execution must remain false before freezing")
    return {
        "schema_version": "relation-value-v3-acceptance-freeze-v1",
        "dataset": "relation-value-v3-acceptance-v1",
        "source_commit": ACCEPTANCE_SOURCE_COMMIT,
        "freeze_scope": (
            "reviewed acceptance dataset and label-review chain only; no candidate, "
            "retrieval, model, production, or acceptance-run authorization"
        ),
        "artifacts": artifact_hashes(),
        "frozen_at": datetime.now(UTC).isoformat(),
        "review_state": "agreed",
        "freeze_stage_audit_passed": True,
        "candidate_executed": False,
        "next_step_requires_separate_protocol_and_authorization": True,
    }


def verify_manifest(manifest_path: Path) -> tuple[bool, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = artifact_hashes()
    recorded = manifest.get("artifacts", {})
    checks = {
        name: recorded.get(name) == actual.get(name) for name in sorted(ARTIFACTS)
    }
    complete = set(recorded) == set(ARTIFACTS)
    metadata_intact = (
        manifest.get("schema_version") == "relation-value-v3-acceptance-freeze-v1"
        and manifest.get("dataset") == "relation-value-v3-acceptance-v1"
        and manifest.get("source_commit") == ACCEPTANCE_SOURCE_COMMIT
        and manifest.get("review_state") == "agreed"
        and manifest.get("freeze_stage_audit_passed") is True
        and manifest.get("candidate_executed") is False
        and manifest.get("next_step_requires_separate_protocol_and_authorization") is True
    )
    intact = complete and all(checks.values()) and metadata_intact
    return intact, {
        "intact": intact,
        "complete": complete,
        "source_commit": manifest.get("source_commit"),
        "candidate_executed": manifest.get("candidate_executed"),
        "metadata_and_authorization_boundary_intact": metadata_intact,
        "artifact_checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_FREEZE.json"),
    )
    parser.add_argument("--write-freeze", action="store_true")
    args = parser.parse_args()
    if args.write_freeze:
        args.manifest.write_text(
            json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    intact, result = verify_manifest(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not intact:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
