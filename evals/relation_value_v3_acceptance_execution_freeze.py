"""Freeze and verify the V3 acceptance runner and machine judge identity."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REVIEWED_BASE_COMMIT = "ac7949b"
ARTIFACTS = {
    "runner": Path("evals/relation_value_v3_acceptance_runner.py"),
    "machine_judge": Path("evals/relation_value_v3_acceptance_qualification.py"),
    "execution_freeze_verifier": Path(
        "evals/relation_value_v3_acceptance_execution_freeze.py"
    ),
    "runner_tests": Path("tests/unit/test_relation_value_v3_acceptance_runner.py"),
    "protocol_tests": Path("tests/unit/test_relation_value_v3_acceptance_protocol.py"),
    "protocol": Path("evals/designs/relation_value_v3_acceptance_protocol.md"),
    "thresholds": Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_THRESHOLDS.json"),
    "candidate_freeze": Path("evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json"),
    "acceptance_freeze": Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_FREEZE.json"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, dict[str, str]]:
    return {
        name: {"path": path.as_posix(), "sha256": _sha256(path)}
        for name, path in ARTIFACTS.items()
    }


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": "relation-value-v3-acceptance-execution-freeze-v1",
        "candidate": "relation-value-binding-v3",
        "reviewed_base_commit": REVIEWED_BASE_COMMIT,
        "freeze_scope": (
            "acceptance runner, machine judge, protocol, thresholds, and upstream "
            "freeze identities; no acceptance-run or production authorization"
        ),
        "artifacts": artifact_hashes(),
        "frozen_at": datetime.now(UTC).isoformat(),
        "formal_run_started_at_freeze": False,
        "candidate_executed": False,
        "execution_requires_explicit_user_authorization": True,
    }


def verify_manifest(manifest_path: Path) -> tuple[bool, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = artifact_hashes()
    recorded = manifest.get("artifacts", {})
    checks = {
        name: recorded.get(name) == actual.get(name) for name in sorted(ARTIFACTS)
    }
    complete = set(recorded) == set(ARTIFACTS)
    boundary_intact = (
        manifest.get("schema_version")
        == "relation-value-v3-acceptance-execution-freeze-v1"
        and manifest.get("candidate") == "relation-value-binding-v3"
        and manifest.get("reviewed_base_commit") == REVIEWED_BASE_COMMIT
        and manifest.get("formal_run_started_at_freeze") is False
        and manifest.get("candidate_executed") is False
        and manifest.get("execution_requires_explicit_user_authorization") is True
    )
    intact = complete and all(checks.values()) and boundary_intact
    return intact, {
        "intact": intact,
        "complete": complete,
        "reviewed_base_commit": manifest.get("reviewed_base_commit"),
        "formal_run_started_at_freeze": manifest.get("formal_run_started_at_freeze"),
        "candidate_executed": manifest.get("candidate_executed"),
        "authorization_boundary_intact": boundary_intact,
        "artifact_checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_EXECUTION_FREEZE.json"
        ),
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
