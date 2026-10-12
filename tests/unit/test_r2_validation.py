from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ukz16.validation.r2.cohort import load_cohort_jsonl
from ukz16.validation.r2.metrics import brier_score, expected_calibration_error
from ukz16.validation.r2.runner import run_r2_validation
from ukz16.validation.r2.splits import group_holdout_by_worker, temporal_split


ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / "samples" / "validation" / "r2_synthetic_cohort.jsonl"


def _ensure_cohort() -> Path:
    if not COHORT.exists():
        from scripts.generate_r2_synthetic_cohort import main

        main()
    return COHORT


def test_group_holdout_no_worker_overlap():
    rows = load_cohort_jsonl(_ensure_cohort())
    split = group_holdout_by_worker(rows, test_fraction=0.3, seed=16)
    assert split.train_workers.isdisjoint(split.test_workers)
    assert len(split.train) > 0
    assert len(split.test) > 0


def test_temporal_split_purges_workers():
    rows = load_cohort_jsonl(_ensure_cohort())
    cutoff = datetime(2026, 2, 1, tzinfo=timezone.utc)
    split = temporal_split(rows, cutoff=cutoff)
    assert split.train_workers.isdisjoint(split.test_workers)
    assert all(r.measured_at < cutoff for r in split.train)
    assert all(r.measured_at >= cutoff for r in split.test)


def test_metrics_helpers():
    y = [0, 1, 1, 0]
    p = [0.1, 0.8, 0.7, 0.2]
    assert brier_score(y, p) is not None
    ece = expected_calibration_error(y, p, n_bins=4)
    assert ece["ece"] is not None


def test_run_r2_writes_report(tmp_path: Path):
    cohort = _ensure_cohort()
    out = tmp_path / "r2"
    report = run_r2_validation(
        cohort,
        output_dir=out,
        split="both",
        test_fraction=0.3,
        seed=16,
    )
    assert report["n_rows"] == 60
    assert report["n_workers"] == 10
    assert "group" in report["splits"]
    assert "temporal" in report["splits"]
    assert report["splits"]["group"]["guards"]["patient_level_split_ok"] is True
    assert report["diagnosis_claim"] is False
    assert (out / "r2_report.json").exists()
    assert (out / "r2_report.md").exists()
