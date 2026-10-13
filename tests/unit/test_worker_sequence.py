"""WorkerSequence keeps corridor history per worker and excludes the current point."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ukz16.domain.contracts import (
    ContextInfo,
    EmrFlags,
    PrMOIngest,
    Provenance,
    Psychometrics,
    SocialMetrics,
    Vitals,
)
from ukz16.engine.sequence import WorkerSequence
from ukz16.governance.model_registry import load_model_package


def _payload(worker: str, day: int, pulse: float) -> PrMOIngest:
    measured = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    return PrMOIngest(
        worker_id=worker,
        encounter_id=f"{worker}-D{day}",
        measured_at=measured,
        source_system="TEST",
        consent_research=True,
        protocol_id="PRMO_STD_v1",
        protocol_version="1.0",
        vitals=Vitals(
            height_cm=170,
            weight_kg=70,
            bp_systolic_mmhg=120,
            bp_diastolic_mmhg=80,
            pulse_bpm=pulse,
        ),
        context=ContextInfo(site_id="SITE-A", age_years=40),
        psychometrics=Psychometrics(
            instrument="PHQ-9", score=2, scored_at=measured, validated=True
        ),
        social_metrics=SocialMetrics(validated=True, engagement_score=0.8),
        emr_flags=EmrFlags(),
        provenance=Provenance(device_id="DEV", unit_system="SI_medical"),
    )


def test_sequence_baseline_excludes_current_and_separates_workers():
    model = load_model_package("research-v0.2", enforce_signature=False)
    seq = WorkerSequence(model)
    early = []
    for day, pulse in ((0, 70), (1, 70), (2, 70)):
        _q, result = seq.evaluate(_payload("W1", day, pulse))
        early.append(result)
    assert early[0].personal_deviation is not None
    assert early[0].personal_deviation.reason == "insufficient_baseline"
    assert early[2].personal_deviation.baseline_n_unique_dates == 2

    _q, shifted = seq.evaluate(_payload("W1", 3, 140))
    assert shifted.personal_deviation is not None
    assert shifted.personal_deviation.baseline_n_unique_dates == 3
    assert shifted.personal_deviation.outside_corridor is True

    _q, other = seq.evaluate(_payload("W2", 0, 70))
    assert other.personal_deviation is not None
    assert other.personal_deviation.reason == "insufficient_baseline"
