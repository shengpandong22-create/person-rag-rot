from pathlib import Path

from evals.relation_value_v3_freeze import ARTIFACTS, artifact_hashes, verify_manifest

MANIFEST = Path("evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json")


def test_v3_candidate_freeze_contains_every_declared_artifact() -> None:
    hashes = artifact_hashes()

    assert set(hashes) == set(ARTIFACTS)
    assert all(len(record["sha256"]) == 64 for record in hashes.values())


def test_v3_candidate_freeze_is_intact() -> None:
    intact, result = verify_manifest(MANIFEST)

    assert intact, result
