from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ukz16 import __version__
from ukz16.config import ROOT, get_settings
from ukz16.governance.model_registry import load_model_package
from ukz16.validation.r1.checklist import A16_ITEMS, R0_ARTIFACTS, evaluate_r0_artifacts


def run_r1_report(
    output_dir: Path,
    *,
    run_pytest: bool = True,
    pytest_args: list[str] | None = None,
) -> dict[str, Any]:
    """Build R0 freeze + R1/A16 analytical acceptance report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    pkg = load_model_package(settings.model_version, enforce_signature=False)

    r0 = evaluate_r0_artifacts(ROOT)
    a16 = [
        {
            "id": item["id"],
            "criterion": item["criterion"],
            "artifact": item["artifact"],
            "status": item["status"],
            "notes": item.get("notes"),
        }
        for item in A16_ITEMS
    ]
    covered = sum(1 for x in a16 if x["status"] == "covered")
    partial = sum(1 for x in a16 if x["status"] == "partial")

    pytest_result: dict[str, Any] = {"ran": False}
    if run_pytest:
        cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line"]
        if pytest_args:
            cmd.extend(pytest_args)
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        pytest_result = {
            "ran": True,
            "returncode": proc.returncode,
            "passed": proc.returncode == 0,
            "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-20:]),
            "stderr_tail": "\n".join(proc.stderr.strip().splitlines()[-10:]),
        }

    report: dict[str, Any] = {
        "schema": "ukz16.r1_analytical_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ukz16_version": __version__,
        "model_version": pkg.version,
        "model_package_hash": pkg.package_hash,
        "research_only": True,
        "clinical_claim": False,
        "r0": {
            "artifacts": r0,
            "all_present": all(x["present"] for x in r0),
            "expected": [a["path"] for a in R0_ARTIFACTS],
        },
        "a16": {
            "items": a16,
            "covered": covered,
            "partial": partial,
            "total": len(a16),
        },
        "pytest": pytest_result,
        "hard_rules": [
            "no_hidden_imputation",
            "no_diagnosis_or_fitness_claim",
            "no_employer_individual_health_id",
            "chronic_from_emr_only",
            "drift_alert_no_auto_update",
        ],
        "notes": [
            "R1 is analytical correctness on synthetic/golden tests, not clinical validity.",
            "Partial A16 items (employer enterprise contour, MFA/encryption/backup) remain residual risk.",
        ],
    }

    # ready: all non-partial covered + R0 present + pytest green (when run)
    non_partial = [x for x in a16 if x["status"] != "partial"]
    pytest_ok = True if not pytest_result.get("ran") else bool(pytest_result.get("passed"))
    report["a16"]["ready_for_signed_acceptance"] = (
        all(x["status"] == "covered" for x in non_partial)
        and report["r0"]["all_present"]
        and pytest_ok
        and bool(pytest_result.get("ran"))
    )

    (output_dir / "r1_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "r1_report.md").write_text(_to_markdown(report), encoding="utf-8")
    return report


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# R1 Analytical Acceptance Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- model_version: `{report['model_version']}`",
        f"- package_hash: `{report['model_package_hash']}`",
        f"- research_only: `{report['research_only']}`",
        f"- pytest_passed: `{report['pytest'].get('passed')}`",
        f"- ready_for_signed_acceptance: `{report['a16']['ready_for_signed_acceptance']}`",
        "",
        "## R0 artifacts",
        "",
    ]
    for item in report["r0"]["artifacts"]:
        mark = "x" if item["present"] else " "
        lines.append(f"- [{mark}] `{item['path']}` — {item['title']}")
    lines.extend(["", "## A16 checklist", ""])
    lines.append("| ID | Status | Criterion |")
    lines.append("|----|--------|-----------|")
    for item in report["a16"]["items"]:
        lines.append(f"| {item['id']} | {item['status']} | {item['criterion']} |")
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
