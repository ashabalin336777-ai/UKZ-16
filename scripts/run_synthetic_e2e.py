#!/usr/bin/env python3
"""Run synthetic R1→R4 + bench readiness pipeline (no clinical claim)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    py = sys.executable
    _run([py, "scripts/generate_r2_synthetic_cohort.py"])
    _run([py, "scripts/generate_r3_r4_synthetic.py"])
    _run([py, "-m", "ukz16.validation.r1.cli", "--out", "reports/e2e/r1", "--skip-pytest"])
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r2.cli",
            "--cohort",
            "samples/validation/r2_synthetic_cohort.jsonl",
            "--out",
            "reports/e2e/r2",
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r3.cli",
            "freeze",
            "--out",
            "reports/e2e/r3/model_freeze.json",
            "--site",
            "SITE-EXT-1",
            "--site",
            "SITE-EXT-2",
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r3.cli",
            "run",
            "--cohort",
            "samples/validation/r3_synthetic_multisite.jsonl",
            "--freeze",
            "reports/e2e/r3/model_freeze.json",
            "--out",
            "reports/e2e/r3",
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r4.cli",
            "--log",
            "samples/validation/r4_synthetic_review_log.jsonl",
            "--out",
            "reports/e2e/r4",
        ]
    )
    _run([py, "-m", "ukz16.validation.bench.cli", "--out", "reports/e2e/bench", "--n", "100"])
    print("Synthetic e2e complete under reports/e2e/ (research-only, no clinical claim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
