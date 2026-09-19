"""Complete abbreviated ``heading_path`` values into full parser paths.

The human review recorded only the section suffix (for example
``["3.7 第二道防线：证据门禁"]``) while the ingestion parser produces the full
path (``["第 3 课：混合检索与可信 RAG 回答", "一、教案正文", "3.7 第二道防线：证据门禁"]``).
The runner compares paths exactly, so an abbreviated path silently degrades to
``keyword_fallback`` and the row drops out of formal Recall/MRR.

This script resolves each path against the real document outline and rewrites
it in full.  It does **not** invent paths: a suffix that does not match exactly
one real path is reported as ambiguous and left untouched, because guessing
would corrupt a human label.

Usage:
    python -m uv run python scripts/fix_label_paths.py [--apply]
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

DATASET = _REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl"
DOCS_DIR = _REPO_ROOT / "docs" / "learning"


def load_outline() -> dict[str, list[tuple[str, ...]]]:
    from agent_mentor.rag.documents import DocumentParser

    parser = DocumentParser(max_pdf_pages=200)
    outline: dict[str, list[tuple[str, ...]]] = {}
    for path in sorted(DOCS_DIR.glob("*.md")):
        seen: list[tuple[str, ...]] = []
        for section in parser.parse(path.name, path.read_bytes()):
            heading = tuple(section.heading_path)
            if heading and heading not in seen:
                seen.append(heading)
        outline[path.stem] = seen
    return outline


def resolve(
    document: str, suffix: tuple[str, ...], outline: dict[str, list[tuple[str, ...]]]
) -> tuple[tuple[str, ...] | None, str]:
    """Return the unique full path ending with ``suffix`` for ``document``."""
    candidates = [
        path for path in outline.get(document, []) if path[len(path) - len(suffix) :] == suffix
    ]
    if not candidates:
        return None, "no matching path"
    if len(candidates) > 1:
        return None, f"ambiguous: {len(candidates)} candidates"
    return candidates[0], "ok"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Rewrite the dataset in place.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()

    outline = load_outline()
    lines = args.dataset.read_text(encoding="utf-8").splitlines()

    changes: list[str] = []
    problems: list[str] = []
    output: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            output.append(line)
            continue
        row = json.loads(stripped)
        for source in row.get("relevant_sources", []):
            document = str(source["document_logical_name"])
            suffix = tuple(str(part) for part in source.get("heading_path", []))
            if not suffix:
                continue
            full, status = resolve(document, suffix, outline)
            if full is None:
                problems.append(f"{row['id']}: {' > '.join(suffix)} -> {status}")
                continue
            if list(full) != list(suffix):
                changes.append(f"{row['id']}: ['{' > '.join(suffix)}'] -> ['{' > '.join(full)}']")
                source["heading_path"] = list(full)
        output.append(json.dumps(row, ensure_ascii=False))

    print(f"paths completed: {len(changes)}")
    for item in changes:
        print(f"  {item}")
    if problems:
        print(f"\nUNRESOLVED ({len(problems)}):")
        for item in problems:
            print(f"  {item}")

    if args.apply:
        args.dataset.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
        print(f"\nwritten: {args.dataset}")
    else:
        print("\n(dry run; pass --apply to write)")

    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
