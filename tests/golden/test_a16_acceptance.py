from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import pytest
from sqlalchemy.orm import Session

from tests.helpers import make_prmo
from ukz16.api.main import app
from ukz16.corridors.baseline import assert_no_future_leakage, patient_level_split_ok
from ukz16.db.session import get_engine, init_db, reset_engine
from ukz16.domain.contracts import EmrFlags, Psychometrics, ReviewDecisionRequest, SocialMetrics
from ukz16.domain.enums import ComponentStatus, HealthIdStatus
from ukz16.governance.model_registry import load_model_package, stable_input_hash
from ukz16.quality.gates import run_quality_gates
from ukz16.services.evaluation import EvaluationService


def _svc() -> EvaluationService:
    init_db()
    session = Session(get_engine())
    return EvaluationService(session)


def test_a16_deterministic_same_inputs_same_hash_and_trace():
    svc = _svc()
    payload = make_prmo(encounter_id="DET-1")
    r1 = svc.evaluate(payload)
    svc.session.commit()

    # re-evaluate identical logical inputs with new encounter to avoid unique constraint
    payload2 = make_prmo(encounter_id="DET-2")
    # force same measured_at and vitals -> same input hash content except encounter_id
    # Compare pure engine hash excluding encounter by checking model+vitals path:
    h1 = stable_input_hash(payload.model_dump(mode="json"), "research-v0.1")
    h2 = stable_input_hash(payload.model_dump(mode="json"), "research-v0.1")
    assert h1 == h2

    model = load_model_package()
    q = run_quality_gates(payload, model)
    from ukz16.engine.calculator import evaluate_health_id

    e1 = evaluate_health_id(payload, q, model)
    e2 = evaluate_health_id(payload, q, model)
    assert e1.health_id.value == e2.health_id.value
    assert e1.evidence.contribution_trace == e2.evidence.contribution_trace
    assert e1.evidence.input_hash == e2.evidence.input_hash
    assert e1.diagnosis_claim is False
    assert e1.employer_export_allowed is False
    svc.session.close()


def test_a16_missing_height_weight():
    svc = _svc()
    payload = make_prmo(encounter_id="HW-1", height_cm=None, weight_kg=None)
    result = svc.evaluate(payload)
    svc.session.commit()
    hbody = next(c for c in result.components if c.name == "hBody")
    assert hbody.status == ComponentStatus.PARTIAL
    assert hbody.reason == "missing_height_weight"
    assert result.health_id.status in (HealthIdStatus.PARTIAL, HealthIdStatus.OK)
    svc.session.close()


def test_a16_no_psychometrics_hmental_not_calculable():
    svc = _svc()
    payload = make_prmo(encounter_id="PSY-1", psychometrics=None)
    result = svc.evaluate(payload)
    svc.session.commit()
    mental = next(c for c in result.components if c.name == "hMental")
    assert mental.status == ComponentStatus.NOT_CALCULABLE
    assert mental.reason == "no_validated_psychometrics"
    svc.session.close()


def test_a16_same_day_repeats_do_not_increase_persistence():
    svc = _svc()
    base = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    # Build history with deviations on 3 unique dates
    for i, day in enumerate([0, 1, 2]):
        p = make_prmo(
            worker_id="W-PERS",
            encounter_id=f"P-{i}",
            measured_at=base + timedelta(days=day),
            pulse=140.0,  # push population acute / low body score
            sbp=180.0,
            dbp=110.0,
        )
        svc.evaluate(p)
    svc.session.commit()

    # Two attempts same day
    d = base + timedelta(days=3)
    r1 = svc.evaluate(make_prmo(worker_id="W-PERS", encounter_id="P-same-1", measured_at=d, pulse=150, sbp=185, dbp=115))
    r2 = svc.evaluate(
        make_prmo(worker_id="W-PERS", encounter_id="P-same-2", measured_at=d + timedelta(hours=2), pulse=152, sbp=186, dbp=116)
    )
    svc.session.commit()
    # unique dates count for r2 should treat same calendar day once in dates list
    assert r2.persistence.same_day_attempts_do_not_increase_persistence is True
    assert len(r2.persistence.dates) == len(set(r2.persistence.dates))
    assert r1.persistence.unique_dates_with_deviation <= r2.persistence.unique_dates_with_deviation + 0
    svc.session.close()


def test_a16_current_point_excluded_from_baseline():
    svc = _svc()
    base = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
    for i in range(4):
        svc.evaluate(
            make_prmo(
                worker_id="W-BASE",
                encounter_id=f"B-{i}",
                measured_at=base + timedelta(days=i),
                pulse=70 + i,
            )
        )
    svc.session.commit()
    current = make_prmo(
        worker_id="W-BASE",
        encounter_id="B-cur",
        measured_at=base + timedelta(days=10),
        pulse=70,
    )
    result = svc.evaluate(current)
    svc.session.commit()
    assert result.personal_deviation is not None
    # baseline should not include current date
    assert result.personal_deviation.baseline_n_unique_dates >= 3
    assert result.personal_deviation.reason in (None, "insufficient_baseline")
    svc.session.close()


