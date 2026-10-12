from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_r4_report(output_dir: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "r4_report.json"
    md_path = output_dir / "r4_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def _to_markdown(report: dict[str, Any]) -> str:
    m = report.get("metrics") or {}
    nb = m.get("net_benefit") or {}
    safety = m.get("safety") or {}
    return "\n".join(
        [
            "# R4 Clinical Utility Report",
            "",
            f"- Cases / workers: {report.get('n_cases')} / {report.get('n_workers')}",
            f"- Sites: {', '.join(report.get('sites') or [])}",
            f"- Override rate: {m.get('override_rate')}",
            f"- Mean time-to-review (sec): {m.get('mean_time_to_review_sec')}",
            f"- Decisions: `{m.get('decision_distribution')}`",
            f"- Net benefit (model / all / none): {nb.get('net_benefit_model')} / {nb.get('net_benefit_all')} / {nb.get('net_benefit_none')}",
            f"- Harm flags: {safety.get('n_harm_flags')} (rate {safety.get('harm_rate')})",
            f"- Auto diagnosis: `{safety.get('diagnosis_auto_assigned')}`",
            "",
            "## Gate",
            "",
            "- Utility > risk must be shown in a signed clinical study before operational claim.",
            "- Module remains decision-support with mandatory human review.",
            "",
        ]
    )
