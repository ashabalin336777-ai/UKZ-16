from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_r3_report(output_dir: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "r3_report.json"
    md_path = output_dir / "r3_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def _to_markdown(report: dict[str, Any]) -> str:
    overall = report.get("overall") or {}
    lines = [
        "# R3 External Prospective Validation Report",
        "",
        f"- Protocol: `{report.get('protocol_id')}`",
        f"- Frozen model: `{report.get('model_version')}` / `{report.get('model_package_hash')}`",
        f"- Freeze check OK: `{(report.get('freeze_check') or {}).get('ok')}`",
        f"- Sites: {', '.join(report.get('sites') or [])}",
        f"- Rows / workers: {report.get('n_rows')} / {report.get('n_workers')}",
        f"- Brier / ECE: {overall.get('brier')} / {overall.get('ece')}",
        f"- Abstention rate: {overall.get('abstention_rate')}",
        f"- Auto-update: `{report.get('auto_update')}`",
        "",
        "## Transportability by site",
        "",
    ]
    for site, metrics in ((report.get("transportability") or {}).get("by_site") or {}).items():
        conf = metrics.get("confusion") or {}
        lines.append(
            f"- **{site}**: n={metrics.get('n')}, brier={metrics.get('brier')}, "
            f"FN={conf.get('fn')}, FP={conf.get('fp')}"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- External prospective claim requires real second site/PАК, frozen model, and signed protocol.",
            "- Synthetic output does not authorize clinical deployment.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
