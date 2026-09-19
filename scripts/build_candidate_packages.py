"""Generate candidate evidence packages for human labelling.

Produces two artefacts under ``evals/review/``:

* ``candidates_<dataset>.jsonl`` — machine-readable review queue
* ``candidates_<dataset>.md``   — same content for human reading

Nothing produced here is a label.  ``human_verified`` is always ``false`` and
``suggested_by`` is always ``model_suggested``; a reviewer must set the final
``relevant_sources`` by hand.

Usage:
    python -m uv run python scripts/build_candidate_packages.py \
        [evals/datasets/retrieval_regression_v1.jsonl] [--limit 5]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from evals.candidates import (  # noqa: E402
    CaseCandidatePackage,
    build_packages,
    load_sections_from_directory,
)
from evals.schema import load_dataset  # noqa: E402

DEFAULT_DATASET = _REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl"
DOCS_DIR = _REPO_ROOT / "docs" / "learning"
REVIEW_DIR = _REPO_ROOT / "evals" / "review"


def render_markdown(packages: tuple[CaseCandidatePackage, ...], *, source: str) -> str:
    lines = [
        "# Candidate Evidence Packages — HUMAN REVIEW REQUIRED",
        "",
        f"- source_dataset: `{source}`",
        f"- packages: {len(packages)}",
        "- every candidate below is a **model suggestion**, NOT a label.",
        "- `human_verified` is false for all rows. A reviewer must select the",
        "  correct source(s) and record them as `relevant_sources` manually.",
        "- labels are located by `document_logical_name > heading_path` and carry a",
        "  `content_fingerprint`; no chunk UUID is used as a long-term label.",
        "",
        "## Review checklist per case",
        "",
        "1. Does any candidate actually answer the question? If none does, decide",
        "   between `partial` / `none` instead of forcing a label.",
        "2. Is the `heading_path` the section that would be cited, or merely a",
        "   nearby section that mentions the right words?",
        "3. Are the `suggested_answer_points` supported by the excerpt, or do they",
        "   need editing before they can serve as a grading rubric?",
        "4. Record the final `relevant_sources` and set `label_origin=human`.",
        "",
    ]
    for package in packages:
        lines.append(f"## {package.case_id}")
        lines.append("")
        lines.append(f"- question: {package.question}")
        lines.append(f"- declared answerability: {package.answerability}")
        lines.append(f"- diagnostic_keywords: {list(package.diagnostic_keywords)}")
        for note in package.notes:
            lines.append(f"- note: {note}")
        lines.append("")
        if not package.candidates:
            lines.append("**No candidates above threshold.** Manual authoring required.")
            lines.append("")
            continue
        for index, candidate in enumerate(package.candidates, start=1):
            path_text = " > ".join(candidate.heading_path)
            lines.append(f"### candidate {index} (score {candidate.score:.2f})")
            lines.append("")
            lines.append(f"- document_logical_name: `{candidate.document_logical_name}`")
            lines.append(f"- heading_path: `{path_text}`")
            lines.append(f"- content_fingerprint: `{candidate.content_fingerprint[:16]}...`")
            lines.append("- evidence_excerpt:")
            lines.append("")
            lines.append("  ```")
            for excerpt_line in candidate.evidence_excerpt.splitlines()[:12]:
                lines.append(f"  {excerpt_line}")
            lines.append("  ```")
            lines.append("")
            lines.append("- suggested_answer_points (verify before use):")
            for point in candidate.suggested_answer_points:
                lines.append(f"  - {point}")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--docs", type=Path, default=DOCS_DIR)
    parser.add_argument("--limit", type=int, default=5, help="Candidates per case.")
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(f"dataset not found: {args.dataset}")
    if not args.docs.is_dir():
        raise SystemExit(f"documents directory not found: {args.docs}")

    result = load_dataset(args.dataset, require_graded=False)
    sections = load_sections_from_directory(args.docs)
    packages = build_packages(result.cases, sections, limit=args.limit)

    args.review_dir.mkdir(parents=True, exist_ok=True)
    stem = args.dataset.stem
    jsonl_path = args.review_dir / f"candidates_{stem}.jsonl"
    markdown_path = args.review_dir / f"candidates_{stem}.md"

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for package in packages:
            handle.write(json.dumps(package.to_json(), ensure_ascii=False) + "\n")
    markdown_path.write_text(
        render_markdown(packages, source=str(args.dataset)) + "\n", encoding="utf-8"
    )

    with_candidates = sum(1 for package in packages if package.candidates)
    print(f"sections_parsed: {len(sections)}")
    print(f"packages: {len(packages)} (with candidates: {with_candidates})")
    print(f"written: {jsonl_path}")
    print(f"written: {markdown_path}")
    print("REMINDER: these are suggestions only; no row is human_verified.")


if __name__ == "__main__":
    main()
