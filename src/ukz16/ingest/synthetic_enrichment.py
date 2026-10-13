"""Deterministic synthetic fill for missing PrMO fields (research scaffolding).

Used to unblock engineering R2–R4 when customer extract lacks height/weight,
psychometrics, EMR, and multi-site. Never a clinical claim: all generated
fields are marked via source_system / reference.source.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Any

from ukz16.domain.contracts import (
    ContextInfo,
    EmrFlags,
    PrMOIngest,
    Psychometrics,
    SocialMetrics,
    Vitals,
)

SITES = ("SITE-A", "SITE-B", "SITE-C")
INSTRUMENTS = ("PHQ-9", "GAD-7", "WHO-5")


def _stable_u01(*parts: str, seed: int = 16) -> float:
    raw = hashlib.sha256(f"{seed}|{'|'.join(parts)}".encode()).hexdigest()
    return int(raw[:12], 16) / float(0xFFFFFFFFFFFF)


@dataclass(frozen=True)
class WorkerEnrichmentProfile:
    height_cm: float
    weight_kg: float
    age_years: float
    site_id: str
    sex: str
    phq_base: float
    gad_base: float
    who5_base: float
    engagement_base: float
    chronic: bool
    chronic_codes: tuple[str, ...]
    instrument: str


def worker_enrichment_profile(worker_id: str, *, seed: int = 16) -> WorkerEnrichmentProfile:
    """Stable per-worker synthetic anthropometrics / baseline mental-social / site."""
    u0 = _stable_u01(worker_id, "h", seed=seed)
    u1 = _stable_u01(worker_id, "w", seed=seed)
    u2 = _stable_u01(worker_id, "age", seed=seed)
    u3 = _stable_u01(worker_id, "site", seed=seed)
    u4 = _stable_u01(worker_id, "sex", seed=seed)
    u5 = _stable_u01(worker_id, "phq", seed=seed)
    u6 = _stable_u01(worker_id, "eng", seed=seed)
    u7 = _stable_u01(worker_id, "chr", seed=seed)
    u8 = _stable_u01(worker_id, "inst", seed=seed)

    height = round(155.0 + u0 * 35.0, 1)  # 155–190
    # Target BMI ~22–29 with noise
    target_bmi = 22.0 + u1 * 7.0
    h_m = height / 100.0
    weight = round(target_bmi * h_m * h_m, 1)
    age = round(25.0 + u2 * 30.0, 1)  # 25–55
    site = SITES[int(u3 * len(SITES)) % len(SITES)]
    sex = "F" if u4 < 0.5 else "M"
    phq_base = round(u5 * 12.0, 1)  # 0–12 typical
    gad_base = round(_stable_u01(worker_id, "gad", seed=seed) * 10.0, 1)
    who5_base = round(40.0 + _stable_u01(worker_id, "who", seed=seed) * 50.0, 1)
    engagement = round(0.45 + u6 * 0.5, 3)
    chronic = u7 < 0.12
    codes = ("I10",) if chronic and u7 < 0.06 else (("E11",) if chronic else ())
    instrument = INSTRUMENTS[int(u8 * len(INSTRUMENTS)) % len(INSTRUMENTS)]
    return WorkerEnrichmentProfile(
        height_cm=height,
        weight_kg=weight,
        age_years=age,
        site_id=site,
        sex=sex,
        phq_base=phq_base,
        gad_base=gad_base,
        who5_base=who5_base,
        engagement_base=engagement,
        chronic=chronic,
        chronic_codes=codes,
        instrument=instrument,
    )


def _vital_stress(payload: PrMOIngest) -> float:
    """0–1 stress proxy from BP/pulse distance to ref (for synthetic psychometrics)."""
    v = payload.vitals
    parts: list[float] = []
    if v.pulse_bpm is not None:
        parts.append(min(1.0, abs(v.pulse_bpm - 70.0) / 40.0))
    if v.bp_systolic_mmhg is not None:
        parts.append(min(1.0, abs(v.bp_systolic_mmhg - 120.0) / 40.0))
    if v.bp_diastolic_mmhg is not None:
        parts.append(min(1.0, abs(v.bp_diastolic_mmhg - 80.0) / 20.0))
    return sum(parts) / len(parts) if parts else 0.3


def _instrument_score(profile: WorkerEnrichmentProfile, stress: float, encounter_id: str, seed: int) -> float:
    noise = (_stable_u01(encounter_id, "psy_noise", seed=seed) - 0.5) * 2.0
    if profile.instrument == "PHQ-9":
        return float(max(0, min(27, round(profile.phq_base + stress * 8.0 + noise, 1))))
    if profile.instrument == "GAD-7":
        return float(max(0, min(21, round(profile.gad_base + stress * 6.0 + noise, 1))))
    # WHO-5 higher_better: stress lowers score
    return float(max(0, min(100, round(profile.who5_base - stress * 25.0 + noise * 3.0, 1))))


def enrich_prmo(
    payload: PrMOIngest,
    *,
    seed: int = 16,
    profile: WorkerEnrichmentProfile | None = None,
    source_system: str = "CUSTOMER_DRIVE_CSV+SYNTHETIC_ENRICH_v1",
) -> PrMOIngest:
    """Fill missing anthropometrics / psychometrics / social / EMR / site deterministically."""
    prof = profile or worker_enrichment_profile(payload.worker_id, seed=seed)
    stress = _vital_stress(payload)
    score = _instrument_score(prof, stress, payload.encounter_id, seed)
    # scored_at slightly before measured_at (same day)
    scored_at = payload.measured_at - timedelta(hours=1)
    if scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=timezone.utc)

    eng = round(max(0.05, min(1.0, prof.engagement_base - stress * 0.25)), 3)
    vitals = payload.vitals.model_copy(
        update={
            "height_cm": payload.vitals.height_cm if payload.vitals.height_cm is not None else prof.height_cm,
            "weight_kg": payload.vitals.weight_kg if payload.vitals.weight_kg is not None else prof.weight_kg,
        }
    )
    ctx = payload.context or ContextInfo()
    context = ctx.model_copy(
        update={
            "site_id": ctx.site_id if ctx.site_id and ctx.site_id.startswith("SITE-") else prof.site_id,
            "age_years": ctx.age_years if ctx.age_years is not None else prof.age_years,
        }
    )
    return payload.model_copy(
        update={
            "source_system": source_system,
            "vitals": vitals,
            "context": context,
            "psychometrics": Psychometrics(
                instrument=prof.instrument,
                score=score,
                scored_at=scored_at,
                validated=True,
            ),
            "social_metrics": SocialMetrics(
                validated=True,
                engagement_score=eng,
                attendance_rate=None,
                notes="synthetic_enrichment_v1",
            ),
            "emr_flags": EmrFlags(
                clinically_confirmed_chronic=prof.chronic,
                chronic_condition_codes=list(prof.chronic_codes),
            ),
        }
    )


def synthetic_reference_label(row: dict[str, Any], payload: PrMOIngest) -> tuple[int, str]:
    """Independent binary label for R2 (not derived from UKZ HEALTH_ID value)."""
    risk = str(row.get("risk_bucket") or "").strip().lower()
    medic = str(row.get("result_medic_class") or "").strip().lower()
    if risk == "yellow" or medic.startswith("not_admitted"):
        return 1, "customer_risk_or_non_admission_v1"
    v = payload.vitals
    if v.bp_systolic_mmhg is not None and v.bp_systolic_mmhg >= 150:
        return 1, "synthetic_sbp_ge_150_v1"
    if v.pulse_bpm is not None and v.pulse_bpm >= 110:
        return 1, "synthetic_pulse_ge_110_v1"
    return 0, "customer_risk_or_non_admission_v1"


def remap_worker_id(employee_anon_id: str, index: int) -> str:
    """Stable public-ish remapped id for committed samples."""
    return f"W-ENR-{index:02d}"
