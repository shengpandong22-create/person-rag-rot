"""Machine-readable qualification for the frozen V3 acceptance protocol."""

from __future__ import annotations

from typing import Any


def qualify(
    thresholds: dict[str, Any],
    report: dict[str, Any],
    *,
    candidate_freeze_before: bool,
    candidate_freeze_after: bool,
    acceptance_freeze_before: bool,
    acceptance_freeze_after: bool,
    production_imports_candidate: bool,
    report_integrity: bool,
    execution_freeze_before: bool,
    execution_freeze_after: bool,
) -> dict[str, Any]:
    gates = thresholds["hard_gates"]
    metrics = report["metrics"]
    counts = report["counts"]
    checks = {
        "demand_accuracy": metrics["demand_accuracy"] >= gates["demand_accuracy_min"],
        "positive_demand_recall": metrics["positive_demand_recall"]
        >= gates["positive_demand_recall_min"],
        "positive_row_all_demands_accuracy": metrics[
            "positive_row_all_demands_accuracy"
        ]
        >= gates["positive_row_all_demands_accuracy_min"],
        "negative_demand_rejection": metrics["negative_demand_rejection"]
        == gates["negative_demand_rejection_required"],
        "negative_row_rejection": metrics["negative_row_rejection"]
        == gates["negative_row_rejection_required"],
        "binding_precision": metrics["binding_precision"]
        >= gates["binding_precision_min"],
        "average_bindings_per_demand": metrics["average_bindings_per_demand"]
        <= gates["average_bindings_per_demand_max"],
        "max_bindings_per_demand": metrics["max_bindings_per_demand"]
        <= gates["max_bindings_per_demand_max"],
        "paired_discrimination": metrics["paired_discrimination"]
        >= gates["paired_discrimination_min"],
        "span_success_counts": _minimum_counts(
            metrics["span_success_counts"], gates["span_success_count_min"]
        ),
        "role_success_counts": _minimum_counts(
            metrics["role_success_counts"], gates["role_success_count_min"]
        ),
        "semantic_success_counts": _minimum_counts(
            metrics["semantic_success_counts"], gates["semantic_success_count_min"]
        ),
        "negative_category_rejection": _required_rates(
            metrics["negative_category_rejection"],
            gates["negative_category_rejection_required"],
        ),
        "evaluated_rows": counts["evaluated_rows"] == gates["evaluated_rows_required"],
        "evaluated_demands": counts["evaluated_demands"]
        == gates["evaluated_demands_required"],
        "unresolved_labels": counts["unresolved_labels"]
        == gates["unresolved_labels_required"],
        "case_errors": counts["case_errors"] == gates["case_errors_required"],
        "candidate_p95_ms": metrics["candidate_p95_ms"]
        <= gates["candidate_p95_ms_max"],
        "candidate_freeze_before_and_after": candidate_freeze_before
        and candidate_freeze_after,
        "acceptance_freeze_before_and_after": acceptance_freeze_before
        and acceptance_freeze_after,
        "production_isolation": production_imports_candidate
        == gates["production_imports_candidate_required"],
        "report_integrity": report_integrity,
        "execution_freeze_before_and_after": execution_freeze_before
        and execution_freeze_after,
    }
    return {
        "candidate": thresholds["candidate"],
        "accepted_for_production_integration_design": all(checks.values()),
        "checks": checks,
        "observed_metrics": metrics,
        "observed_counts": counts,
    }


def _minimum_counts(observed: dict[str, int], required: dict[str, int]) -> bool:
    return all(observed.get(name, 0) >= minimum for name, minimum in required.items())


def _required_rates(observed: dict[str, float], required: dict[str, float]) -> bool:
    return all(observed.get(name, 0.0) == rate for name, rate in required.items())
