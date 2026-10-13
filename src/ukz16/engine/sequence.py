"""Chronological per-worker evaluation with personal-corridor history.

One place for the rule used by the API-less batch paths (customer pilot, R2, R4):
feed encounters in time order, keep prior hBody points, and accumulate deviation dates.
"""

from __future__ import annotations

from collections import defaultdict

from ukz16.corridors.baseline import PriorPoint
from ukz16.domain.contracts import EvaluationResult, PrMOIngest
from ukz16.domain.enums import ComponentStatus, QualityStatus
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import ModelPackage
from ukz16.quality.gates import QualityGateResult, run_quality_gates

_HBODY_INPUTS = ("bp_systolic_mmhg", "bp_diastolic_mmhg", "pulse_bpm")


def hbody_prior_point(
    payload: PrMOIngest,
    quality: QualityGateResult,
    result: EvaluationResult,
) -> PriorPoint | None:
    """Baseline point for the next encounter. None when hBody itself is unusable."""
    component = next(
        (
            c
            for c in result.components
            if c.name == "hBody" and c.status == ComponentStatus.DERIVED and c.value is not None
        ),
        None,
    )
    if component is None or quality.refuse or "hBody" in quality.blocked_components:
        return None
    inputs_present = all(getattr(payload.vitals, name) is not None for name in _HBODY_INPUTS)
    inputs_ok = all(
        quality.field_quality.get(name) in (None, QualityStatus.OK) for name in _HBODY_INPUTS
    )
    return PriorPoint(
        measured_at=payload.measured_at,
        measured_date=payload.measured_at.date().isoformat(),
        value=float(component.value),
        quality_ok=inputs_present and inputs_ok,
    )


class WorkerSequence:
    """Stateful evaluator: history is keyed by worker and never includes the current point."""

    def __init__(self, model: ModelPackage) -> None:
        self.model = model
        self._priors: dict[str, list[PriorPoint]] = defaultdict(list)
        self._deviation_dates: dict[str, list[str]] = defaultdict(list)

    def evaluate(self, payload: PrMOIngest) -> tuple[QualityGateResult, EvaluationResult]:
        worker_id = payload.worker_id
        quality = run_quality_gates(payload, self.model)
        result = evaluate_health_id(
            payload,
            quality,
            self.model,
            prior_points=list(self._priors[worker_id]),
            prior_deviation_dates=list(self._deviation_dates[worker_id]),
        )
        point = hbody_prior_point(payload, quality, result)
        if point is not None:
            self._priors[worker_id].append(point)
        if result.personal_deviation and result.personal_deviation.outside_corridor:
            self._deviation_dates[worker_id].append(payload.measured_at.date().isoformat())
        return quality, result
