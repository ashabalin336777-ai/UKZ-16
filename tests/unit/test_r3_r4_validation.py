from __future__ import annotations

from pathlib import Path

from ukz16.validation.r3.freeze import assert_model_matches_freeze, freeze_model_for_r3
from ukz16.validation.r3.runner import run_r3_validation
from ukz16.validation.r4.runner import run_r4_utility

ROOT = Path(__file__).resolve().parents[2]


def _ensure_samples() -> tuple[Path, Path]:
    r3 = ROOT / "samples" / "validation" / "r3_synthetic_multisite.jsonl"
    r4 = ROOT / "samples" / "validation" / "r4_synthetic_review_log.jsonl"
    if not r3.exists() or not r4.exists():
        from scripts.generate_r3_r4_synthetic import main

        main()
    return r3, r4


def test_r3_freeze_and_run(tmp_path: Path):
    cohort, _ = _ensure_samples()
    freeze_path = tmp_path / "freeze.json"
    freeze = freeze_model_for_r3(output_path=freeze_path, sites=["SITE-EXT-1", "SITE-EXT-2"])
    assert freeze["auto_update_forbidden"] is True
    match = assert_model_matches_freeze(freeze)
    assert match["ok"] is True

    out = tmp_path / "r3"
    report = run_r3_validation(cohort, freeze_path, output_dir=out)
    assert report["freeze_check"]["ok"] is True
    assert report["diagnosis_claim"] is False
    assert report["auto_update"] is False
    assert "SITE-EXT-1" in report["sites"]
    assert "SITE-EXT-2" in report["sites"]
    assert (out / "r3_report.md").exists()


def test_r4_utility(tmp_path: Path):
    _, log_path = _ensure_samples()
    out = tmp_path / "r4"
    report = run_r4_utility(log_path, output_dir=out, model_version="research-v0.2")
    assert report["n_cases"] == 40
    assert report["human_review_required"] is True
    assert report["diagnosis_claim"] is False
    assert report["metrics"]["safety"]["diagnosis_auto_assigned"] is False
    assert 0.0 <= report["metrics"]["override_rate"] <= 1.0
    assert (out / "r4_report.json").exists()
