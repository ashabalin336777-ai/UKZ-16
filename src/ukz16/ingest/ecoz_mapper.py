from __future__ import annotations

from datetime import datetime
from typing import Any

from ukz16.domain.contracts import (
    ContextInfo,
    EmrFlags,
    PrMOIngest,
    Provenance,
    Psychometrics,
    SocialMetrics,
    Vitals,
)


def map_ecoz_encounter(payload: dict[str, Any]) -> PrMOIngest:
    """Map ECOZ/MIS encounter JSON (research contract) to PrMOIngest.

    Expected shape (minimal):
    {
      "subject_pseudonym": "...",
      "event_id": "...",
      "measured_at": "...",
      "source_system": "ECOZ",
      "consent": {"research": true, "type": "...", "version": "..."},
      "protocol": {"id": "PRMO_STD_v1", "version": "1.0"},
      "device": {"id": "..."},
      "observations": [{"metric_code": "pulse_bpm", "value": 70, "unit": "bpm", ...}],
      "context": {...},
      "psychometrics": {...},
      "social_metrics": {...},
      "emr_flags": {...}
    }
    """
    if "worker_id" in payload and "vitals" in payload:
        # Already in internal shape
        return PrMOIngest.model_validate(payload)

    observations = payload.get("observations") or []
    by_code: dict[str, Any] = {}
    input_ids: list[str] = []
    for obs in observations:
        code = obs.get("metric_code") or obs.get("code")
        if not code:
            continue
        by_code[str(code)] = obs
        if obs.get("input_id"):
            input_ids.append(str(obs["input_id"]))
        elif obs.get("id"):
            input_ids.append(str(obs["id"]))

    def _num(code: str) -> float | None:
        obs = by_code.get(code)
        if not obs:
            return None
        value = obs.get("value")
        return float(value) if value is not None else None

    consent = payload.get("consent") or {}
    protocol = payload.get("protocol") or {}
    device = payload.get("device") or {}
    context = payload.get("context") or {}
    psy = payload.get("psychometrics")
    social = payload.get("social_metrics")
    emr = payload.get("emr_flags")

    measured_at = payload.get("measured_at") or payload.get("event_time")
    if isinstance(measured_at, str):
        measured_dt = datetime.fromisoformat(measured_at.replace("Z", "+00:00"))
    elif isinstance(measured_at, datetime):
        measured_dt = measured_at
    else:
        raise ValueError("ecoz_missing_measured_at")

    unit_system = payload.get("unit_system") or "SI_medical"
    # Unknown units on any observation block via unit_system override
    for obs in observations:
        unit = (obs.get("unit") or "").lower()
        # Research whitelist: if unit present and not in known set, mark non-SI
        if unit and unit not in {"bpm", "mmhg", "cm", "kg", "c", "celsius", "%", "pct", ""}:
            unit_system = "unknown"

    return PrMOIngest(
        worker_id=str(payload.get("subject_pseudonym") or payload.get("worker_id")),
        encounter_id=str(payload.get("event_id") or payload.get("encounter_id")),
        measured_at=measured_dt,
        source_system=str(payload.get("source_system") or "ECOZ"),
        consent_research=bool(consent.get("research", consent.get("consent_research", False))),
        protocol_id=str(protocol.get("id") or payload.get("protocol_id") or ""),
        protocol_version=str(protocol.get("version") or payload.get("protocol_version") or "1.0"),
        vitals=Vitals(
            height_cm=_num("height_cm"),
            weight_kg=_num("weight_kg"),
            bp_systolic_mmhg=_num("bp_systolic_mmhg"),
            bp_diastolic_mmhg=_num("bp_diastolic_mmhg"),
            pulse_bpm=_num("pulse_bpm"),
            temperature_c=_num("temperature_c"),
            spo2_pct=_num("spo2_pct"),
        ),
        context=ContextInfo(
            site_id=context.get("site_id"),
            shift=context.get("shift"),
            posture=context.get("posture"),
            age_years=float(context["age_years"]) if context.get("age_years") is not None else None,
        )
        if context
        else None,
        psychometrics=Psychometrics.model_validate(psy) if psy else None,
        social_metrics=SocialMetrics.model_validate(social) if social else None,
        emr_flags=EmrFlags.model_validate(emr) if emr else None,
        provenance=Provenance(
            device_id=str(device.get("id") or payload.get("device_id") or "ECOZ_UNKNOWN"),
            operator_id=(payload.get("operator") or {}).get("id") if isinstance(payload.get("operator"), dict) else payload.get("operator_id"),
            input_ids=input_ids,
            unit_system=unit_system,
        ),
    )
