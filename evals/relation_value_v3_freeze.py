"""Create and verify the eval-only Relation-Value V3 candidate freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ARTIFACTS = {
    "implementation": Path("evals/relation_value_binding_v3.py"),
    "original_development_dataset": Path(
        "evals/datasets/retrieval_relation_value_development_v1.jsonl"
    ),
    "semantic_role_development_dataset": Path(
        "evals/datasets/relation_value_role_development_v1.jsonl"
    ),
    "original_development_report": Path(
        "evals/reports/relation_value_binding_v3_development/result.json"
    ),
    "semantic_role_development_report": Path(
        "evals/reports/relation_value_role_development_v1/result.json"
    ),
    "qualification_thresholds": Path(
        "evals/datasets/RELATION_VALUE_V3_FREEZE_THRESHOLDS.json"
    ),
}


def artifact_hashes() -> dict[str, dict[str, str]]:
    return {
        name: {"path": path.as_posix(), "sha256": _sha256(path)}
        for name, path in ARTIFACTS.items()
    }


def build_manifest() -> dict[str, Any]:
    thresholds = json.loads(
        ARTIFACTS["qualification_thresholds"].read_text(encoding="utf-8")
    )
    return {
        "candidate": thresholds["candidate"],
        "candidate_commit": thresholds["candidate_commit"],
        "freeze_scope": "eval-only candidate; no production or formal split authorization",
        "artifacts": artifact_hashes(),
        "frozen_at": datetime.now(UTC).isoformat(),
        "qualification_result": "qualified_for_freeze",
        "next_step_requires_separate_authorization": True,
    }


def verify_manifest(manifest_path: Path) -> tuple[bool, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = artifact_hashes()
    checks = {
        name: record == actual.get(name)
        for name, record in manifest.get("artifacts", {}).items()
    }
    expected_names = set(ARTIFACTS)
    complete = set(checks) == expected_names
    intact = complete and all(checks.values())
    return intact, {
        "intact": intact,
        "complete": complete,
        "candidate": manifest.get("candidate"),
        "candidate_commit": manifest.get("candidate_commit"),
        "artifact_checks": checks,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json"),
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
