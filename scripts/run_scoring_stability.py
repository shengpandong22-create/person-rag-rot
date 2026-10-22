from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.scoring_stability import run_scoring_stability  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the fixed five-run scoring stability observation."
    )
    parser.add_argument(
        "--dataset", type=Path, default=Path("evals/datasets/evaluation_discrimination_v1.jsonl")
    )
    parser.add_argument("--case-id", default="disc-evaluation-high")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    report = asyncio.run(
        run_scoring_stability(
            dataset_path=args.dataset,
            case_id=args.case_id,
            output_dir=args.output_dir,
            runs=args.runs,
        )
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
