from __future__ import annotations

from sqlalchemy import select

from ukz16.config import get_settings
from ukz16.db.models import AuditEventRow, LaneRecordRow
from ukz16.db.session import init_db, reset_engine
from ukz16.domain.enums import HealthIdStatus
from ukz16.engine.calculator import evaluate_health_id
from ukz16.engine.guidance import build_guidance
from ukz16.governance.model_registry import load_model_package
from ukz16.lanes.pipeline import build_lane_bundle
from ukz16.privacy.pseudonym import Pseudonymizer, get_pseudonymizer
from ukz16.quality.gates import run_quality_gates
from ukz16.services.evaluation import EvaluationService
from ukz16.validation.bench.runner import run_bench
from tests.helpers import make_prmo
from fastapi.testclient import TestClient
from ukz16.api.main import app
from ukz16.db.session import get_session


def test_pseudonym_stable_and_not_raw_id():
    get_pseudonymizer.cache_clear()
    pz = Pseudonymizer("test-pepper")
    a = pz.subject_id("W-1")
    b = pz.subject_id("W-1")
    c = pz.subject_id("W-2")
    assert a == b
    assert a != c
    assert "W-1" not in a


def test_lane_bundle_and_guidance():
    model = load_model_package("research-v0.2", enforce_signature=False)
    payload = make_prmo(encounter_id="LANE-1", height_cm=None, weight_kg=None)
    quality = run_quality_gates(payload, model)
    result = evaluate_health_id(payload, quality, model)
    assert result.guidance is not None
    assert result.guidance.suggested_next_step
    assert "missing" in (result.guidance.codes or []) or result.health_id.status == HealthIdStatus.NOT_CALCULABLE

    bundle = build_lane_bundle(payload, result, actor_id="t", actor_role="researcher")
    assert bundle.research["employer_export_allowed"] is False
    assert bundle.research["subject_pseudo_id"].startswith("sub_")
    assert "W-1" not in bundle.research["subject_pseudo_id"]
    assert bundle.audit.get("phi_fields_omitted") is True
    assert "vitals" not in bundle.audit


def test_persist_lanes_on_evaluate(tmp_path, monkeypatch):
    db = tmp_path / "lanes.db"
    monkeypatch.setenv("UKZ16_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("UKZ16_USE_SQLITE", "true")
    monkeypatch.setenv("UKZ16_PERSIST_LANES", "true")
    monkeypatch.setenv("UKZ16_PSEUDONYM_PEPPER", "unit-pepper")
    get_settings.cache_clear()
    get_pseudonymizer.cache_clear()
    reset_engine()
    init_db()
    session = next(get_session())
    try:
        svc = EvaluationService(session)
        result = svc.evaluate(make_prmo(encounter_id="LANE-PERS-1"), actor_id="a", actor_role="researcher")
        session.commit()
        lanes = list(session.scalars(select(LaneRecordRow).where(LaneRecordRow.evaluation_id == str(result.evaluation_id))))
        assert {r.lane for r in lanes} == {"raw", "normalized", "research", "audit"}
        research = next(r for r in lanes if r.lane == "research")
        assert research.subject_pseudo_id
        assert research.subject_pseudo_id.startswith("sub_")
    finally:
        session.close()
        get_settings.cache_clear()
        get_pseudonymizer.cache_clear()
        reset_engine()


def test_employer_export_writes_audit(tmp_path, monkeypatch):
    db = tmp_path / "audit.db"
    monkeypatch.setenv("UKZ16_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("UKZ16_USE_SQLITE", "true")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/health-id/employer/export",
        headers={"X-API-Key": "researcher-key"},
    )
    assert resp.status_code == 403
    session = next(get_session())
    try:
        events = list(session.scalars(select(AuditEventRow).where(AuditEventRow.event_type == "employer_export_denied")))
        assert len(events) >= 1
    finally:
        session.close()
        get_settings.cache_clear()
        reset_engine()


def test_bench_report(tmp_path):
    report = run_bench(tmp_path, n=20, seed=1)
    assert report["sla_claim"] is False
    assert report["latency_ms"]["p95"] >= 0
    assert (tmp_path / "bench_report.json").exists()


def test_guidance_builder_codes():
    model = load_model_package("research-v0.2", enforce_signature=False)
    payload = make_prmo(encounter_id="G-1", psychometrics=None)
    quality = run_quality_gates(payload, model)
    result = evaluate_health_id(payload, quality, model)
    g = build_guidance(result)
    assert g.alternative_explanation
    assert "diagnosis" not in (g.suggested_next_step or "").lower()
