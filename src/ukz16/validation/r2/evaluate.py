from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ukz16.engine.sequence import WorkerSequence
from ukz16.governance.model_registry import ModelPackage
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
    ordered = sorted(rows, key=lambda r: (r.worker_id, r.measured_at, r.row_id))
    sequence = WorkerSequence(model)
    for row in ordered:
        _quality, result = sequence.evaluate(row.payload)
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
    return preds
