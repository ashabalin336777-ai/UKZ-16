"""Synthetic enrichment makes HEALTH_ID calculable without claiming clinical truth."""

from __future__ import annotations

from ukz16.domain.enums import ComponentStatus, HealthIdStatus
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import load_model_package
from ukz16.ingest.customer_csv import map_customer_exam_row
from ukz16.ingest.synthetic_enrichment import enrich_prmo, worker_enrichment_profile
from ukz16.quality.gates import run_quality_gates

SAMPLE = {
    "object_id": "7704153",
    "exam_anon_id": "64477c3c96bdf54b",
    "employee_anon_id": "009b0690f1bf3f1f",
    "exam_dt": "2025-04-07 07:06:14",
    "organization": "Чебоксарский речной порт",
    "terminal": "Терминал 1",
    "exam_type": "Предрейсовый",
    "sbp": "125.0",
    "dbp": "73.0",
    "pulse": "85.0",
    "temperature": "36.3",
    "risk_bucket": "green",
    "result_medic_class": "admitted",
}


def test_enrichment_is_deterministic():
    a = worker_enrichment_profile("W-ENR-01", seed=16)
    b = worker_enrichment_profile("W-ENR-01", seed=16)
    assert a == b
    c = worker_enrichment_profile("W-ENR-02", seed=16)
    assert a.height_cm != c.height_cm or a.site_id != c.site_id or a.phq_base != c.phq_base


def test_enriched_customer_row_health_id_calculable():
    model = load_model_package("research-v0.2", enforce_signature=False)
    base = map_customer_exam_row(SAMPLE)
    payload = enrich_prmo(base, seed=16)
    assert payload.vitals.height_cm is not None
    assert payload.vitals.weight_kg is not None
    assert payload.psychometrics and payload.psychometrics.validated
    assert payload.social_metrics and payload.social_metrics.validated
    quality = run_quality_gates(payload, model)
    assert quality.refuse is False
    result = evaluate_health_id(payload, quality, model)
    assert result.health_id.status == HealthIdStatus.OK
    assert result.health_id.value is not None
    by_name = {c.name: c for c in result.components}
    assert by_name["hBody"].status == ComponentStatus.DERIVED
    assert by_name["hMental"].status == ComponentStatus.DERIVED
    assert by_name["hSocial"].status == ComponentStatus.DERIVED
    assert by_name["bmi"].status == ComponentStatus.DERIVED
    assert result.diagnosis_claim is False
