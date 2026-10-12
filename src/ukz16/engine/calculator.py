from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from ukz16.classify.state import classify_state
from ukz16.corridors.baseline import PriorPoint, compute_personal_corridor
from ukz16.domain.contracts import (
    ChronicFromEmr,
    ClinicalReview,
    Completeness,
    ComponentResult,
    EvaluationResult,
    Evidence,
    HealthIdValue,
    PersistenceInfo,
    PrMOIngest,
    Uncertainty,
)
from ukz16.domain.enums import ComponentStatus, HealthIdStatus, QualityStatus
from ukz16.governance.model_registry import ModelPackage, stable_input_hash
from ukz16.quality.gates import QualityGateResult


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _vital_score(value: float, ref: float, span: float) -> float:
    return _clamp01(1.0 - abs(value - ref) / span)


def _bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if height_cm is None or weight_kg is None or height_cm <= 0:
        return None
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def _completeness(payload: PrMOIngest) -> Completeness:
    required = [
        "bp_systolic_mmhg",
        "bp_diastolic_mmhg",
        "pulse_bpm",
        "height_cm",
        "weight_kg",
        "psychometrics.validated",
        "social_metrics.validated",
    ]
    present: list[str] = []
    missing: list[str] = []
    vitals = payload.vitals.model_dump()
    for key in ("bp_systolic_mmhg", "bp_diastolic_mmhg", "pulse_bpm", "height_cm", "weight_kg"):
        if vitals.get(key) is not None:
            present.append(key)
        else:
            missing.append(key)
    if payload.psychometrics and payload.psychometrics.validated and payload.psychometrics.score is not None:
        present.append("psychometrics.validated")
    else:
        missing.append("psychometrics.validated")
    if payload.social_metrics and payload.social_metrics.validated:
        present.append("social_metrics.validated")
    else:
        missing.append("social_metrics.validated")
    ratio = len(present) / len(required) if required else 0.0
    return Completeness(required_fields_present=round(ratio, 4), missing=missing, present=present)


