"""Customer Drive CSV → PrMOIngest mapping and TZ hard rules for the pilot."""

from __future__ import annotations

from ukz16.domain.enums import ComponentStatus, HealthIdStatus
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import load_model_package
from ukz16.ingest.customer_csv import customer_reference_fields, map_customer_exam_row
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
    "hBody_ID": "90.0",
    "hMental_ID_proxy": "80.0",
    "hSocial_Health_ID_proxy": "100.0",
    "HEALTH_ID": "88.0",
    "risk_bucket": "green",
    "result_medic_class": "admitted",
}


def test_map_customer_exam_row_vitals_only():
    payload = map_customer_exam_row(SAMPLE)
    assert payload.worker_id == "009b0690f1bf3f1f"
    assert payload.encounter_id == "64477c3c96bdf54b"
    assert payload.consent_research is True
    assert payload.protocol_id == "PRMO_RESEARCH_v1"
    assert payload.vitals.bp_systolic_mmhg == 125.0
    assert payload.vitals.bp_diastolic_mmhg == 73.0
    assert payload.vitals.pulse_bpm == 85.0
    assert payload.vitals.temperature_c == 36.3
    assert payload.vitals.height_cm is None
    assert payload.vitals.weight_kg is None
    assert payload.psychometrics is None
    assert payload.social_metrics is None
    assert payload.provenance.unit_system == "SI_medical"


def test_customer_proxies_not_in_payload():
    payload = map_customer_exam_row(SAMPLE)
    dumped = payload.model_dump()
    assert "hBody_ID" not in dumped
    assert "HEALTH_ID" not in dumped
    assert "result_medic_class" not in dumped
    ref = customer_reference_fields(SAMPLE)
    assert ref["result_medic_class"] == "admitted"
    assert ref["HEALTH_ID"] == 88.0


def test_customer_row_health_id_not_calculable_without_mental_social():
    model = load_model_package("research-v0.2", enforce_signature=False)
    payload = map_customer_exam_row(SAMPLE)
    quality = run_quality_gates(payload, model)
    assert quality.refuse is False
    result = evaluate_health_id(payload, quality, model)
    assert result.health_id.status == HealthIdStatus.NOT_CALCULABLE
    assert result.health_id.value is None
    assert result.health_id.reason is not None
    assert "hMental" in result.health_id.reason
    assert "hSocial" in result.health_id.reason
    by_name = {c.name: c for c in result.components}
    assert by_name["hBody"].status == ComponentStatus.DERIVED
    assert by_name["hBody"].value is not None
    assert by_name["bmi"].status == ComponentStatus.MISSING
    assert by_name["bmi"].reason == "missing_height_weight"
    assert by_name["ap_baevsky"].status == ComponentStatus.MISSING
    assert by_name["ap_baevsky"].reason == "missing_height_weight"
    assert result.diagnosis_claim is False
    assert result.employer_export_allowed is False
