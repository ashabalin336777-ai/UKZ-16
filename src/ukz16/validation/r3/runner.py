from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ukz16.governance.model_registry import load_model_package
from ukz16.validation.r2.cohort import load_cohort_jsonl
from ukz16.validation.r2.evaluate import predict_cohort
from ukz16.validation.r2.metrics import brier_score, confusion_at_threshold, expected_calibration_error
from ukz16.validation.r3.freeze import assert_model_matches_freeze, load_freeze
from ukz16.validation.r3.report import write_r3_report


def run_r3_validation(
    cohort_path: Path,
    freeze_path: Path,
    *,
    output_dir: Path,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """External prospective-style evaluation on a frozen model.

    Uses multi-site cohort JSONL. Does not retrain or update the model.
    """
    freeze = load_freeze(freeze_path)
    match = assert_model_matches_freeze(freeze)
    if not match["ok"]:
        raise RuntimeError(f"frozen_model_mismatch:{match}")

    rows = load_cohort_jsonl(cohort_path)
    model = load_model_package(freeze["model_version"], enforce_signature=False)
    preds = predict_cohort(rows, model)

    scored = [p for p in preds if not p.abstained and p.risk_prob is not None]
    y = [p.reference_label for p in scored]
    p = [float(x.risk_prob) for x in scored]

    by_site: dict[str, list] = defaultdict(list)
    for pred in scored:
        site = str(pred.subgroup.get("site_id") or "unknown")
        by_site[site].append(pred)

    site_metrics: dict[str, Any] = {}
    for site, items in sorted(by_site.items()):
        ys = [i.reference_label for i in items]
        ps = [float(i.risk_prob) for i in items]
        site_metrics[site] = {
            "n": len(items),
            "brier": None if not ys else round(brier_score(ys, ps) or 0.0, 6),
            "ece": expected_calibration_error(ys, ps).get("ece"),
            "confusion": confusion_at_threshold(ys, ps, threshold=threshold),
        }

    devices = sorted({str(r.subgroup.get("device_id") or "unknown") for r in rows})
    report = {
        "stage": "R3",
        "protocol_id": freeze.get("protocol_id"),
        "freeze_path": str(freeze_path),
        "frozen_at": freeze.get("frozen_at"),
        "model_version": model.version,
        "model_package_hash": model.package_hash,
        "freeze_check": match,
        "cohort_path": str(cohort_path),
        "n_rows": len(rows),
        "n_workers": len({r.worker_id for r in rows}),
        "sites": sorted(by_site.keys()),
        "devices": devices,
        "intended_use": "research_only",
        "diagnosis_claim": False,
        "auto_update": False,
        "overall": {
            "n_scored": len(scored),
            "n_abstained": len(preds) - len(scored),
            "abstention_rate": round((len(preds) - len(scored)) / len(preds), 6) if preds else None,
            "brier": None if not y else round(brier_score(y, p) or 0.0, 6),
            "ece": expected_calibration_error(y, p).get("ece"),
            "confusion": confusion_at_threshold(y, p, threshold=threshold),
        },
        "transportability": {"by_site": site_metrics},
        "notes": [
            "R3 requires independent external site enrollment against a frozen package.",
            "Synthetic multi-site cohort is for pipeline readiness only.",
            "No model update is performed in this runner.",
        ],
    }
    write_r3_report(output_dir, report)
    return report
