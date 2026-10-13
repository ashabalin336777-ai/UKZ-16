from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ukz16.domain.contracts import Psychometrics, SocialMetrics
from ukz16.domain.enums import ComponentStatus
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import load_model_package
from ukz16.quality.gates import run_quality_gates
from tests.helpers import make_prmo


def _eval(payload):
    model = load_model_package("research-v0.2", enforce_signature=False)
    quality = run_quality_gates(payload, model)
    return evaluate_health_id(payload, quality, model), quality


def test_height_out_of_range_does_not_enter_bmi():
    payload = make_prmo(encounter_id="H10", height_cm=10.0, weight_kg=70.0)
    result, quality = _eval(payload)
    assert quality.field_quality["height_cm"].value == "reject"
    bmi = next(c for c in result.components if c.name == "bmi")
    ap = next(c for c in result.components if c.name == "ap_baevsky")
    body = next(c for c in result.components if c.name == "hBody")
    assert bmi.status == ComponentStatus.MISSING
    assert bmi.value is None
    assert bmi.reason == "out_of_range"
    assert ap.value is None
    assert ap.reason == "out_of_range"
    assert body.status == ComponentStatus.DERIVED
    assert body.value is not None


def test_unknown_instrument_and_future_score_do_not_enter_hmental():
    measured = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
    unknown, _ = _eval(
        make_prmo(
            encounter_id="PSY-UNK",
            measured_at=measured,
            psychometrics=Psychometrics(
                instrument="RANDOM-Q",
                score=3,
                scored_at=measured,
                validated=True,
            ),
            social=SocialMetrics(validated=True, engagement_score=0.5),
        )
    )
    mental = next(c for c in unknown.components if c.name == "hMental")
    assert mental.status == ComponentStatus.MISSING
    assert mental.reason == "unknown_instrument"
    assert mental.value is None

    future, _ = _eval(
        make_prmo(
            encounter_id="PSY-FUT",
            measured_at=measured,
            psychometrics=Psychometrics(
                instrument="PHQ-9",
                score=3,
                scored_at=measured + timedelta(days=1),
                validated=True,
            ),
        )
    )
    mental_f = next(c for c in future.components if c.name == "hMental")
    assert mental_f.reason == "psychometrics_after_encounter"
    assert mental_f.value is None


def test_instrument_specific_scoring():
    measured = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
    phq, _ = _eval(
        make_prmo(
            encounter_id="PHQ",
            measured_at=measured,
            psychometrics=Psychometrics(
                instrument="PHQ-9", score=0, scored_at=measured, validated=True
            ),
        )
    )
    gad, _ = _eval(
        make_prmo(
            encounter_id="GAD",
            measured_at=measured,
            psychometrics=Psychometrics(
                instrument="GAD-7", score=21, scored_at=measured, validated=True
            ),
        )
    )
    who, _ = _eval(
        make_prmo(
            encounter_id="WHO",
            measured_at=measured,
            psychometrics=Psychometrics(
                instrument="WHO-5", score=100, scored_at=measured, validated=True
            ),
        )
    )
    assert next(c for c in phq.components if c.name == "hMental").value == 1.0
    assert next(c for c in gad.components if c.name == "hMental").value == 0.0
    assert next(c for c in who.components if c.name == "hMental").value == 1.0
    assert next(c for c in who.components if c.name == "hMental").formula_id == "hMental_who5_v0"
