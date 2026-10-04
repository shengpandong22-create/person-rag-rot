"""One-shot runner for the frozen Relation-Value V3 acceptance protocol.

Importing this module or running its unit tests does not execute the acceptance set. The CLI
requires the explicit confirmation token declared below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from evals.relation_value_binding_v3 import (
    EvidenceProvenance,
    TypedBoundValue,
    TypedRelationDemand,
    bind_typed_relation_value,
    normalize_demand,
)
from evals.relation_value_v3_acceptance_audit import load_jsonl
from evals.relation_value_v3_acceptance_execution_freeze import (
    verify_manifest as verify_execution_freeze,
)
from evals.relation_value_v3_acceptance_freeze import (
    verify_manifest as verify_acceptance_freeze,
)
from evals.relation_value_v3_acceptance_qualification import qualify
from evals.relation_value_v3_freeze import verify_manifest as verify_candidate_freeze
from evals.relation_value_v3_regression_safety import production_imports_candidate

CONFIRMATION = "RUN-FROZEN-V3-ACCEPTANCE-ONCE"
THRESHOLDS = Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_THRESHOLDS.json")
THRESHOLDS_SHA256 = "3ab4309c12c631e0dd1030b81b2a01e6d4a27dbda5039253a82bec366213a67c"
FINAL_OUTPUT_DIR = Path("evals/reports/relation_value_v3_acceptance_final")
EXECUTION_FREEZE = Path(
    "evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_EXECUTION_FREEZE.json"
)
Binder = Callable[..., tuple[TypedBoundValue, ...]]
Normalizer = Callable[[str, str | None, str], TypedRelationDemand]


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    binder: Binder = bind_typed_relation_value,
    normalizer: Normalizer = normalize_demand,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    latencies: list[float] = []
    unresolved = 0
    errors = 0
    for row in rows:
        demand_results: list[dict[str, Any]] = []
        evidence_by_id = {item["evidence_id"]: item for item in row["evidence"]}
        for label in row["demands"]:
            selected = (
                [evidence_by_id[item] for item in label["evidence_ids"]]
                if label["expected_binding"]
                else list(row["evidence"])
            )
            try:
                demand = normalizer(
                    label["requested_relation"],
                    label.get("canonical_unit"),
                    row["primary_span_type"],
                )
                started = clock()
                emitted = [
                    binding
                    for evidence in selected
                    for binding in binder(
                        demand,
                        provenance=_provenance(evidence),
                        content=evidence["span_text"],
                    )
                ]
                elapsed_ms = (clock() - started) * 1000
                latencies.append(elapsed_ms)
                result = _score_demand(row, label, selected, demand, emitted, elapsed_ms)
            except (KeyError, TypeError, ValueError) as exc:
                errors += 1
                unresolved += 1
                result = {
                    "demand_id": label.get("demand_id"),
                    "expected_binding": label.get("expected_binding"),
                    "passed": False,
                    "correct_binding": False,
                    "binding_count": 0,
                    "correct_binding_count": 0,
                    "spurious_binding_count": 0,
                    "latency_ms": None,
                    "failure_category": "evaluator_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "bindings": [],
                }
            demand_results.append(result)
        cases.append(
            {
                "id": row["id"],
                "answerability": row["answerability"],
                "confusion_type": row.get("confusion_type"),
                "pair_id": row.get("pair_id"),
                "passed": all(item["passed"] for item in demand_results),
                "demands": demand_results,
            }
        )
    return _build_report(cases, latencies, unresolved=unresolved, errors=errors)


def _score_demand(
    row: dict[str, Any],
    label: dict[str, Any],
    evidence: list[dict[str, Any]],
    demand: TypedRelationDemand,
    emitted: list[TypedBoundValue],
    elapsed_ms: float,
) -> dict[str, Any]:
    correct_flags = [
        _binding_matches(binding, demand, label, evidence) for binding in emitted
    ]
    correct_count = sum(correct_flags)
    expected = bool(label["expected_binding"])
    passed = correct_count > 0 if expected else not emitted
    return {
        "demand_id": label["demand_id"],
        "expected_binding": expected,
        "relation_role": label["relation_role"],
        "value_semantic": label["value_semantic"],
        "span_type": row["primary_span_type"],
        "passed": passed,
        "correct_binding": correct_count > 0,
        "binding_count": len(emitted),
        "correct_binding_count": correct_count,
        "spurious_binding_count": len(emitted) - correct_count,
        "latency_ms": round(elapsed_ms, 6),
        "failure_category": _failure_category(expected, emitted, correct_count),
        "normalized_demand": asdict(demand),
        "bindings": [
            {**asdict(binding), "fully_correct": correct}
            for binding, correct in zip(emitted, correct_flags, strict=True)
        ],
    }


def _binding_matches(
    binding: TypedBoundValue,
    demand: TypedRelationDemand,
    label: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> bool:
    accepted = label.get("accepted_value_sets") or []
    values_match = any(
        _values_equal(binding.values, tuple(str(value) for value in values), demand.role.value)
        for values in accepted
    )
    provenance_keys = {
        (
            item["chunk_id"],
            item["document_logical_name"],
            tuple(item["heading_path"]),
            item["span_type"],
        )
        for item in evidence
    }
    provenance_key = (
        binding.provenance.chunk_id,
        binding.provenance.document_logical_name,
        binding.provenance.heading_path,
        binding.span_type,
    )
    return (
        values_match
        and demand.role.value == label["relation_role"]
        and demand.value_semantic.value == label["value_semantic"]
        and demand.canonical_unit == label.get("canonical_unit")
        and demand.modality.value == label["modality"]
        and binding.role.value == label["relation_role"]
        and binding.value_semantic.value == label["value_semantic"]
        and binding.canonical_unit == label.get("canonical_unit")
        and provenance_key in provenance_keys
    )


def _values_equal(observed: tuple[str, ...], accepted: tuple[str, ...], role: str) -> bool:
    normalized_observed = tuple(_normalize_value(value) for value in observed)
    normalized_accepted = tuple(_normalize_value(value) for value in accepted)
    if role == "sequence":
        return normalized_observed == normalized_accepted
    return sorted(normalized_observed) == sorted(normalized_accepted)


def _normalize_value(value: str) -> str:
    return value.strip().casefold().replace("％", "%")


def _provenance(evidence: dict[str, Any]) -> EvidenceProvenance:
    return EvidenceProvenance(
        chunk_id=evidence["chunk_id"],
        document_logical_name=evidence["document_logical_name"],
        heading_path=tuple(evidence["heading_path"]),
    )


def _failure_category(
    expected: bool, emitted: list[TypedBoundValue], correct_count: int
) -> str | None:
    if not expected:
        return None if not emitted else "false_binding"
    if not emitted:
        return "binding_miss"
    if not correct_count:
        return "binding_mismatch"
    return None


def _build_report(
    cases: list[dict[str, Any]],
    latencies: list[float],
    *,
    unresolved: int,
    errors: int,
) -> dict[str, Any]:
    demands = [demand for case in cases for demand in case["demands"]]
    positives = [item for item in demands if item["expected_binding"]]
    negatives = [item for item in demands if not item["expected_binding"]]
    positive_cases = [case for case in cases if case["answerability"] == "full"]
    negative_cases = [case for case in cases if case["answerability"] == "none"]
    emitted_count = sum(item["binding_count"] for item in demands)
    correct_binding_count = sum(item["correct_binding_count"] for item in demands)
    paired = _paired_results(cases)
    return {
        "candidate": "relation-value-binding-v3",
        "counts": {
            "evaluated_rows": len(cases),
            "evaluated_demands": len(demands),
            "unresolved_labels": unresolved,
            "case_errors": errors,
        },
        "metrics": {
            "demand_accuracy": _rate(sum(item["passed"] for item in demands), len(demands)),
            "positive_demand_recall": _rate(
                sum(item["correct_binding"] for item in positives), len(positives)
            ),
            "positive_row_all_demands_accuracy": _rate(
                sum(case["passed"] for case in positive_cases), len(positive_cases)
            ),
            "negative_demand_rejection": _rate(
                sum(item["passed"] for item in negatives), len(negatives)
            ),
            "negative_row_rejection": _rate(
                sum(case["passed"] for case in negative_cases), len(negative_cases)
            ),
            "binding_precision": _rate(correct_binding_count, emitted_count),
            "average_bindings_per_demand": round(emitted_count / len(demands), 4)
            if demands
            else 0.0,
            "max_bindings_per_demand": max(
                (item["binding_count"] for item in demands), default=0
            ),
            "paired_discrimination": _rate(sum(paired.values()), len(paired)),
            "span_success_counts": _success_counts(positives, "span_type"),
            "role_success_counts": _success_counts(positives, "relation_role"),
            "semantic_success_counts": _success_counts(positives, "value_semantic"),
            "negative_category_rejection": _negative_category_rates(negative_cases),
            "candidate_p50_ms": round(_percentile(latencies, 0.50), 6),
            "candidate_p95_ms": round(_percentile(latencies, 0.95), 6),
        },
        "pair_results": paired,
        "cases": cases,
    }


def _success_counts(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(Counter(item[field] for item in items if item["correct_binding"]))


def _negative_category_rates(cases: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        grouped[str(case["confusion_type"])].append(bool(case["passed"]))
    return {name: _rate(sum(values), len(values)) for name, values in sorted(grouped.items())}


def _paired_results(cases: list[dict[str, Any]]) -> dict[str, bool]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        if case["pair_id"]:
            grouped[str(case["pair_id"])].append(case)
    return {
        pair_id: len(rows) == 2
        and {row["answerability"] for row in rows} == {"full", "none"}
        and all(row["passed"] for row in rows)
        for pair_id, rows in sorted(grouped.items())
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * quantile) - 1)]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _package_versions(names: tuple[str, ...]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _human_summary(result: dict[str, Any], report: dict[str, Any]) -> str:
    accepted = result["accepted_for_production_integration_design"]
    failed = [name for name, passed in result["checks"].items() if not passed]
    failed_cases = [case["id"] for case in report["cases"] if not case["passed"]]
    metrics = report["metrics"]
    return (
        "# Relation-Value V3 Acceptance Result\n\n"
        f"- Accepted for production integration design: `{str(accepted).lower()}`\n"
        f"- Demand accuracy: `{metrics['demand_accuracy']:.4f}`\n"
        f"- Positive demand recall: `{metrics['positive_demand_recall']:.4f}`\n"
        f"- Positive all-demands row accuracy: "
        f"`{metrics['positive_row_all_demands_accuracy']:.4f}`\n"
        f"- Negative demand rejection: `{metrics['negative_demand_rejection']:.4f}`\n"
        f"- Binding precision: `{metrics['binding_precision']:.4f}`\n"
        f"- Candidate P95: `{metrics['candidate_p95_ms']:.6f} ms`\n"
        f"- Failed gates: {', '.join(failed) if failed else 'none'}\n"
        f"- Failed cases: {', '.join(failed_cases) if failed_cases else 'none'}\n"
        "- Scope: eval-only; this result does not change the production default.\n"
        "- Limitation: the fixture measures frozen labeled evidence binding, not retrieval recall "
        "or end-to-end answer quality.\n"
    )


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit("confirmation token mismatch; acceptance was not executed")
    if FINAL_OUTPUT_DIR.exists():
        raise SystemExit("output directory already exists; refusing a rerun")

    if _sha256(THRESHOLDS) != THRESHOLDS_SHA256:
        raise SystemExit("threshold protocol hash mismatch; acceptance was not executed")
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    candidate_manifest = Path(thresholds["candidate_freeze_manifest"])
    acceptance_manifest = Path(thresholds["acceptance_freeze_manifest"])
    candidate_before, _ = verify_candidate_freeze(candidate_manifest)
    acceptance_before, _ = verify_acceptance_freeze(acceptance_manifest)
    execution_before, _ = verify_execution_freeze(EXECUTION_FREEZE)
    hashes_match = (
        _sha256(candidate_manifest) == thresholds["candidate_freeze_manifest_sha256"]
        and _sha256(acceptance_manifest)
        == thresholds["acceptance_freeze_manifest_sha256"]
        and _sha256(Path(thresholds["acceptance_dataset"]))
        == thresholds["acceptance_dataset_sha256"]
    )
    if (
        not candidate_before
        or not acceptance_before
        or not execution_before
        or not hashes_match
    ):
        raise SystemExit("frozen input verification failed; acceptance was not executed")

    FINAL_OUTPUT_DIR.mkdir(parents=True)
    ledger_path = FINAL_OUTPUT_DIR / "attempt.json"
    started_at = datetime.now(UTC).isoformat()
    ledger = {
        "status": "started",
        "started_at": started_at,
        "git_commit": _git_commit(),
        "candidate_freeze_sha256": _sha256(candidate_manifest),
        "acceptance_freeze_sha256": _sha256(acceptance_manifest),
        "dataset_sha256": _sha256(Path(thresholds["acceptance_dataset"])),
        "case_output_persisted": False,
    }
    _atomic_json(ledger_path, ledger)
    try:
        report = evaluate_rows(load_jsonl(Path(thresholds["acceptance_dataset"])))
        report["metadata"] = {
            "git_commit": ledger["git_commit"],
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "platform": platform.platform(),
            "dependency_versions": _package_versions(
                ("sqlalchemy", "pydantic", "pydantic-settings")
            ),
            "thresholds_sha256": _sha256(THRESHOLDS),
            "candidate_freeze_sha256": ledger["candidate_freeze_sha256"],
            "acceptance_freeze_sha256": ledger["acceptance_freeze_sha256"],
            "dataset_sha256": ledger["dataset_sha256"],
            "retrieval_enabled": False,
            "database_lookup_enabled": False,
            "model_inference_enabled": False,
            "command": " ".join(sys.argv),
        }
        _atomic_json(FINAL_OUTPUT_DIR / "raw_report.json", report)
        ledger["case_output_persisted"] = True
        candidate_after, _ = verify_candidate_freeze(candidate_manifest)
        acceptance_after, _ = verify_acceptance_freeze(acceptance_manifest)
        execution_after, _ = verify_execution_freeze(EXECUTION_FREEZE)
        candidate_after = candidate_after and (
            _sha256(candidate_manifest)
            == thresholds["candidate_freeze_manifest_sha256"]
        )
        acceptance_after = acceptance_after and (
            _sha256(acceptance_manifest)
            == thresholds["acceptance_freeze_manifest_sha256"]
        )
        report_integrity = (
            report["candidate"] == thresholds["candidate"]
            and report["metadata"]["candidate_freeze_sha256"]
            == thresholds["candidate_freeze_manifest_sha256"]
            and report["metadata"]["acceptance_freeze_sha256"]
            == thresholds["acceptance_freeze_manifest_sha256"]
            and report["metadata"]["dataset_sha256"]
            == thresholds["acceptance_dataset_sha256"]
            and report["metadata"]["thresholds_sha256"] == THRESHOLDS_SHA256
            and report["metadata"]["retrieval_enabled"] is False
            and report["metadata"]["database_lookup_enabled"] is False
            and report["metadata"]["model_inference_enabled"] is False
        )
        result = qualify(
            thresholds,
            report,
            candidate_freeze_before=candidate_before,
            candidate_freeze_after=candidate_after,
            acceptance_freeze_before=acceptance_before,
            acceptance_freeze_after=acceptance_after,
            production_imports_candidate=production_imports_candidate(),
            report_integrity=report_integrity,
            execution_freeze_before=execution_before,
            execution_freeze_after=execution_after,
        )
        _atomic_json(FINAL_OUTPUT_DIR / "qualification.json", result)
        _atomic_text(
            FINAL_OUTPUT_DIR / "summary.md", _human_summary(result, report)
        )
        ledger.update(status="completed", finished_at=datetime.now(UTC).isoformat())
        _atomic_json(ledger_path, ledger)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        ledger.update(
            status="failed",
            finished_at=datetime.now(UTC).isoformat(),
            error=f"{type(exc).__name__}: {exc}",
        )
        _atomic_json(ledger_path, ledger)
        raise


if __name__ == "__main__":
    main()
