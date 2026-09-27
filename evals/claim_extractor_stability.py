from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from evals.claim_extractor import _key, run_extractor_eval
from evals.freeze import file_sha256
from evals.provenance import collect_git_state


def _claim_keys(case: dict[str, Any]) -> set[str]:
    return {_key(claim["text"]) for claim in case["extracted_claims"]}


def compute_stability_metrics(runs: list[dict[str, Any]]) -> dict[str, float | int]:
    if len(runs) < 2:
        raise ValueError("stability evaluation requires at least two runs")
    case_maps = [{case["id"]: _claim_keys(case) for case in run["cases"]} for run in runs]
    case_ids = set(case_maps[0])
    if any(set(case_map) != case_ids for case_map in case_maps[1:]):
        raise ValueError("all runs must contain the same case ids")
    exact = 0
    jaccards: list[float] = []
    for case_id in sorted(case_ids):
        sets = [case_map[case_id] for case_map in case_maps]
        exact += all(claims == sets[0] for claims in sets[1:])
        for left, right in combinations(sets, 2):
            union = left | right
            jaccards.append(len(left & right) / len(union) if union else 1.0)
    metric_names = (
        "schema_valid_rate",
        "required_claim_recall",
        "extra_claim_rate",
        "unsupported_claim_rate",
        "nli_retained_claim_rate",
        "semantic_duplicate_rate",
        "semantic_duplicate_candidate_rate",
        "semantic_duplicate_subject_rejection_rate",
        "subject_signature_resolution_rate",
    )
    result: dict[str, float | int] = {
        "run_count": len(runs),
        "case_count": len(case_ids),
        "exact_claim_set_stability_rate": round(exact / len(case_ids), 4),
        "mean_pairwise_claim_jaccard": round(sum(jaccards) / len(jaccards), 4),
    }
    for name in metric_names:
        values = [float(run["metrics"][name]) for run in runs]
        result[f"{name}_min"] = min(values)
        result[f"{name}_max"] = max(values)
    return result


def verify_freeze(dataset: Path, manifest: Path) -> dict[str, Any]:
    record = json.loads(manifest.read_text(encoding="utf-8"))
    actual = file_sha256(dataset)
    if record["sha256"] != actual:
        raise ValueError(f"frozen dataset hash mismatch: expected {record['sha256']}, got {actual}")
    return record


async def run_stability_eval(
    dataset: Path, manifest: Path, output_dir: Path, batch_size: int, run_count: int
) -> dict[str, Any]:
    if run_count < 2:
        raise ValueError("run_count must be at least 2")
    freeze = verify_freeze(dataset, manifest)
    runs: list[dict[str, Any]] = []
    for index in range(1, run_count + 1):
        run = await run_extractor_eval(dataset, output_dir / f"run_{index}", batch_size)
        runs.append(run)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        **collect_git_state().to_json(),
        "dataset": str(dataset),
        "dataset_sha256": file_sha256(dataset),
        "freeze_manifest": str(manifest),
        "freeze_manifest_sha256": file_sha256(manifest),
        "freeze_case_count": freeze["case_count"],
        "metrics": compute_stability_metrics(runs),
        "runs": runs,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "claim_extractor_stability.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeated frozen DraftClaim extraction evals.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    result = asyncio.run(
        run_stability_eval(
            args.dataset, args.freeze_manifest, args.output_dir, args.batch_size, args.runs
        )
    )
    print(result["metrics"])


if __name__ == "__main__":
    main()
