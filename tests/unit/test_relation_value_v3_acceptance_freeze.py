import json
from pathlib import Path

import pytest

from evals.relation_value_v3_acceptance_freeze import (
    ARTIFACTS,
    artifact_hashes,
    build_manifest,
    verify_manifest,
)

MANIFEST = Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_FREEZE.json")


def test_acceptance_freeze_contains_every_declared_artifact() -> None:
    hashes = artifact_hashes()

    assert set(hashes) == set(ARTIFACTS)
    assert all(len(record["sha256"]) == 64 for record in hashes.values())


def test_acceptance_freeze_preserves_authorization_boundary() -> None:
    manifest = build_manifest()

    assert manifest["candidate_executed"] is False
    assert manifest["next_step_requires_separate_protocol_and_authorization"] is True


def test_acceptance_freeze_is_intact() -> None:
    intact, result = verify_manifest(MANIFEST)

    assert intact, result


def test_acceptance_freeze_detects_artifact_drift(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["artifacts"]["dataset"]["sha256"] = "0" * 64
    changed = tmp_path / "freeze.json"
    changed.write_text(json.dumps(manifest), encoding="utf-8")

    intact, result = verify_manifest(changed)

    assert not intact
    assert result["artifact_checks"]["dataset"] is False


def test_acceptance_freeze_detects_authorization_drift(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["candidate_executed"] = True
    changed = tmp_path / "freeze.json"
    changed.write_text(json.dumps(manifest), encoding="utf-8")

    intact, result = verify_manifest(changed)

    assert not intact
    assert result["metadata_and_authorization_boundary_intact"] is False


def test_acceptance_freeze_refuses_failed_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed_audit = tmp_path / "audit.json"
    failed_audit.write_text(
        json.dumps({"audit_passed": False, "candidate_executed": False}),
        encoding="utf-8",
    )
    monkeypatch.setitem(ARTIFACTS, "freeze_stage_audit", failed_audit)

    with pytest.raises(ValueError, match="audit has not passed"):
        build_manifest()
