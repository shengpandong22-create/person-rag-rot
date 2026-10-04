"""Audit V3 acceptance annotations without importing or running the candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROLES = {"exact", "derived_value", "range", "upper_bound", "lower_bound", "sequence"}
SEMANTICS = {
    "generic",
    "ratio",
    "score",
    "count",
    "duration",
    "rate",
    "accuracy",
    "coverage",
    "weight",
}
SPAN_TYPES = {"sentence_span", "table_row", "code_statement", "bounded_multi_span"}
NEGATIVE_TYPES = {
    "relation_role",
    "value_semantic",
    "subject_predicate",
    "unit_binding",
    "provenance_structure",
    "missing_value_false_premise",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(value)
    return rows


def normalized_question(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.casefold())


def normalized_span_hash(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _existing_labels(paths: Iterable[Path]) -> tuple[set[str], set[tuple[str, str]]]:
    questions: set[str] = set()
    targets: set[tuple[str, str]] = set()
    for path in paths:
        for row in load_jsonl(path):
            question = row.get("question")
            if isinstance(question, str):
                questions.add(normalized_question(question))
            relation = row.get("requested_relation") or row.get("relation")
            values = row.get("expected_values")
            if isinstance(relation, str) and isinstance(values, list):
                targets.add((normalized_question(relation), json.dumps(values, ensure_ascii=False)))
            for demand in row.get("demands", []):
                for value_set in demand.get("accepted_value_sets", []):
                    targets.add(
                        (
                            normalized_question(demand["requested_relation"]),
                            json.dumps(value_set, ensure_ascii=False),
                        )
                    )
    return questions, targets


def audit(
    rows: list[dict[str, Any]],
    plan: dict[str, Any],
    *,
    existing_paths: Iterable[Path] = (),
    source_root: Path = Path("docs/learning"),
) -> dict[str, Any]:
    errors: list[str] = []
    ids: set[str] = set()
    questions: set[str] = set()
    targets: set[tuple[str, str]] = set()
    existing_questions, existing_targets = _existing_labels(existing_paths)
    positive_spans: Counter[str] = Counter()
    positive_roles: Counter[str] = Counter()
    negative_types: Counter[str] = Counter()
    documents: Counter[str] = Counter()
    positive_count = 0
    negative_count = 0
    multi_demand_count = 0
    explicit_unit_count = 0
    unitless_count = 0
    conversion_count = 0
    multi_value_count = 0
    numeric_distractor_count = 0
    pair_members: Counter[str] = Counter()

    for index, row in enumerate(rows, start=1):
        prefix = f"row {index}"
        row_id = row.get("id")
        if not isinstance(row_id, str) or not re.fullmatch(r"rva3-\d{3}", row_id):
            errors.append(f"{prefix}: invalid id")
        elif row_id in ids:
            errors.append(f"{prefix}: duplicate id {row_id}")
        else:
            ids.add(row_id)
        if row.get("split") != "acceptance" or row.get("label_origin") != "human":
            errors.append(f"{prefix}: split/label_origin must be acceptance/human")
        question = row.get("question")
        if not isinstance(question, str) or not question.strip():
            errors.append(f"{prefix}: missing question")
        else:
            normalized = normalized_question(question)
            if normalized in questions or normalized in existing_questions:
                errors.append(f"{prefix}: question overlap")
            questions.add(normalized)

        demands = row.get("demands")
        evidence = row.get("evidence")
        if not isinstance(demands, list) or not demands:
            errors.append(f"{prefix}: demands must be non-empty")
            continue
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}: evidence must be non-empty")
            continue
        if len(demands) > 1:
            multi_demand_count += 1
        positive = row.get("answerability") == "full"
        if positive:
            positive_count += 1
            if not all(demand.get("expected_binding") is True for demand in demands):
                errors.append(f"{prefix}: full row contains unsupported demand")
            role = row.get("primary_relation_role")
            span_type = row.get("primary_span_type")
            positive_roles[str(role)] += 1
            positive_spans[str(span_type)] += 1
            if role != demands[0].get("relation_role"):
                errors.append(f"{prefix}: primary role does not match first demand")
            if span_type != evidence[0].get("span_type"):
                errors.append(f"{prefix}: primary span does not match first evidence")
            document = evidence[0].get("document_logical_name")
            if isinstance(document, str):
                documents[document] += 1
        elif row.get("answerability") == "none":
            negative_count += 1
            confusion = row.get("confusion_type")
            negative_types[str(confusion)] += 1
            if confusion not in NEGATIVE_TYPES:
                errors.append(f"{prefix}: invalid negative confusion type")
            if not row.get("negative_reason"):
                errors.append(f"{prefix}: negative_reason required")
            if any(re.search(r"\d", item.get("span_text", "")) for item in evidence):
                numeric_distractor_count += 1
        else:
            errors.append(f"{prefix}: answerability must be full or none")

        pair_id = row.get("pair_id")
        if pair_id is not None:
            pair_members[str(pair_id)] += 1
        tags = set(row.get("tags", []))
        if "unit_alias_or_conversion" in tags:
            conversion_count += 1
        for demand in demands:
            role = demand.get("relation_role")
            semantic = demand.get("value_semantic")
            expected_binding = demand.get("expected_binding")
            value_sets = demand.get("accepted_value_sets")
            if role not in ROLES or semantic not in SEMANTICS:
                errors.append(f"{prefix}: invalid role or value semantic")
            if demand.get("modality") not in {"fact", "guarantee"}:
                errors.append(f"{prefix}: invalid modality")
            if not isinstance(value_sets, list):
                errors.append(f"{prefix}: accepted_value_sets must be a list")
                continue
            if expected_binding is True and not value_sets:
                errors.append(f"{prefix}: positive demand needs accepted values")
            if expected_binding is False and value_sets:
                errors.append(f"{prefix}: negative demand must not accept values")
            if expected_binding is True:
                canonical_unit = demand.get("canonical_unit")
                if canonical_unit is None:
                    unitless_count += 1
                else:
                    explicit_unit_count += 1
                if value_sets and len(value_sets[0]) > 1:
                    multi_value_count += 1
            for value_set in value_sets:
                target = (
                    normalized_question(str(demand.get("requested_relation", ""))),
                    json.dumps(value_set, ensure_ascii=False),
                )
                if target in targets or target in existing_targets:
                    errors.append(f"{prefix}: relation/value target overlap")
                targets.add(target)

        evidence_ids = {item.get("evidence_id") for item in evidence}
        if None in evidence_ids or len(evidence_ids) != len(evidence):
            errors.append(f"{prefix}: evidence ids missing or duplicated")
        for item in evidence:
            span_text = item.get("span_text")
            span_type = item.get("span_type")
            if span_type not in SPAN_TYPES or not isinstance(span_text, str):
                errors.append(f"{prefix}: invalid evidence span")
                continue
            if normalized_span_hash(span_text) != item.get("span_sha256"):
                errors.append(f"{prefix}: evidence span hash mismatch")
            document = item.get("document_logical_name")
            if not isinstance(document, str):
                errors.append(f"{prefix}: missing document logical name")
                continue
            source = source_root / f"{document}.md"
            if not source.is_file():
                errors.append(f"{prefix}: source document missing")
                continue
            if file_sha256(source) != item.get("source_content_hash"):
                errors.append(f"{prefix}: source content hash mismatch")
            normalized_source = source.read_text(encoding="utf-8").replace("\r\n", "\n")
            normalized_span = span_text.replace("\r\n", "\n").replace("\r", "\n")
            if normalized_span not in normalized_source:
                errors.append(f"{prefix}: evidence span not found in source")
        annotation = row.get("annotation", {})
        if annotation.get("review_state") != plan["required_review_state"]:
            errors.append(f"{prefix}: review is not agreed")
        if not annotation.get("author") or not annotation.get("reviewer"):
            errors.append(f"{prefix}: author and reviewer required")
        if annotation.get("author") == annotation.get("reviewer"):
            errors.append(f"{prefix}: author and reviewer must differ")

    checks = {
        "total_rows": len(rows) == plan["total_rows"],
        "positive_rows": positive_count == plan["positive_rows"],
        "hard_negative_rows": negative_count == plan["hard_negative_rows"],
        "multi_demand_rows": multi_demand_count == plan["multi_demand_rows"],
        "positive_span_distribution": dict(positive_spans)
        == plan["positive_span_distribution"],
        "positive_role_distribution": dict(positive_roles)
        == plan["positive_role_distribution"],
        "hard_negative_distribution": dict(negative_types)
        == plan["hard_negative_distribution"],
        "documents_represented": len(documents) >= plan["minimums"]["documents_represented"],
        "positive_rows_per_document": max(documents.values(), default=0)
        <= plan["maximums"]["positive_rows_per_document"],
        "explicit_unit_positives": explicit_unit_count
        >= plan["minimums"]["explicit_unit_positives"],
        "unitless_positives": unitless_count >= plan["minimums"]["unitless_positives"],
        "unit_alias_or_conversion_positives": conversion_count
        >= plan["minimums"]["unit_alias_or_conversion_positives"],
        "multi_value_positives": multi_value_count
        >= plan["minimums"]["multi_value_positives"],
        "numeric_distractor_negatives": numeric_distractor_count
        >= plan["minimums"]["numeric_distractor_negatives"],
        "paired_hard_negatives": sum(count >= 2 for count in pair_members.values())
        >= plan["minimums"]["paired_hard_negatives"],
        "row_validation": not errors,
    }
    return {
        "schema_version": plan["schema_version"],
        "audit_passed": all(checks.values()),
        "checks": checks,
        "counts": {
            "total": len(rows),
            "positive": positive_count,
            "hard_negative": negative_count,
            "multi_demand": multi_demand_count,
            "positive_spans": dict(positive_spans),
            "positive_roles": dict(positive_roles),
            "hard_negative_types": dict(negative_types),
            "documents": dict(documents),
        },
        "errors": errors,
        "candidate_executed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--compare", action="append", type=Path, default=[])
    parser.add_argument("--source-root", type=Path, default=Path("docs/learning"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(
        load_jsonl(args.dataset),
        json.loads(args.plan.read_text(encoding="utf-8")),
        existing_paths=args.compare,
        source_root=args.source_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["audit_passed"] else 1)


if __name__ == "__main__":
    main()
