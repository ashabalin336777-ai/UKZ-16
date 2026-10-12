from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from ukz16.domain.enums import ComponentStatus, HealthIdStatus, QualityStatus


class Vitals(BaseModel):
    height_cm: float | None = None
    weight_kg: float | None = None
    bp_systolic_mmhg: float | None = None
    bp_diastolic_mmhg: float | None = None
    pulse_bpm: float | None = None
    temperature_c: float | None = None
    spo2_pct: float | None = None


class Psychometrics(BaseModel):
    instrument: str | None = None
    score: float | None = None
    scored_at: datetime | None = None
    validated: bool = False


class SocialMetrics(BaseModel):
    validated: bool = False
    attendance_rate: float | None = None
    engagement_score: float | None = None
    notes: str | None = None


class EmrFlags(BaseModel):
    clinically_confirmed_chronic: bool = False
    chronic_condition_codes: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    device_id: str
    operator_id: str | None = None
    input_ids: list[str] = Field(default_factory=list)
    unit_system: str = "SI_medical"


class ContextInfo(BaseModel):
    site_id: str | None = None
    shift: str | None = None
    posture: str | None = None


class PrMOIngest(BaseModel):
    worker_id: str
    encounter_id: str
    measured_at: datetime
    source_system: str = "ECOZ_MOCK"
    consent_research: bool
    protocol_id: str
    protocol_version: str
    vitals: Vitals
    context: ContextInfo | None = None
    psychometrics: Psychometrics | None = None
    social_metrics: SocialMetrics | None = None
    emr_flags: EmrFlags | None = None
    provenance: Provenance


class HealthIdValue(BaseModel):
    value: float | None
    version: str
    status: HealthIdStatus
    reason: str | None = None


class ComponentResult(BaseModel):
    name: str
    status: ComponentStatus
    value: float | None = None
    weight: float
    contribution: float | None = None
    inputs: list[str] = Field(default_factory=list)
    quality: QualityStatus | None = None
    reason: str | None = None
    formula_id: str | None = None


class Completeness(BaseModel):
    required_fields_present: float
    missing: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)


class Uncertainty(BaseModel):
    method: str
    score: float | None = None
    notes: str | None = None


class AcuteState(BaseModel):
    is_acute: bool
    flags: list[str] = Field(default_factory=list)
    method: str | None = None


class ChronicFromEmr(BaseModel):
    clinically_confirmed: bool = False
    codes: list[str] = Field(default_factory=list)
    source: Literal["emr_only"] = "emr_only"
    inferred_from_persistence: Literal[False] = False


class PersonalDeviation(BaseModel):
    outside_corridor: bool
    z_score: float | None = None
    corridor_low: float | None = None
    corridor_high: float | None = None
    baseline_n_unique_dates: int = 0
    method: str | None = None
    reason: str | None = None


class PersistenceInfo(BaseModel):
    unique_dates_with_deviation: int = 0
    unique_dates_rule: str = "prior_quality_dates_only"
    same_day_attempts_do_not_increase_persistence: bool = True
    is_persistent: bool = False
    dates: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    input_ids: list[str] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    formula_ids: list[str] = Field(default_factory=list)
    normals_version: str | None = None
    contribution_trace: list[dict[str, Any]] = Field(default_factory=list)
    input_hash: str
    model_version: str
    model_package_hash: str | None = None


ClinicalReviewStatus = Literal["pending", "confirmed", "rejected"]


class ClinicalReview(BaseModel):
    status: ClinicalReviewStatus = "pending"
    medical_worker_id: str | None = None
    comment: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    signed_at: datetime | None = None
    signature_ref: str | None = None  # TODO: 63-FZ electronic signature


class EvaluationResult(BaseModel):
    evaluation_id: UUID
    worker_id: str
    encounter_id: str
    measured_at: datetime
    health_id: HealthIdValue
    components: list[ComponentResult]
    completeness: Completeness
    uncertainty: Uncertainty
    acute_state: AcuteState | None
    personal_deviation: PersonalDeviation | None
    persistence: PersistenceInfo
    chronic_from_emr: ChronicFromEmr = Field(default_factory=ChronicFromEmr)
    evidence: Evidence
    clinical_review: ClinicalReview
    diagnosis_claim: Literal[False] = False
    employer_export_allowed: Literal[False] = False


class ReviewDecisionRequest(BaseModel):
    decision: ClinicalReviewStatus
    medical_worker_id: str
    comment: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    signature_ref: str | None = None
