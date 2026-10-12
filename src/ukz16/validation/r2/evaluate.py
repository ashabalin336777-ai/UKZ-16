from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import ModelPackage
from ukz16.quality.gates import run_quality_gates
from ukz16.validation.r2.cohort import CohortRow
from ukz16.validation.r2.metrics import score_to_risk


@dataclass
class PredictionRow:
    row_id: str
    worker_id: str
    reference_label: int
    health_id_value: float | None
    health_id_status: str
    risk_prob: float | None
    abstained: bool
    acute: bool
    persistence: bool
    subgroup: dict[str, Any]
    reason: str | None


def predict_cohort(rows: list[CohortRow], model: ModelPackage) -> list[PredictionRow]:
    preds: list[PredictionRow] = []
    # History for corridors: prior points within same worker, earlier times only
    history: dict[str, list[Any]] = {}
    ordered = sorted(rows, key=lambda r: (r.worker_id, r.measured_at, r.row_id))
    from ukz16.corridors.baseline import PriorPoint

    for row in ordered:
        quality = run_quality_gates(row.payload, model)
        prior_points: list[PriorPoint] = history.get(row.worker_id, [])
        result = evaluate_health_id(
            row.payload,
            quality,
            model,
            prior_points=prior_points,
            prior_deviation_dates=[],
        )
        value = result.health_id.value
        abstained = value is None
        risk = None if abstained else score_to_risk(value)
        preds.append(
            PredictionRow(
                row_id=row.row_id,
                worker_id=row.worker_id,
                reference_label=row.reference_label,
                health_id_value=value,
                health_id_status=result.health_id.status.value,
                risk_prob=risk,
                abstained=abstained,
                acute=bool(result.acute_state and result.acute_state.is_acute),
                persistence=bool(result.persistence and result.persistence.is_persistent),
                subgroup=row.subgroup,
                reason=result.health_id.reason,
            )
        )
        # Update personal baseline history with hBody if available
        hbody = next((c for c in result.components if c.name == "hBody" and c.value is not None), None)
        if hbody is not None and quality.status.value == "ok":
            history.setdefault(row.worker_id, []).append(
                PriorPoint(
                    measured_at=row.measured_at,
                    measured_date=row.measured_at.date().isoformat(),
                    value=float(hbody.value),
                    quality_ok=True,
                )
            )
    return preds
