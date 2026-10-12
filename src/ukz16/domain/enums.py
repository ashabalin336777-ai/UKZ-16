from enum import StrEnum


class Role(StrEnum):
    RESEARCHER = "researcher"
    MEDICAL_WORKER = "medical_worker"
    AUDITOR = "auditor"


class QualityStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    REJECT = "reject"


class ComponentStatus(StrEnum):
    """TZ §12 vocabulary for components[].status."""

    MEASURED = "measured"
    DERIVED = "derived"
    EXPERIMENTAL = "experimental"
    MISSING = "missing"


class HealthIdStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    NOT_CALCULABLE = "not_calculable"
