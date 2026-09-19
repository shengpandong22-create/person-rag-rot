"""Run A/B/C/D label diagnostics over an existing retrieval report.

Usage:
    python -m uv run python scripts/run_label_diagnostics.py \
        [report.json] [--output path.md]

Reads a previously written ``retrieval_eval.json`` and re-scores its stored
``top_chunks`` under four matching rules, without touching the database, the
embedding model or the retrieval implementation.  The output is diagnostic
only; it never replaces human labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/run_label_diagnostics.py` from the repo root without
# requiring PYTHONPATH to be set.
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from evals.diagnostics import (  # noqa: E402
    chunks_carry_content,
    render_diagnostics,
    run_diagnostics,
)

DEFAULT_REPORT = Path("evals/reports/retrieval_current/retrieval_eval.json")
DEFAULT_OUTPUT = Path("evals/reports/diagnostics/label_diagnostics.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.report.exists():
        raise SystemExit(f"report not found: {args.report}")
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not cases:
        raise SystemExit(f"report has no cases: {args.report}")

    content_available = chunks_carry_content(cases)
    results = run_diagnostics(cases)
    markdown = render_diagnostics(
        results, source=str(args.report), content_available=content_available
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown + "\n", encoding="utf-8")

    print(f"source: {args.report}")
    print(f"chunk_content_available: {content_available}")
    for result in results:
        if not result.available:
            print(f"  {result.variant}: not computable from this report")
            continue
        print(
            f"  {result.variant}: hit@1={result.hit_at_1} hit@3={result.hit_at_3} "
            f"hit@6={result.hit_at_6} misses={len(result.misses)}"
        )
    print(f"written: {args.output}")


if __name__ == "__main__":
    sys.exit(main())
