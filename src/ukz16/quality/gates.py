from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ukz16.domain.contracts import PrMOIngest
from ukz16.domain.enums import QualityStatus
from ukz16.governance.model_registry import ModelPackage


@dataclass
class FieldIssue:
    field: str
    reason: str
    severity: str  # block | warn


@dataclass
class QualityGateResult:
    status: QualityStatus
    issues: list[FieldIssue] = field(default_factory=list)
    field_quality: dict[str, QualityStatus] = field(default_factory=dict)
    blocked_components: list[str] = field(default_factory=list)
    refuse: bool = False
    refuse_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "issues": [{"field": i.field, "reason": i.reason, "severity": i.severity} for i in self.issues],
            "field_quality": {k: v.value for k, v in self.field_quality.items()},
            "blocked_components": self.blocked_components,
            "refuse": self.refuse,
            "refuse_reason": self.refuse_reason,
        }


def run_quality_gates(payload: PrMOIngest, model: ModelPackage) -> QualityGateResult:
    result = QualityGateResult(status=QualityStatus.OK)

    if not payload.consent_research:
        result.status = QualityStatus.REJECT
        result.refuse = True
        result.refuse_reason = "consent_required"
        result.issues.append(FieldIssue("consent_research", "consent_required", "block"))
        return result

    expected_unit = model.config["quality"]["expected_unit_system"]
    if payload.provenance.unit_system != expected_unit:
        result.status = QualityStatus.REJECT
        result.refuse = True
        result.refuse_reason = "unknown_unit"
        result.issues.append(FieldIssue("provenance.unit_system", "unknown_unit", "block"))
        result.blocked_components.extend(["hBody", "hMental", "hSocial"])
        return result

    known = set(model.config["quality"]["known_protocols"])
    protocol_key = payload.protocol_id
    if model.config["quality"].get("reject_unknown_protocol", True) and protocol_key not in known:
        result.status = QualityStatus.REJECT
        result.refuse = True
        result.refuse_reason = "bad_protocol"
        result.issues.append(FieldIssue("protocol_id", "bad_protocol", "block"))
        result.blocked_components.extend(["hBody", "hMental", "hSocial"])
        return result

    thresholds = model.config["thresholds"]
    vitals = payload.vitals.model_dump()
    for field_name, value in vitals.items():
        if value is None:
            continue
        if field_name not in thresholds:
            result.field_quality[field_name] = QualityStatus.OK
            continue
        bounds = thresholds[field_name]
        lo, hi = bounds["hard_min"], bounds["hard_max"]
        if value < lo or value > hi:
            result.field_quality[field_name] = QualityStatus.REJECT
            result.issues.append(FieldIssue(field_name, "out_of_range", "block"))
            if "hBody" not in result.blocked_components:
                result.blocked_components.append("hBody")
            result.status = QualityStatus.DEGRADED
        else:
            result.field_quality[field_name] = QualityStatus.OK

    # Required vitals for scaffold hBody core
    for req in ("bp_systolic_mmhg", "bp_diastolic_mmhg", "pulse_bpm"):
        if vitals.get(req) is None:
            result.field_quality[req] = QualityStatus.REJECT
            result.issues.append(FieldIssue(req, "missing_required", "block"))
            if "hBody" not in result.blocked_components:
                result.blocked_components.append("hBody")
            result.status = QualityStatus.DEGRADED

    if result.issues and result.status == QualityStatus.OK:
        result.status = QualityStatus.DEGRADED

    return result
