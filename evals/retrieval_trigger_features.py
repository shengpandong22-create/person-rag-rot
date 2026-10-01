"""Offline structural features for monotonic heading-supplemental triggers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_CLAUSE_SPLIT = re.compile(r"[，,；;？?。]|(?:以及|并且|同时|再|而)")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*|[\u4e00-\u9fff]{2,8}")
_STOP = {
    "什么",
    "为什么",
    "如何",
    "是否",
    "哪个",
    "哪些",
    "多少",
    "当前",
    "默认",
    "具体",
    "系统",
    "资料",
    "可以",
    "已经",
}


def structural_features(case: dict[str, Any]) -> dict[str, Any]:
    question = str(case["question"])
    core_terms = _terms(question)
    primary = list(case.get("top_chunks") or [])
    supplemental = list(case.get("supplemental_chunks") or [])
    primary_heading = " ".join(_heading_text(item) for item in primary).casefold()
    supplemental_heading = " ".join(_heading_text(item) for item in supplemental).casefold()
    primary_covered = tuple(term for term in core_terms if term.casefold() in primary_heading)
    supplemental_covered = tuple(
        term for term in core_terms if term.casefold() in supplemental_heading
    )
    newly_covered = tuple(term for term in supplemental_covered if term not in primary_covered)
    primary_documents = {
        str(item.get("document_logical_name") or item.get("document_title") or "")
        for item in primary
    }
    primary_paths = {tuple(item.get("heading_path") or ()) for item in primary}
    same_document_new_heading = any(
        str(item.get("document_logical_name") or item.get("document_title") or "")
        in primary_documents
        and tuple(item.get("heading_path") or ()) not in primary_paths
        for item in supplemental
    )
    clauses = tuple(part.strip() for part in _CLAUSE_SPLIT.split(question) if part.strip())
    primary_clause_coverage = tuple(
        _coverage_ratio(_terms(clause), primary_heading) for clause in clauses
    )
    supplemental_clause_gain = tuple(
        max(0.0, _coverage_ratio(_terms(clause), supplemental_heading) - primary_ratio)
        for clause, primary_ratio in zip(clauses, primary_clause_coverage, strict=True)
    )
    return {
        "core_terms": list(core_terms),
        "primary_covered_terms": list(primary_covered),
        "primary_missing_terms": [term for term in core_terms if term not in primary_covered],
        "supplemental_covered_terms": list(supplemental_covered),
        "supplemental_new_terms": list(newly_covered),
        "same_document_new_heading": same_document_new_heading,
        "clause_count": len(clauses),
        "primary_clause_coverage": list(primary_clause_coverage),
        "supplemental_clause_gain": list(supplemental_clause_gain),
        "primary_heading_coverage": _coverage_ratio(core_terms, primary_heading),
        "supplemental_novelty_ratio": round(len(newly_covered) / len(core_terms), 4)
        if core_terms
        else 0.0,
    }


def structural_trigger(features: dict[str, Any]) -> bool:
    """Predeclared label-free trigger; thresholds are frozen before cross-fixture evaluation."""
    return (
        float(features["primary_heading_coverage"]) < 0.20
        and bool(features["supplemental_new_terms"])
        and bool(features["same_document_new_heading"])
    )


def build_feature_report(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = []
    for case in report["cases"]:
        features = structural_features(case)
        rows.append(
            {
                "id": case["id"],
                "answerability": case["answerability"],
                "primary_hit": case.get("first_relevant_rank") is not None,
                "supplemental_hit_rank": case.get("first_supplemental_rank"),
                "structural_trigger": structural_trigger(features),
                "features": features,
            }
        )
    return {
        "source_report": str(report_path),
        "dataset": report["dataset"],
        "dataset_sha256": report["metadata"]["dataset_sha256"],
        "case_count": len(rows),
        "cases": rows,
    }


def _terms(text: str) -> tuple[str, ...]:
    terms: list[str] = []
    for token in _TOKEN.findall(text):
        if token in _STOP:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
        else:
            terms.append(token.casefold())
    return tuple(dict.fromkeys(term for term in terms if term not in _STOP))


def _heading_text(item: dict[str, Any]) -> str:
    return " ".join(str(part) for part in item.get("heading_path") or ())


def _coverage_ratio(terms: tuple[str, ...], text: str) -> float:
    return round(sum(term.casefold() in text for term in terms) / len(terms), 4) if terms else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for report_path in args.reports:
        payload = build_feature_report(report_path)
        output = args.output_dir / f"{report_path.parent.name}.json"
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
