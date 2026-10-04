import json
from pathlib import Path

from evals.relation_value_v3_acceptance_execution_freeze import (
    ARTIFACTS,
    artifact_hashes,
    build_manifest,
    verify_manifest,
)

MANIFEST = Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_EXECUTION_FREEZE.json")


def test_execution_freeze_contains_every_declared_artifact() -> None:
    hashes = artifact_hashes()

    assert set(hashes) == set(ARTIFACTS)
    assert all(len(record["sha256"]) == 64 for record in hashes.values())


def test_execution_freeze_preserves_authorization_boundary() -> None:
    manifest = build_manifest()

    assert manifest["formal_run_started_at_freeze"] is False
    assert manifest["candidate_executed"] is False
    assert manifest["execution_requires_explicit_user_authorization"] is True


def test_execution_freeze_is_intact() -> None:
    intact, result = verify_manifest(MANIFEST)

    assert intact, result


def test_execution_freeze_detects_runner_drift(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["artifacts"]["runner"]["sha256"] = "0" * 64
    changed = tmp_path / "freeze.json"
    changed.write_text(json.dumps(manifest), encoding="utf-8")

    intact, result = verify_manifest(changed)

    assert not intact
    assert result["artifact_checks"]["runner"] is False
