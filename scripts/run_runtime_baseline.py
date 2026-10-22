"""Run the intentionally small, sequential AgentMentor runtime baseline."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.provenance import collect_git_state  # noqa: E402
from evals.runtime_baseline import (  # noqa: E402
    RuntimeMeasurement,
    build_runtime_report,
    write_runtime_report,
)


def _load_cases(path: Path) -> list[dict[str, str]]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not cases or any(not row.get("id") or not row.get("question") for row in cases):
        raise ValueError("dataset must contain non-empty id and question fields")
    return [{"id": str(row["id"]), "question": str(row["question"])} for row in cases]


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _runtime(client: httpx.Client, base_url: str, expected_llm_enabled: bool) -> dict[str, Any]:
    response = client.get(f"{base_url}/health/runtime")
    response.raise_for_status()
    runtime = response.json()
    if runtime.get("llm_enabled") is not expected_llm_enabled:
        raise RuntimeError(
            f"{base_url} llm_enabled={runtime.get('llm_enabled')!r}; "
            f"expected {expected_llm_enabled!r}"
        )
    return runtime


def _measure(
    client: httpx.Client,
    *,
    base_url: str,
    mode: str,
    phase: str,
    knowledge_base_id: UUID,
    case: dict[str, str],
    iteration: int,
) -> RuntimeMeasurement:
    endpoint = "retrieve" if phase == "retrieval" else "ask"
    payload: dict[str, object] = {"query": case["question"], "top_k": 6, "candidate_k": 20}
    if phase == "end_to_end":
        payload = {
            "question": case["question"],
            "top_k": 6,
            "candidate_k": 20,
            "allow_model_knowledge": False,
        }
    started = time.perf_counter()
    try:
        response = client.post(
            f"{base_url}/api/v1/knowledge-bases/{knowledge_base_id}/{endpoint}", json=payload
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        content_type = response.headers.get("content-type", "")
        body = response.json() if content_type.startswith("application/json") else {}
        if response.is_error:
            return RuntimeMeasurement(
                mode, phase, case["id"], iteration, elapsed_ms, False, response.status_code,
                error=str(body),
            )
        return RuntimeMeasurement(
            mode,
            phase,
            case["id"],
            iteration,
            elapsed_ms,
            True,
            response.status_code,
            generation_mode=body.get("generation_mode") if isinstance(body, dict) else None,
            fallback_reason=body.get("fallback_reason") if isinstance(body, dict) else None,
        )
    except (httpx.HTTPError, ValueError) as error:
        return RuntimeMeasurement(
            mode,
            phase,
            case["id"],
            iteration,
            round((time.perf_counter() - started) * 1000, 3),
            False,
            None,
            error=f"{type(error).__name__}: {error}",
        )


def run_baseline(
    *,
    fallback_base_url: str,
    llm_base_url: str,
    knowledge_base_id: UUID,
    dataset_path: Path,
    knowledge_fixture_path: Path,
    output_dir: Path,
    repetitions: int,
    warmups: int,
) -> dict[str, object]:
    if repetitions < 1 or warmups < 0:
        raise ValueError("repetitions must be positive and warmups cannot be negative")
    cases = _load_cases(dataset_path)
    measurements: list[RuntimeMeasurement] = []
    timeout = httpx.Timeout(180.0)
    with httpx.Client(timeout=timeout) as client:
        runtimes = {
            "fallback": _runtime(client, fallback_base_url, expected_llm_enabled=False),
            "llm": _runtime(client, llm_base_url, expected_llm_enabled=True),
        }
        baseline = runtimes["fallback"]
        for name, runtime in runtimes.items():
            for key in ("embedding_provider", "embedding_model", "embedding_dimension"):
                if runtime.get(key) != baseline.get(key):
                    raise RuntimeError(f"runtime mismatch for {key}: fallback != {name}")
        for mode, base_url in (("fallback", fallback_base_url), ("llm", llm_base_url)):
            for phase in ("retrieval", "end_to_end"):
                for warmup in range(warmups):
                    _measure(
                        client,
                        base_url=base_url,
                        mode=mode,
                        phase=phase,
                        knowledge_base_id=knowledge_base_id,
                        case=cases[warmup % len(cases)],
                        iteration=0,
                    )
                for iteration in range(1, repetitions + 1):
                    for case in cases:
                        measurements.append(
                            _measure(
                                client, base_url=base_url, mode=mode, phase=phase,
                                knowledge_base_id=knowledge_base_id, case=case, iteration=iteration,
                            )
                        )
    report = build_runtime_report(
        metadata={
            "generated_at": datetime.now(UTC).isoformat(),
            **collect_git_state().to_json(),
            "dataset": str(dataset_path),
            "dataset_sha256": _sha256(dataset_path),
            "knowledge_fixture": str(knowledge_fixture_path),
            "knowledge_fixture_sha256": _sha256(knowledge_fixture_path),
            "knowledge_base_id": str(knowledge_base_id),
            "repetitions": repetitions,
            "warmups": warmups,
            "runtime_modes": runtimes,
            "machine": {"platform": platform.platform(), "python": platform.python_version()},
        },
        measurements=measurements,
    )
    write_runtime_report(report, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fallback-base-url", required=True)
    parser.add_argument("--llm-base-url", required=True)
    parser.add_argument("--knowledge-base-id", type=UUID, required=True)
    parser.add_argument(
        "--dataset", type=Path, default=Path("evals/datasets/runtime_baseline_v1.jsonl")
    )
    parser.add_argument(
        "--knowledge-fixture",
        type=Path,
        default=Path("evals/fixtures/runtime_baseline_knowledge_v1.md"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=4)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--allow-persistent-chat-writes", action="store_true")
    args = parser.parse_args()
    if not args.allow_persistent_chat_writes:
        parser.error(
            "refusing to call /ask without --allow-persistent-chat-writes; "
            "use a dedicated benchmark KB"
        )
    report = run_baseline(
        fallback_base_url=args.fallback_base_url.rstrip("/"),
        llm_base_url=args.llm_base_url.rstrip("/"),
        knowledge_base_id=args.knowledge_base_id,
        dataset_path=args.dataset,
        knowledge_fixture_path=args.knowledge_fixture,
        output_dir=args.output_dir,
        repetitions=args.repetitions,
        warmups=args.warmups,
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
