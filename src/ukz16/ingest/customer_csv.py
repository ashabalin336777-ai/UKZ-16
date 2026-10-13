"""Map customer Drive CSV rows (health_id_per_exam) → PrMOIngest.

Engineering pilot only. Customer admission / result_medic_class never become
HEALTH_ID outputs. Missing height/weight/psychometrics/social stay missing —
no proxy substitution into the TZ index.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ukz16.domain.contracts import ContextInfo, EmrFlags, PrMOIngest, Provenance, Vitals

DEFAULT_PROTOCOL_ID = "PRMO_RESEARCH_v1"
DEFAULT_PROTOCOL_VERSION = "1.0"
DEFAULT_SOURCE = "CUSTOMER_DRIVE_CSV"


def _opt_float(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_exam_dt(raw: str) -> datetime:
    text = (raw or "").strip()
    if not text:
        raise ValueError("customer_csv_missing_exam_dt")
    # Customer export: "2025-04-07 07:06:14" (naive local). Treat as UTC for research determinism.
    if "T" in text:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    else:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def map_customer_exam_row(
    row: dict[str, Any],
    *,
    consent_research: bool = True,
    protocol_id: str = DEFAULT_PROTOCOL_ID,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
    source_system: str = DEFAULT_SOURCE,
) -> PrMOIngest:
    """Convert one anonymized per-exam CSV row into PrMOIngest."""
    worker_id = str(row.get("employee_anon_id") or "").strip()
    encounter_id = str(row.get("exam_anon_id") or "").strip()
    object_id = str(row.get("object_id") or "").strip()
    if not worker_id or not encounter_id:
        raise ValueError("customer_csv_missing_ids")

    measured_at = _parse_exam_dt(str(row.get("exam_dt") or ""))
    terminal = str(row.get("terminal") or "").strip() or "unknown_terminal"
    organization = str(row.get("organization") or "").strip() or None
    exam_type = str(row.get("exam_type") or "").strip() or None

    input_ids = [f"csv:{encounter_id}"]
    if object_id:
        input_ids.append(f"object:{object_id}")

    return PrMOIngest(
        worker_id=worker_id,
        encounter_id=encounter_id,
        measured_at=measured_at,
        source_system=source_system,
        consent_research=consent_research,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        vitals=Vitals(
            bp_systolic_mmhg=_opt_float(row.get("sbp")),
            bp_diastolic_mmhg=_opt_float(row.get("dbp")),
            pulse_bpm=_opt_float(row.get("pulse")),
            temperature_c=_opt_float(row.get("temperature")),
            # height/weight absent in current Drive extract — BMI/AP stay missing
        ),
        context=ContextInfo(
            site_id=organization,
            shift=exam_type,
        ),
        psychometrics=None,
        social_metrics=None,
        emr_flags=EmrFlags(clinically_confirmed_chronic=False, chronic_condition_codes=[]),
        provenance=Provenance(
            device_id=terminal,
            operator_id=None,
            input_ids=input_ids,
            unit_system="SI_medical",
        ),
        experimental_signals=None,
    )


def customer_reference_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Side-car customer columns for engineering comparison (never model inputs)."""
    return {
        "object_id": str(row.get("object_id") or "").strip() or None,
        "hBody_ID": _opt_float(row.get("hBody_ID")),
        "hMental_ID_proxy": _opt_float(row.get("hMental_ID_proxy")),
        "hSocial_Health_ID_proxy": _opt_float(row.get("hSocial_Health_ID_proxy")),
        "HEALTH_ID": _opt_float(row.get("HEALTH_ID")),
        "HEALTH_ID_blind": _opt_float(row.get("HEALTH_ID_blind")),
        "risk_bucket": str(row.get("risk_bucket") or "").strip() or None,
        "result_medic_class": str(row.get("result_medic_class") or "").strip() or None,
        "measurement_confidence": _opt_float(row.get("measurement_confidence")),
        "history_rows_count": _opt_float(row.get("history_rows_count")),
        "note": "customer proxies are comparison-only; not substituted into UKZ-16 HEALTH_ID",
    }
