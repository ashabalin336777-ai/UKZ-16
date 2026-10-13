from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers import make_prmo
from ukz16.api.main import app
from ukz16.db.models import DriftAlertRow
from ukz16.db.session import get_engine, init_db, reset_engine
from ukz16.domain.contracts import Psychometrics, SocialMetrics
from sqlalchemy.orm import Session


def _client() -> TestClient:
    reset_engine()
    init_db()
    return TestClient(app)


def test_tz14_create_get_trajectory_and_request_id():
    client = _client()
    headers = {"X-API-Key": "researcher-key", "X-Request-Id": "req-123"}
    payload = make_prmo(
        encounter_id="TZ-1",
        psychometrics=Psychometrics(
            instrument="PHQ-9",
            score=1,
            scored_at=datetime(2026, 1, 9, tzinfo=timezone.utc),
            validated=True,
        ),
        social=SocialMetrics(validated=True, engagement_score=0.9),
    ).model_dump(mode="json")
    created = client.post("/api/v1/health-id/evaluations", json=payload, headers=headers)
    assert created.status_code == 200, created.text
    assert created.headers.get("X-Request-Id") == "req-123"
    eid = created.json()["evaluation_id"]

    got = client.get(f"/api/v1/health-id/evaluations/{eid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["evaluation_id"] == eid

    traj = client.get(
        "/api/v1/health-id/subjects/W-1/trajectory",
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        headers=headers,
    )
    assert traj.status_code == 200
    assert len(traj.json()) == 1


def test_idempotency_key_returns_same_evaluation():
    client = _client()
    headers = {
        "X-API-Key": "researcher-key",
        "Idempotency-Key": "idem-1",
    }
    payload = make_prmo(encounter_id="IDEM-1").model_dump(mode="json")
    r1 = client.post("/api/v1/health-id/evaluations", json=payload, headers=headers)
    assert r1.status_code == 200
    # second call with same key must not create duplicate even with new encounter
    payload2 = make_prmo(encounter_id="IDEM-2").model_dump(mode="json")
    r2 = client.post("/api/v1/health-id/evaluations", json=payload2, headers=headers)
    assert r2.status_code == 200
    assert r1.json()["evaluation_id"] == r2.json()["evaluation_id"]


def test_model_card_version_and_validation_metrics():
    client = _client()
    headers = {"X-API-Key": "auditor-key"}
    card = client.get("/api/v1/health-id/model-card/research-v0.2", headers=headers)
    assert card.status_code == 200
    assert card.json()["version"] == "research-v0.2"

    metrics = client.get("/api/v1/health-id/validation/metrics", headers=headers)
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["model_version"] == "research-v0.2"
    assert "metrics" in body
    assert body["drift"]["auto_update"] is False


def test_clinical_review_returns_audit_id():
    client = _client()
    payload = make_prmo(encounter_id="REV-API-1").model_dump(mode="json")
    created = client.post(
        "/api/v1/health-id/evaluations",
        json=payload,
        headers={"X-API-Key": "researcher-key"},
    )
    eid = created.json()["evaluation_id"]
    reviewed = client.post(
        f"/api/v1/health-id/evaluations/{eid}/clinical-review",
        json={"decision": "confirmed", "medical_worker_id": "MW-9", "comment": "ok"},
        headers={"X-API-Key": "medical-key"},
    )
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["review_status"] == "confirmed"
    assert body["audit_id"]
    assert body["evaluation"]["clinical_review"]["status"] == "confirmed"


def test_a16_drift_blocks_evaluation():
    client = _client()
    reset_engine()
    init_db()
    with Session(get_engine()) as session:
        session.add(
            DriftAlertRow(
                id=str(uuid4()),
                alert_type="status_distribution",
                message="forced",
                metrics={"alert": True},
                auto_update=False,
                blocks_evaluation=True,
                resolved=False,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    client = TestClient(app)
    payload = make_prmo(encounter_id="DRIFT-1").model_dump(mode="json")
    blocked = client.post(
        "/api/v1/health-id/evaluations",
        json=payload,
        headers={"X-API-Key": "researcher-key"},
    )
    assert blocked.status_code == 423
    assert "drift_blocks_evaluation" in blocked.json()["detail"]
