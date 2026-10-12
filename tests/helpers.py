from __future__ import annotations

from datetime import datetime, timezone

from ukz16.domain.contracts import (
    EmrFlags,
    PrMOIngest,
    Provenance,
    Psychometrics,
    SocialMetrics,
    Vitals,
)


def make_prmo(
    *,
    worker_id: str = "W-1",
    encounter_id: str = "E-1",
    measured_at: datetime | None = None,
    height_cm: float | None = 175.0,
    weight_kg: float | None = 70.0,
    pulse: float = 70.0,
    sbp: float = 120.0,
    dbp: float = 80.0,
    consent: bool = True,
    protocol_id: str = "PRMO_STD_v1",
    unit_system: str = "SI_medical",
    psychometrics: Psychometrics | None = None,
    social: SocialMetrics | None = None,
    emr: EmrFlags | None = None,
) -> PrMOIngest:
    return PrMOIngest(
        worker_id=worker_id,
        encounter_id=encounter_id,
        measured_at=measured_at or datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc),
        source_system="ECOZ_MOCK",
        consent_research=consent,
        protocol_id=protocol_id,
        protocol_version="1.0",
        vitals=Vitals(
            height_cm=height_cm,
            weight_kg=weight_kg,
            bp_systolic_mmhg=sbp,
            bp_diastolic_mmhg=dbp,
            pulse_bpm=pulse,
        ),
        psychometrics=psychometrics,
        social_metrics=social,
        emr_flags=emr,
        provenance=Provenance(
            device_id="DEV-1",
            operator_id="OP-1",
            input_ids=["in-1"],
            unit_system=unit_system,
        ),
    )
