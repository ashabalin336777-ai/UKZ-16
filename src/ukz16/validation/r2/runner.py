from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ukz16.governance.model_registry import load_model_package
from ukz16.validation.r2.cohort import load_cohort_jsonl
from ukz16.validation.r2.evaluate import predict_cohort
from ukz16.validation.r2.metrics import (
    bootstrap_ci,
    brier_score,
    confusion_at_threshold,
    expected_calibration_error,
    subgroup_metrics,
)
from ukz16.validation.r2.report import write_r2_report
from ukz16.validation.r2.splits import group_holdout_by_worker, temporal_split


def run_r2_validation(
    cohort_path: Path,
    *,
    output_dir: Path,
    model_version: str | None = None,
    split: Literal["group", "temporal", "both"] = "both",
    temporal_cutoff: datetime | None = None,
    test_fraction: float = 0.3,
    threshold: float = 0.5,
    seed: int = 16,
) -> dict[str, Any]:
    rows = load_cohort_jsonl(cohort_path)
    model = load_model_package(model_version)
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "stage": "R2",
        "model_version": model.version,
        "model_package_hash": model.package_hash,
        "cohort_path": str(cohort_path),
        "n_rows": len(rows),
        "n_workers": len({r.worker_id for r in rows}),
        "reference_sources": sorted({r.reference_source for r in rows}),
        "intended_use": "research_only",
        "diagnosis_claim": False,
        "splits": {},
        "notes": [
            "HEALTH_ID is research-only until R0–R4 complete.",
            "Reference labels must be independent of HEALTH_ID formula.",
            "No weight renormalization; abstentions reported separately.",
        ],
    }

    plans: list[tuple[str, Any]] = []
    if split in {"group", "both"}:
        plans.append(("group", group_holdout_by_worker(rows, test_fraction=test_fraction, seed=seed)))
    if split in {"temporal", "both"}:
        if temporal_cutoff is None:
            # default: median timestamp
            times = sorted(r.measured_at for r in rows)
            temporal_cutoff = times[len(times) // 2]
        plans.append(("temporal", temporal_split(rows, cutoff=temporal_cutoff)))

    for name, split_res in plans:
        preds = predict_cohort(split_res.test, model)
        scored = [p for p in preds if not p.abstained and p.risk_prob is not None]
        y = [p.reference_label for p in scored]
        p = [float(p_.risk_prob) for p_ in scored]
        brier = brier_score(y, p)
        brier_values = [(pi - yi) ** 2 for yi, pi in zip(y, p, strict=True)] if y else []
        ece = expected_calibration_error(y, p)
        conf = confusion_at_threshold(y, p, threshold=threshold)
        report["splits"][name] = {
            "method": split_res.method,
            "cutoff": split_res.cutoff,
            "n_train": len(split_res.train),
            "n_test": len(split_res.test),
            "n_train_workers": len(split_res.train_workers),
            "n_test_workers": len(split_res.test_workers),
            "overlap_workers": sorted(split_res.train_workers & split_res.test_workers),
            "abstention": {
                "n_test": len(preds),
                "n_scored": len(scored),
                "n_abstained": len(preds) - len(scored),
                "abstention_rate": round((len(preds) - len(scored)) / len(preds), 6) if preds else None,
            },
            "metrics": {
                "brier": None if brier is None else round(brier, 6),
                "brier_ci95": bootstrap_ci(brier_values, seed=seed),
                "ece": ece,
                "confusion": conf,
            },
            "subgroup": {
                "site_id": subgroup_metrics(y, p, [x.subgroup for x in scored], "site_id") if scored else {},
                "sex": subgroup_metrics(y, p, [x.subgroup for x in scored], "sex") if scored else {},
            },
            "failure_analysis": {
                "false_negatives": conf["fn"],
                "false_positives": conf["fp"],
                "abstained_positive_refs": sum(
                    1 for row in preds if row.abstained and row.reference_label == 1
                ),
                "acute_flags_on_test": sum(1 for row in preds if row.acute),
                "persistence_flags_on_test": sum(1 for row in preds if row.persistence),
            },
            "guards": {
                "patient_level_split_ok": len(split_res.train_workers & split_res.test_workers) == 0,
                "auto_model_update": False,
            },
        }

    write_r2_report(output_dir, report)
    return report