def _population_flags(payload: PrMOIngest, normals: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    pop = normals.get("population", {})
    v = payload.vitals
    checks = [
        ("pulse_bpm", v.pulse_bpm),
        ("bp_systolic_mmhg", v.bp_systolic_mmhg),
        ("bp_diastolic_mmhg", v.bp_diastolic_mmhg),
    ]
    for name, value in checks:
        if value is None or name not in pop:
            continue
        band = pop[name]
        if value < band["low"] or value > band["high"]:
            flags.append(f"population_{name}")
    bmi = _bmi(v.height_cm, v.weight_kg)
    if bmi is not None and "bmi" in pop:
        band = pop["bmi"]
        if bmi < band["low"] or bmi > band["high"]:
            flags.append("population_bmi")
    return flags


def _compute_hbody(
    payload: PrMOIngest,
    model: ModelPackage,
    quality: QualityGateResult,
) -> tuple[ComponentResult, list[dict[str, Any]]]:
    weights = model.config["weights"]
    cfg = model.config["components"]["hBody"]
    scoring = model.config["scoring"]
    trace: list[dict[str, Any]] = []
    w = float(weights["hBody"])

    if "hBody" in quality.blocked_components:
        return (
            ComponentResult(
                name="hBody",
                status=ComponentStatus.BLOCKED,
                value=None,
                weight=w,
                contribution=None,
                inputs=[],
                quality=QualityStatus.REJECT,
                reason="quality_blocked",
                formula_id=cfg["formula_id"],
            ),
            [{"component": "hBody", "step": "blocked", "reason": "quality_blocked"}],
        )

    v = payload.vitals
    if v.bp_systolic_mmhg is None or v.bp_diastolic_mmhg is None or v.pulse_bpm is None:
        return (
            ComponentResult(
                name="hBody",
                status=ComponentStatus.NOT_CALCULABLE,
                value=None,
                weight=w,
                contribution=None,
                inputs=[],
                quality=QualityStatus.REJECT,
                reason="missing_core_vitals",
                formula_id=cfg["formula_id"],
            ),
            [{"component": "hBody", "step": "missing_core_vitals"}],
        )

    pulse_s = _vital_score(v.pulse_bpm, scoring["pulse_ref_bpm"], scoring["pulse_span"])
    sbp_s = _vital_score(v.bp_systolic_mmhg, scoring["sbp_ref_mmhg"], scoring["sbp_span"])
    dbp_s = _vital_score(v.bp_diastolic_mmhg, scoring["dbp_ref_mmhg"], scoring["dbp_span"])
    parts = [pulse_s, sbp_s, dbp_s]
    inputs = ["bp_systolic_mmhg", "bp_diastolic_mmhg", "pulse_bpm"]
    trace.append(
        {
            "component": "hBody",
            "pulse_score": round(pulse_s, 6),
            "sbp_score": round(sbp_s, 6),
            "dbp_score": round(dbp_s, 6),
        }
    )

    bmi = _bmi(v.height_cm, v.weight_kg)
    status = ComponentStatus.OK
    reason = None
    if bmi is None:
        status = ComponentStatus.PARTIAL
        reason = "missing_height_weight"
        trace.append({"component": "hBody", "bmi": None, "reason": "missing_height_weight"})
    else:
        # map BMI distance from 22 into 0..1 scaffold
        bmi_s = _clamp01(1.0 - abs(bmi - 22.0) / 10.0)
        parts.append(bmi_s)
        inputs.extend(["height_cm", "weight_kg"])
        trace.append({"component": "hBody", "bmi": round(bmi, 4), "bmi_score": round(bmi_s, 6)})

    value = round(sum(parts) / len(parts), 6)
    contribution = round(value * w, 6)
    return (
        ComponentResult(
            name="hBody",
            status=status,
            value=value,
            weight=w,
            contribution=contribution,
            inputs=inputs,
            quality=QualityStatus.OK,
            reason=reason,
            formula_id=cfg["formula_id"],
        ),
        trace,
    )


def _compute_hmental(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    w = float(model.config["weights"]["hMental"])
    cfg = model.config["components"]["hMental"]
    psy = payload.psychometrics
    if not psy or not psy.validated or psy.score is None:
        return (
            ComponentResult(
                name="hMental",
                status=ComponentStatus.NOT_CALCULABLE,
                value=None,
                weight=w,
                contribution=None,
                inputs=[],
                quality=None,
                reason="no_validated_psychometrics",
                formula_id=cfg["formula_id"],
            ),
            [{"component": "hMental", "reason": "no_validated_psychometrics"}],
        )
    # Scaffold: assume instrument scores 0..27 (PHQ-9-like) -> invert to 0..1 wellness
    value = round(_clamp01(1.0 - float(psy.score) / 27.0), 6)
    return (
        ComponentResult(
            name="hMental",
            status=ComponentStatus.OK,
            value=value,
            weight=w,
            contribution=round(value * w, 6),
            inputs=["psychometrics.score", "psychometrics.instrument"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "hMental", "score": psy.score, "value": value}],
    )


def _compute_hsocial(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    w = float(model.config["weights"]["hSocial"])
    cfg = model.config["components"]["hSocial"]
    sm = payload.social_metrics
    if not sm or not sm.validated:
        return (
            ComponentResult(
                name="hSocial",
                status=ComponentStatus.NOT_CALCULABLE,
                value=None,
                weight=w,
                contribution=None,
                inputs=[],
                quality=None,
                reason="no_validated_social_metrics",
                formula_id=cfg["formula_id"],
            ),
            [{"component": "hSocial", "reason": "no_validated_social_metrics"}],
        )
    # Attendance is NOT motivation — only use engagement_score if present
    if sm.engagement_score is None:
        return (
            ComponentResult(
                name="hSocial",
                status=ComponentStatus.NOT_CALCULABLE,
                value=None,
                weight=w,
                contribution=None,
                inputs=["social_metrics.validated"],
                quality=None,
                reason="no_validated_social_metrics",
                formula_id=cfg["formula_id"],
            ),
            [{"component": "hSocial", "reason": "attendance_not_motivation"}],
        )
    value = round(_clamp01(float(sm.engagement_score)), 6)
    return (
        ComponentResult(
            name="hSocial",
            status=ComponentStatus.OK,
            value=value,
            weight=w,
            contribution=round(value * w, 6),
            inputs=["social_metrics.engagement_score"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "hSocial", "value": value}],
    )


def _aggregate(
    components: list[ComponentResult],
    model: ModelPackage,
) -> HealthIdValue:
    policies = model.config["policies"]
    version = model.version
    usable = [c for c in components if c.value is not None and c.status in (ComponentStatus.OK, ComponentStatus.PARTIAL)]
    if not usable:
        return HealthIdValue(
            value=None,
            version=version,
            status=HealthIdStatus.NOT_CALCULABLE,
            reason="no_calculable_components",
        )

    weight_sum = sum(c.weight for c in usable)
    if not policies.get("allow_weighted_partial", True):
        if any(c.status != ComponentStatus.OK for c in components) or len(usable) < 3:
            return HealthIdValue(
                value=None,
                version=version,
                status=HealthIdStatus.NOT_CALCULABLE,
                reason="partial_not_allowed",
            )

    min_w = float(policies.get("min_weight_for_partial", 0.6))
    if weight_sum < min_w:
        return HealthIdValue(
            value=None,
            version=version,
            status=HealthIdStatus.NOT_CALCULABLE,
            reason="insufficient_component_weight",
        )

    # Renormalize over available weights (explicit partial policy — not hidden imputation of missing comps)
    raw = sum((c.value or 0.0) * c.weight for c in usable) / weight_sum
    value = round(raw, 6)
    status = HealthIdStatus.OK if len(usable) == 3 and all(c.status == ComponentStatus.OK for c in usable) else HealthIdStatus.PARTIAL
    reason = None if status == HealthIdStatus.OK else "weighted_partial"
    return HealthIdValue(value=value, version=version, status=status, reason=reason)


def evaluate_health_id(
    payload: PrMOIngest,
    quality: QualityGateResult,
    model: ModelPackage,
    *,
    prior_points: list[PriorPoint] | None = None,
    prior_deviation_dates: list[str] | None = None,
    evaluation_id: UUID | None = None,
) -> EvaluationResult:
    """Deterministic HEALTH_ID evaluation with full explanation contract."""
    if quality.refuse:
        eid = evaluation_id or uuid4()
        input_hash = stable_input_hash(payload.model_dump(mode="json"), model.version)
        return EvaluationResult(
            evaluation_id=eid,
            worker_id=payload.worker_id,
            encounter_id=payload.encounter_id,
            measured_at=payload.measured_at,
            health_id=HealthIdValue(
                value=None,
                version=model.version,
                status=HealthIdStatus.NOT_CALCULABLE,
                reason=quality.refuse_reason,
            ),
            components=[],
            completeness=_completeness(payload),
            uncertainty=Uncertainty(method="not_available_due_to_refusal", score=None, notes=quality.refuse_reason),
            acute_state=None,
            personal_deviation=None,
            persistence=PersistenceInfo(),
            chronic_from_emr=ChronicFromEmr(
                clinically_confirmed=bool(payload.emr_flags and payload.emr_flags.clinically_confirmed_chronic),
                codes=list(payload.emr_flags.chronic_condition_codes) if payload.emr_flags else [],
            ),
            evidence=Evidence(
                input_ids=list(payload.provenance.input_ids),
                quality=quality.to_dict(),
                formula_ids=[],
                normals_version=str(model.normals.get("version")),
                contribution_trace=[{"step": "safe_refusal", "reason": quality.refuse_reason}],
                input_hash=input_hash,
                model_version=model.version,
                model_package_hash=model.package_hash,
            ),
            clinical_review=ClinicalReview(status="pending"),
        )

    hbody, t1 = _compute_hbody(payload, model, quality)
    hmental, t2 = _compute_hmental(payload, model)
    hsocial, t3 = _compute_hsocial(payload, model)
    components = [hbody, hmental, hsocial]
    health = _aggregate(components, model)

    # Corridor on hBody value when available
    current_date = payload.measured_at.date().isoformat()
    corridor_cfg = model.config["corridor"]
    personal = compute_personal_corridor(
        prior_points or [],
        hbody.value,
        current_date,
        min_prior_unique_dates=int(corridor_cfg["min_prior_unique_dates"]),
        acute_z=float(model.config["thresholds"]["acute_z"]),
        mad_floor=float(corridor_cfg["mad_floor"]),
        exclude_current=bool(model.config["policies"]["baseline_exclude_current"]),
    )
    pop_flags = _population_flags(payload, model.normals)
    acute, deviation, persistence, chronic_emr = classify_state(
        personal=personal,
        prior_deviation_dates=prior_deviation_dates or [],
        current_date=current_date,
        current_outside=bool(personal.get("outside_corridor")),
        persistence_threshold=int(model.config["thresholds"]["persistence_unique_dates"]),
        emr_flags=payload.emr_flags,
        population_flags=pop_flags,
    )
    # Attach chronic evidence into acute flags for visibility (not a diagnosis)
    if chronic_emr:
        acute.flags = list(acute.flags) + ["clinically_confirmed_chronic_from_emr"]

    chronic = ChronicFromEmr(
        clinically_confirmed=chronic_emr,
        codes=list(payload.emr_flags.chronic_condition_codes) if payload.emr_flags else [],
    )

    completeness = _completeness(payload)
    unc_score = round(1.0 - completeness.required_fields_present, 4)
    uncertainty = Uncertainty(
        method="completeness_complement",
        score=unc_score,
        notes="Higher score = more missing required fields; no conformal intervals in v0.1",
    )

    input_hash = stable_input_hash(payload.model_dump(mode="json"), model.version)
    trace = t1 + t2 + t3
    if chronic_emr:
        trace.append({"chronic_from_emr": True, "codes": (payload.emr_flags.chronic_condition_codes if payload.emr_flags else [])})

    # Recompute contributions after possible status
    for c in components:
        if c.value is not None:
            c.contribution = round(c.value * c.weight, 6)

    return EvaluationResult(
        evaluation_id=evaluation_id or uuid4(),
        worker_id=payload.worker_id,
        encounter_id=payload.encounter_id,
        measured_at=payload.measured_at,
        health_id=health,
        components=components,
        completeness=completeness,
        uncertainty=uncertainty,
        acute_state=acute,
        personal_deviation=deviation,
        persistence=persistence,
        chronic_from_emr=chronic,
        evidence=Evidence(
            input_ids=list(payload.provenance.input_ids),
            quality=quality.to_dict(),
            formula_ids=[c.formula_id for c in components if c.formula_id],
            normals_version=str(model.normals.get("version")),
            contribution_trace=trace,
            input_hash=input_hash,
            model_version=model.version,
            model_package_hash=model.package_hash,
        ),
        clinical_review=ClinicalReview(status="pending"),
    )
