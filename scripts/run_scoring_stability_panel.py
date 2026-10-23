"""Run the frozen three-band, five-runs-each scoring stability observation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.scoring_stability import run_scoring_stability  # noqa: E402

CASE_IDS = (
    "disc-rag-boundary-low",
    "disc-rag-boundary-mid",
    "disc-rag-boundary-high",
)


async def run_panel(dataset: Path, output_dir: Path) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for case_id in CASE_IDS:
        report = await run_scoring_stability(
            dataset_path=dataset,
            case_id=case_id,
            output_dir=output_dir / case_id,
            runs=5,
        )
        cases.append(
            {
                "case_id": case_id,
                "metadata": report["metadata"],
                "metrics": report["metrics"],
            }
        )
    result = {
        "protocol": "scoring-stability-panel-v1",
        "executed_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "total_model_runs": len(cases) * 5,
        "cases": cases,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "panel.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=Path("evals/datasets/evaluation_discrimination_v1.jsonl")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(run_panel(args.dataset, args.output_dir))
    print(
        json.dumps(
            {"case_count": report["case_count"], "total_model_runs": report["total_model_runs"]}
        )
    )


if __name__ == "__main__":
    main()
