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


def _missing_component(
    name: str,
    weight: float,
    reason: str,
    formula_id: str,
    *,
    quality: QualityStatus | None = None,
) -> tuple[ComponentResult, list[dict[str, Any]]]:
    return (
        ComponentResult(
            name=name,
            status=ComponentStatus.MISSING,
            value=None,
            weight=weight,
            contribution=None,
            inputs=[],
            quality=quality,
            reason=reason,
            formula_id=formula_id,
        ),
        [{"component": name, "status": "missing", "reason": reason}],
    )


def _compute_hbody(
    payload: PrMOIngest,
    model: ModelPackage,
    quality: QualityGateResult,
) -> tuple[ComponentResult, list[dict[str, Any]]]:
    weights = model.config["weights"]
    cfg = model.config["components"]["hBody"]
    scoring = model.config["scoring"]
    w = float(weights["hBody"])

    if "hBody" in quality.blocked_components:
        return _missing_component(
            "hBody",
            w,
            "quality_blocked",
            cfg["formula_id"],
            quality=QualityStatus.REJECT,
        )

    v = payload.vitals
    if v.bp_systolic_mmhg is None or v.bp_diastolic_mmhg is None or v.pulse_bpm is None:
        return _missing_component(
            "hBody",
            w,
            "missing_core_vitals",
            cfg["formula_id"],
            quality=QualityStatus.REJECT,
        )

    pulse_s = _vital_score(v.pulse_bpm, scoring["pulse_ref_bpm"], scoring["pulse_span"])
    sbp_s = _vital_score(v.bp_systolic_mmhg, scoring["sbp_ref_mmhg"], scoring["sbp_span"])
    dbp_s = _vital_score(v.bp_diastolic_mmhg, scoring["dbp_ref_mmhg"], scoring["dbp_span"])
    value = round((pulse_s + sbp_s + dbp_s) / 3.0, 6)
    trace = [
        {
            "component": "hBody",
            "status": "derived",
            "pulse_score": round(pulse_s, 6),
            "sbp_score": round(sbp_s, 6),
            "dbp_score": round(dbp_s, 6),
            "bmi_excluded": True,
        }
    ]
    return (
        ComponentResult(
            name="hBody",
            status=ComponentStatus.DERIVED,
            value=value,
            weight=w,
            contribution=round(value * w, 6),
            inputs=["bp_systolic_mmhg", "bp_diastolic_mmhg", "pulse_bpm"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        trace,
    )


def _compute_hmental(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    w = float(model.config["weights"]["hMental"])
    cfg = model.config["components"]["hMental"]
    psy = payload.psychometrics
    if not psy or not psy.validated or psy.score is None:
        return _missing_component("hMental", w, "no_validated_psychometrics", cfg["formula_id"])
    # Scaffold: assume instrument scores 0..27 (PHQ-9-like) -> invert to 0..1 wellness
    value = round(_clamp01(1.0 - float(psy.score) / 27.0), 6)
    return (
        ComponentResult(
            name="hMental",
            status=ComponentStatus.DERIVED,
            value=value,
            weight=w,
            contribution=round(value * w, 6),
            inputs=["psychometrics.score", "psychometrics.instrument"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "hMental", "status": "derived", "score": psy.score, "value": value}],
    )


def _compute_hsocial(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    w = float(model.config["weights"]["hSocial"])
    cfg = model.config["components"]["hSocial"]
    sm = payload.social_metrics
    if not sm or not sm.validated or sm.engagement_score is None:
        reason = "no_validated_social_metrics" if not sm or not sm.validated else "attendance_not_motivation"
        return _missing_component("hSocial", w, reason, cfg["formula_id"])
    value = round(_clamp01(float(sm.engagement_score)), 6)
    return (
        ComponentResult(
            name="hSocial",
            status=ComponentStatus.DERIVED,
            value=value,
            weight=w,
            contribution=round(value * w, 6),
            inputs=["social_metrics.engagement_score"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "hSocial", "status": "derived", "value": value}],
    )


def _compute_svs_experimental() -> tuple[ComponentResult, list[dict[str, Any]]]:
    """SVS is experimental and never substitutes hMental (TZ §5 / A16-03)."""
    return (
        ComponentResult(
            name="SVS",
            status=ComponentStatus.EXPERIMENTAL,
            value=None,
            weight=0.0,
            contribution=None,
            inputs=[],
            quality=None,
            reason="experimental_not_in_phase1",
            formula_id="svs_experimental_placeholder",
        ),
        [
            {
                "component": "SVS",
                "status": "experimental",
                "diagnostic_value": False,
                "enters_hMental": False,
                "enters_health_id": False,
            }
        ],
    )


def _compute_bmi(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    cfg = model.config["indicators"]["bmi"]
    value = _bmi(payload.vitals.height_cm, payload.vitals.weight_kg)
    if value is None:
        return _missing_component("bmi", 0.0, cfg["missing_reason"], cfg["formula_id"])
    rounded = round(value, 4)
    return (
        ComponentResult(
            name="bmi",
            status=ComponentStatus.DERIVED,
            value=rounded,
            weight=0.0,
            contribution=None,
            inputs=["height_cm", "weight_kg"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "bmi", "status": "derived", "value": rounded, "enters_health_id": False}],
    )


def _compute_ap(payload: PrMOIngest, model: ModelPackage) -> tuple[ComponentResult, list[dict[str, Any]]]:
    cfg = model.config["indicators"]["ap_baevsky"]
    v = payload.vitals
    if v.height_cm is None or v.weight_kg is None:
        return _missing_component("ap_baevsky", 0.0, cfg["missing_height_weight_reason"], cfg["formula_id"])
    age = payload.context.age_years if payload.context else None
    if age is None or v.pulse_bpm is None or v.bp_systolic_mmhg is None or v.bp_diastolic_mmhg is None:
        return _missing_component("ap_baevsky", 0.0, "missing_age_or_vitals", cfg["formula_id"])
    coef = cfg["coefficients"]
    raw = (
        coef["pulse"] * v.pulse_bpm
        + coef["sbp"] * v.bp_systolic_mmhg
        + coef["dbp"] * v.bp_diastolic_mmhg
        + coef["age"] * age
        + coef["weight"] * v.weight_kg
        - coef["height"] * v.height_cm
        + coef["intercept"]
    )
    value = round(raw, 6)
    return (
        ComponentResult(
            name="ap_baevsky",
            status=ComponentStatus.DERIVED,
            value=value,
            weight=0.0,
            contribution=None,
            inputs=["pulse_bpm", "bp_systolic_mmhg", "bp_diastolic_mmhg", "age_years", "weight_kg", "height_cm"],
            quality=QualityStatus.OK,
            reason=None,
            formula_id=cfg["formula_id"],
        ),
        [{"component": "ap_baevsky", "status": "derived", "value": value, "thresholds_applied": False, "enters_health_id": False}],
    )


_INDEX_COMPONENTS = ("hBody", "hMental", "hSocial")


def _aggregate(components: list[ComponentResult], model: ModelPackage) -> HealthIdValue:
    """Exact weighted sum. Missing index components refuse the total. No renormalization."""
    version = model.version
    index = [c for c in components if c.name in _INDEX_COMPONENTS]
    missing = [c.name for c in index if c.status != ComponentStatus.DERIVED or c.value is None]
    if missing:
        return HealthIdValue(
            value=None,
            version=version,
            status=HealthIdStatus.NOT_CALCULABLE,
            reason="insufficient_components:" + ",".join(missing),
        )
    raw = sum((c.value or 0.0) * c.weight for c in index)
    return HealthIdValue(value=round(raw, 6), version=version, status=HealthIdStatus.OK, reason=None)


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
    bmi, t_bmi = _compute_bmi(payload, model)
    ap, t_ap = _compute_ap(payload, model)
    svs, t_svs = _compute_svs_experimental()
    components = [hbody, hmental, hsocial, bmi, ap, svs]
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
    trace = t1 + t2 + t3 + t_bmi + t_ap + t_svs
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
