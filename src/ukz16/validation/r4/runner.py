from __future__ import annotations

from pathlib import Path
from typing import Any

from ukz16.validation.r4.logs import load_review_log_jsonl
from ukz16.validation.r4.metrics import (
    decision_distribution,
    mean_time_to_review,
    net_benefit,
    override_rate,
    safety_summary,
)
from ukz16.validation.r4.report import write_r4_report


def run_r4_utility(
    review_log_path: Path,
    *,
    output_dir: Path,
    threshold: float = 0.5,
    model_version: str | None = None,
) -> dict[str, Any]:
    rows = load_review_log_jsonl(review_log_path)
    report = {
        "stage": "R4",
        "review_log_path": str(review_log_path),
        "model_version": model_version,
        "n_cases": len(rows),
        "n_workers": len({r.worker_id for r in rows}),
        "sites": sorted({r.site_id for r in rows}),
        "intended_use": "research_only",
        "diagnosis_claim": False,
        "human_review_required": True,
        "metrics": {
            "override_rate": round(override_rate(rows), 6),
            "mean_time_to_review_sec": round(mean_time_to_review(rows), 3),
            "decision_distribution": decision_distribution(rows),
            "net_benefit": net_benefit(rows, threshold=threshold),
            "safety": safety_summary(rows),
        },
        "notes": [
            "R4 evaluates human-AI team usefulness, not automatic diagnosis.",
            "Synthetic review logs only prove pipeline readiness.",
            "Clinical utility claim needs prospective clinician study protocol.",
        ],
    }
    write_r4_report(output_dir, report)
    return report
