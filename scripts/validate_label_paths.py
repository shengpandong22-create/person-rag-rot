"""Check that every dataset heading_path actually resolves against the docs.

The runner resolves labels at run time via ``document_logical_name`` +
``heading_path``.  If a path in the dataset does not exist in the parsed
documents, the row silently degrades to ``keyword_fallback`` and drops out of
formal Recall/MRR — the evaluation still "passes" while measuring nothing.

This script fails loudly instead.  It reads only files; it never touches the
knowledge base, so it can run before any database is available.

Usage:
    python -m uv run python scripts/validate_label_paths.py [dataset.jsonl]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from evals.schema import Answerability, load_dataset  # noqa: E402

DOCS_DIR = _REPO_ROOT / "docs" / "learning"
DATASETS = (
    _REPO_ROOT / "evals" / "datasets" / "retrieval_development_v1.jsonl",
    _REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl",
    _REPO_ROOT / "evals" / "datasets" / "retrieval_validation_v1.jsonl",
    _REPO_ROOT / "evals" / "datasets" / "retrieval_holdout_v1.jsonl",
)


def load_document_paths(docs_dir: Path) -> dict[str, set[tuple[str, ...]]]:
    """Map document name to the exact heading_path tuples the parser produces."""
    from agent_mentor.rag.documents import DocumentParser

    parser = DocumentParser(max_pdf_pages=200)
    index: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for path in sorted(docs_dir.glob("*.md")):
        for section in parser.parse(path.name, path.read_bytes()):
            if section.heading_path:
                index[path.stem].add(tuple(section.heading_path))
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", type=Path, default=None)
    args = parser.parse_args()
    datasets = args.datasets or list(DATASETS)

    document_paths = load_document_paths(DOCS_DIR)
    print(f"documents indexed: {len(document_paths)}")
    print(f"distinct heading paths: {sum(len(v) for v in document_paths.values())}")

    total_missing = 0
    for dataset in datasets:
        if not dataset.exists():
            print(f"\n## {dataset.name}\n- SKIP: file not present")
            continue
        result = load_dataset(dataset, require_graded=False)
        graded = [
            case
            for case in result.cases
            if case.relevant_sources and case.answerability is not Answerability.NONE
        ]
        missing: list[str] = []
        checked = 0
        for case in graded:
            for source in case.relevant_sources:
                checked += 1
                known = document_paths.get(source.document_logical_name)
                if known is None:
                    missing.append(
                        f"{case.case_id}: unknown document {source.document_logical_name!r}"
                    )
                    continue
                if source.heading_path not in known:
                    rendered = " > ".join(source.heading_path)
                    missing.append(f"{case.case_id}: path not found -> {rendered}")
        print(f"\n## {dataset.name}")
        print(f"- cases: {len(result.cases)}")
        print(f"- graded rows with sources: {len(graded)}")
        print(f"- source references checked: {checked}")
        if missing:
            total_missing += len(missing)
            print(f"- UNRESOLVED ({len(missing)}):")
            for item in missing:
                print(f"  - {item}")
        else:
            print("- UNRESOLVED: none")

    print(f"\ntotal unresolved label references: {total_missing}")
    if total_missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