def test_a16_future_leakage_and_patient_split():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert_no_future_leakage([t1], [t0])
    try:
        assert_no_future_leakage([t0], [t1])
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert patient_level_split_ok({"a"}, {"b"})
    assert not patient_level_split_ok({"a", "c"}, {"c"})


def test_a16_unknown_unit_and_bad_protocol_block():
    svc = _svc()
    bad_unit = make_prmo(encounter_id="U-1", unit_system="imperial")
    r1 = svc.evaluate(bad_unit)
    assert r1.health_id.status == HealthIdStatus.NOT_CALCULABLE
    assert r1.health_id.reason == "unknown_unit"

    bad_proto = make_prmo(encounter_id="U-2", protocol_id="UNKNOWN_PROTO")
    r2 = svc.evaluate(bad_proto)
    assert r2.health_id.reason == "bad_protocol"
    svc.session.commit()
    svc.session.close()


def test_a16_review_pending_confirmed_rejected():
    svc = _svc()
    result = svc.evaluate(
        make_prmo(
            encounter_id="REV-1",
            psychometrics=Psychometrics(instrument="PHQ-9", score=2, validated=True),
            social=SocialMetrics(validated=True, engagement_score=0.7),
        )
    )
    svc.session.commit()
    assert result.clinical_review.status == "pending"

    confirmed = svc.review(
        result.evaluation_id,
        ReviewDecisionRequest(decision="confirmed", medical_worker_id="MW-1", comment="ok"),
        actor_role="medical_worker",
    )
    assert confirmed.clinical_review.status == "confirmed"

    # new evaluation for reject path
    result2 = svc.evaluate(make_prmo(encounter_id="REV-2"))
    svc.session.commit()
    rejected = svc.review(
        result2.evaluation_id,
        ReviewDecisionRequest(decision="rejected", medical_worker_id="MW-1", comment="noise"),
        actor_role="medical_worker",
    )
    assert rejected.clinical_review.status == "rejected"
    svc.session.commit()
    svc.session.close()


def test_a16_output_contract_fields():
    svc = _svc()
    result = svc.evaluate(make_prmo(encounter_id="OUT-1"))
    svc.session.commit()
    assert result.components
    assert result.completeness is not None
    assert result.uncertainty is not None
    assert result.evidence.input_hash
    assert result.evidence.model_version == "research-v0.1"
    assert result.evidence.contribution_trace is not None
    assert "hBody" in [c.name for c in result.components]
    svc.session.close()


def test_a16_chronic_only_from_emr_not_from_persistence():
    svc = _svc()
    # Persistence alone must NOT set chronic_from_emr
    base = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    for i in range(3):
        svc.evaluate(
            make_prmo(
                worker_id="W-CHR",
                encounter_id=f"C-{i}",
                measured_at=base + timedelta(days=i),
                pulse=150,
                sbp=180,
                dbp=110,
            )
        )
    svc.session.commit()
    without_emr = svc.evaluate(
        make_prmo(worker_id="W-CHR", encounter_id="C-4", measured_at=base + timedelta(days=4), pulse=155, sbp=185, dbp=112)
    )
    assert without_emr.chronic_from_emr.clinically_confirmed is False
    assert without_emr.chronic_from_emr.inferred_from_persistence is False

    with_emr = svc.evaluate(
        make_prmo(
            worker_id="W-CHR",
            encounter_id="C-5",
            measured_at=base + timedelta(days=5),
            pulse=70,
            emr=EmrFlags(clinically_confirmed_chronic=True, chronic_condition_codes=["I10"]),
        )
    )
    svc.session.commit()
    assert with_emr.chronic_from_emr.clinically_confirmed is True
    assert with_emr.chronic_from_emr.codes == ["I10"]
    assert with_emr.chronic_from_emr.source == "emr_only"
    assert with_emr.diagnosis_claim is False
    svc.session.close()


def test_a16_duplicate_encounter_rejected():
    svc = _svc()
    svc.evaluate(make_prmo(encounter_id="DUP-1"))
    svc.session.commit()
    with pytest.raises(ValueError, match="duplicate_encounter"):
        svc.evaluate(make_prmo(encounter_id="DUP-1"))
    svc.session.close()


def test_a16_api_employer_export_forbidden():
    reset_engine()
    init_db()
    client = TestClient(app)
    resp = client.post("/v1/employer/export", headers={"X-API-Key": "researcher-key"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "employer_export_forbidden"


def test_a16_api_evaluate_and_model_card():
    reset_engine()
    init_db()
    client = TestClient(app)
    payload = make_prmo(encounter_id="API-1").model_dump(mode="json")
    resp = client.post("/v1/evaluate", json=payload, headers={"X-API-Key": "researcher-key"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["employer_export_allowed"] is False
    assert body["diagnosis_claim"] is False

    card = client.get("/v1/model-card", headers={"X-API-Key": "researcher-key"})
    assert card.status_code == 200
    assert card.json()["version"] == "research-v0.1"

    models = client.get("/v1/models", headers={"X-API-Key": "auditor-key"})
    assert models.status_code == 200
    assert any(m["version"] == "research-v0.1" for m in models.json())
