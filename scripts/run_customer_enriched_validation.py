#!/usr/bin/env python3
"""Generate synthetic-enriched customer cohort and run R2→R3→R4 (research only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "customer_enriched"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    py = sys.executable
    _run([py, "scripts/generate_customer_enriched_cohort.py"])

    _run(
        [
            py,
            "-m",
            "ukz16.validation.r2.cli",
            "--cohort",
            str(REPORTS / "r2_cohort.jsonl"),
            "--out",
            str(REPORTS / "r2"),
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r3.cli",
            "freeze",
            "--out",
            str(REPORTS / "r3" / "model_freeze.json"),
            "--site",
            "SITE-A",
            "--site",
            "SITE-B",
            "--site",
            "SITE-C",
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r3.cli",
            "run",
            "--cohort",
            str(REPORTS / "r3_cohort.jsonl"),
            "--freeze",
            str(REPORTS / "r3" / "model_freeze.json"),
            "--out",
            str(REPORTS / "r3"),
        ]
    )
    _run(
        [
            py,
            "-m",
            "ukz16.validation.r4.cli",
            "--log",
            str(REPORTS / "r4_review_log.jsonl"),
            "--out",
            str(REPORTS / "r4"),
        ]
    )

    # Quick HEALTH_ID calculable check on a few rows
    from ukz16.domain.contracts import PrMOIngest
    from ukz16.domain.enums import HealthIdStatus
    from ukz16.engine.sequence import WorkerSequence
    from ukz16.governance.model_registry import load_model_package

    model = load_model_package("research-v0.2", enforce_signature=False)
    sequence = WorkerSequence(model)
    ok = 0
    n = 0
    with (REPORTS / "r2_cohort.jsonl").open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= 50:
                break
            row = json.loads(line)
            payload = PrMOIngest.model_validate(row["payload"])
            _quality, res = sequence.evaluate(payload)
            n += 1
            if res.health_id.status == HealthIdStatus.OK and res.health_id.value is not None:
                ok += 1
    summary = {
        "clinical_claim": False,
        "pipeline": "customer_vitals+synthetic_enrichment → R2/R3/R4",
        "health_id_ok_in_first_50": ok,
        "checked": n,
        "reports": str(REPORTS),
    }
    (REPORTS / "pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Customer enriched validation complete (research-only, no clinical claim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
