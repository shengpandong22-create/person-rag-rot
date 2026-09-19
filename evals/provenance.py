"""Reproducibility context attached to every evaluation report.

An evaluation number is only meaningful together with the code, data and
configuration that produced it.  The previous report in
``evals/reports/retrieval_current`` recorded parameters but not the commit, so
after the retriever changed it was impossible to tell which implementation the
0.6538 Recall@3 actually described.  That ambiguity is the reason the current
retrieval quality is unknown rather than merely poor.

This module collects the missing pieces:

* ``git_commit`` / ``git_dirty`` — which code produced the number
* ``dataset_sha256`` — which labels were used
* ``holdout`` — whether the acceptance set was still frozen at run time

``git`` is invoked with a short timeout and every field degrades to ``unknown``
rather than raising, because an evaluation must still be able to run outside a
git checkout (for example inside the API container).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.freeze import FREEZE_RECORD, HOLDOUT_DATASET, check_freeze, file_sha256

GIT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class GitState:
    commit: str
    short_commit: str
    dirty: bool
    branch: str

    def to_json(self) -> dict[str, Any]:
        return {
            "git_commit": self.commit,
            "git_short_commit": self.short_commit,
            "git_dirty": self.dirty,
            "git_branch": self.branch,
        }


def _run_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def collect_git_state() -> GitState:
    """Return the commit under evaluation, degrading to ``unknown`` off-repo."""
    commit = _run_git("rev-parse", "HEAD") or "unknown"
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    status = _run_git("status", "--porcelain")
    return GitState(
        commit=commit,
        short_commit=commit[:12] if commit != "unknown" else "unknown",
        dirty=bool(status) if status is not None else False,
        branch=branch,
    )


def collect_holdout_state(
    dataset: Path = HOLDOUT_DATASET,
    record: Path = FREEZE_RECORD,
) -> dict[str, Any]:
    """Report whether the frozen acceptance set was intact when the run started."""
    if not dataset.exists():
        return {"holdout_present": False, "holdout_intact": None, "holdout_detail": "absent"}
    ok, message = check_freeze(dataset, record)
    return {
        "holdout_present": True,
        "holdout_intact": ok,
        "holdout_sha256": file_sha256(dataset),
        "holdout_detail": message,
    }


def build_provenance(
    *,
    dataset_path: Path,
    holdout_dataset: Path = HOLDOUT_DATASET,
    holdout_record: Path = FREEZE_RECORD,
) -> dict[str, Any]:
    """Assemble the full reproducibility block for a report's metadata."""
    provenance: dict[str, Any] = {}
    provenance.update(collect_git_state().to_json())
    provenance["dataset_sha256"] = file_sha256(dataset_path) if dataset_path.exists() else "unknown"
    provenance.update(collect_holdout_state(holdout_dataset, holdout_record))
    return provenance
