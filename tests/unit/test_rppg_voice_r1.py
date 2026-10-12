from __future__ import annotations

import math

from ukz16.experimental.rppg import extract_rppg_feature
from ukz16.experimental.signals import extract_experimental_features
from ukz16.experimental.voice import extract_voice_svs_feature
from ukz16.validation.r1.checklist import evaluate_r0_artifacts
from ukz16.validation.r1.runner import run_r1_report
from ukz16.config import ROOT


def _sine_ppg(fs: float = 30.0, seconds: float = 8.0, bpm: float = 72.0) -> list[float]:
    n = int(fs * seconds)
    freq = bpm / 60.0
    return [math.sin(2 * math.pi * freq * (i / fs)) for i in range(n)]


def test_rppg_from_signal():
    feat = extract_rppg_feature(
        {
            "consent_scope": "research_rppg",
            "signal": _sine_ppg(),
            "sampling_rate": 30.0,
            "protocol_version": "rppg-r0",
            "device_id": "CAM-1",
        }
    )
    assert feat.name == "rPPG"
    assert feat.enters_health_id is False
    assert feat.value is not None
    assert feat.reason == "experimental_rppg_computed"


def test_rppg_bpm_estimate():
    feat = extract_rppg_feature(
        {"consent_scope": "research_rppg", "bpm_estimate": 68.0}
    )
    assert feat.value is not None
    assert feat.reason == "experimental_rppg_computed"


def test_voice_svs_from_acoustics():
    feat = extract_voice_svs_feature(
        {
            "consent_scope": "research_voice",
            "f0_hz": 155.0,
            "jitter_pct": 0.8,
            "shimmer_pct": 2.0,
            "hnr_db": 18.0,
        }
    )
    assert feat.name == "voice_SVS"
    assert feat.enters_hMental is False
    assert feat.value is not None
    assert feat.reason == "experimental_voice_svs_computed"


def test_voice_svs_passthrough_score():
    feat = extract_voice_svs_feature(
        {"consent_scope": "research_voice", "svs_score": 0.42}
    )
    assert feat.value == 0.42


def test_experimental_bundle_never_enters_scores():
    features = extract_experimental_features(
        {
            "experimental_signals": {
                "hrv": {"consent_scope": "r", "nn_intervals_ms": [800, 820, 790, 810]},
                "rppg": {"consent_scope": "r", "bpm_estimate": 70},
                "voice": {"consent_scope": "r", "svs_score": 0.5},
            }
        }
    )
    assert all(f.enters_health_id is False and f.enters_hMental is False for f in features)
    assert all(f.value is not None for f in features)


def test_r1_report_skip_pytest(tmp_path):
    r0 = evaluate_r0_artifacts(ROOT)
    assert any(x["present"] for x in r0)
    report = run_r1_report(tmp_path, run_pytest=False)
    assert report["schema"] == "ukz16.r1_analytical_report.v1"
    assert report["r0"]["all_present"] is True
    assert (tmp_path / "r1_report.json").exists()
    assert (tmp_path / "r1_report.md").exists()
    assert report["a16"]["covered"] >= 10
