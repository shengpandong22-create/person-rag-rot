"""Extract the heading outline of the learning documents.

Heading paths are produced by the **real ingestion parser**
(``agent_mentor.rag.documents.DocumentParser``), not by a reimplementation.
This matters because dataset labels store ``heading_path`` verbatim and the
runner resolves them against the live knowledge base; a path that differs by
one level would silently fail to resolve and would be reported as an
unresolved label rather than a wrong answer.

This script only reads files; it never touches the knowledge base.

Usage:
    python -m uv run python scripts/extract_headings.py [docs/learning] \
        [--json] [--output path.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from agent_mentor.rag.documents import DocumentParser  # noqa: E402

DEFAULT_DIR = _REPO_ROOT / "docs" / "learning"


@dataclass(frozen=True, slots=True)
class SectionOutline:
    heading_path: tuple[str, ...]
    block_type: str
    char_count: int
    excerpt: str


def collect_sections(directory: Path) -> dict[str, list[SectionOutline]]:
    """Parse every markdown file with the production parser."""
    parser = DocumentParser(max_pdf_pages=200)
    outlines: dict[str, list[SectionOutline]] = OrderedDict()
    for path in sorted(directory.glob("*.md")):
        sections = parser.parse(path.name, path.read_bytes())
        outlines[path.stem] = [
            SectionOutline(
                heading_path=tuple(section.heading_path),
                block_type=section.block_type,
                char_count=len(section.text),
                excerpt=_excerpt(section.text),
            )
            for section in sections
        ]
    return outlines


def _excerpt(text: str, limit: int = 90) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit]


def render_markdown(outlines: dict[str, list[SectionOutline]]) -> str:
    lines: list[str] = []
    for name, sections in outlines.items():
        lines.append(f"\n## {name}")
        lines.append(f"document_logical_name: {name}")
        lines.append(f"section_count: {len(sections)}")
        for index, section in enumerate(sections, start=1):
            path_text = " > ".join(section.heading_path) or "(no heading)"
            lines.append(
                f"{index}. [{section.block_type}|{section.char_count}c] {path_text}"
            )
            lines.append(f"   {section.excerpt}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write UTF-8 to this file instead of stdout (Windows console is GBK).",
    )
    args = parser.parse_args()

    if not args.directory.exists():
        raise SystemExit(f"directory not found: {args.directory}")
    outlines = collect_sections(args.directory)
    if not outlines:
        raise SystemExit(f"no markdown files in {args.directory}")

    if args.json:
        payload = {
            name: [
                {
                    "heading_path": list(section.heading_path),
                    "block_type": section.block_type,
                    "char_count": section.char_count,
                    "excerpt": section.excerpt,
                }
                for section in sections
            ]
            for name, sections in outlines.items()
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        rendered = render_markdown(outlines)

    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"written: {args.output}")
        return
    print(rendered)


if __name__ == "__main__":
    main()
