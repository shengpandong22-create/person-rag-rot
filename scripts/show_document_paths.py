"""Print the exact heading_path tuples for one document.

Used to reconcile dataset labels with parser output.  Run this when
``validate_label_paths.py`` reports an unresolved path: it shows the verbatim
string the runner will compare against.

Usage:
    python -m uv run python scripts/show_document_paths.py "第 3 课：混合检索与可信 RAG 回答"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

DOCS_DIR = _REPO_ROOT / "docs" / "learning"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", help="document stem, or a substring of it")
    parser.add_argument("--filter", default=None, help="only show paths containing this text")
    args = parser.parse_args()

    from agent_mentor.rag.documents import DocumentParser

    doc_parser = DocumentParser(max_pdf_pages=200)
    matches = [path for path in sorted(DOCS_DIR.glob("*.md")) if args.document in path.stem]
    if not matches:
        raise SystemExit(f"no document matching {args.document!r}")

    for path in matches:
        print(f"\n## {path.stem}")
        for section in doc_parser.parse(path.name, path.read_bytes()):
            heading = tuple(section.heading_path)
            if not heading:
                continue
            rendered = " > ".join(heading)
            if args.filter and args.filter not in rendered:
                continue
            print(f"  {' > '.join(heading)}")
            print(f"      as JSON: {list(heading)}")


if __name__ == "__main__":
    main()
