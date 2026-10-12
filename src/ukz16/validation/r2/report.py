from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_r2_report(output_dir: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "r2_report.json"
    md_path = output_dir / "r2_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# R2 Retrospective Validation Report",
        "",
        f"- Model: `{report.get('model_version')}`",
        f"- Package hash: `{report.get('model_package_hash')}`",
        f"- Cohort: `{report.get('cohort_path')}`",
        f"- Rows / workers: {report.get('n_rows')} / {report.get('n_workers')}",
        f"- Diagnosis claim: `{report.get('diagnosis_claim')}`",
        "",
        "## Notes",
        "",
    ]
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    lines.extend(["", "## Splits", ""])
    for name, split in (report.get("splits") or {}).items():
        metrics = split.get("metrics") or {}
        abst = split.get("abstention") or {}
        conf = metrics.get("confusion") or {}
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Method: `{split.get('method')}`",
                f"- Cutoff: `{split.get('cutoff')}`",
                f"- Train/test rows: {split.get('n_train')} / {split.get('n_test')}",
                f"- Train/test workers: {split.get('n_train_workers')} / {split.get('n_test_workers')}",
                f"- Worker overlap: `{split.get('overlap_workers')}`",
                f"- Abstention rate: {abst.get('abstention_rate')}",
                f"- Brier: {metrics.get('brier')} (95% CI { (metrics.get('brier_ci95') or {}).get('low') }–{(metrics.get('brier_ci95') or {}).get('high') })",
                f"- ECE: {(metrics.get('ece') or {}).get('ece')}",
                f"- FN / FP: {conf.get('fn')} / {conf.get('fp')}",
                f"- Patient split OK: `{(split.get('guards') or {}).get('patient_level_split_ok')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation gate",
            "",
            "- This report does **not** authorize clinical use.",
            "- Thresholds for pass/fail must be pre-registered in the statistical analysis plan before claiming R2 success.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
