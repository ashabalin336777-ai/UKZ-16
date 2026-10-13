from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ukz16.domain.contracts import PrMOIngest
from ukz16.governance.model_registry import ModelPackage


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def instrument_catalog(model: ModelPackage) -> dict[str, Any]:
    return dict((model.config.get("psychometrics") or {}).get("instruments") or {})


def psychometrics_reject_reason(payload: PrMOIngest, model: ModelPackage) -> str | None:
    """Return a block reason, or None when the score may enter hMental.

    Absence of a validated score is `no_validated_psychometrics` (not a field reject).
    """
    psy = payload.psychometrics
    if not psy or not psy.validated or psy.score is None:
        return "no_validated_psychometrics"
    catalog = instrument_catalog(model)
    name = (psy.instrument or "").strip()
    spec = catalog.get(name)
    if spec is None:
        return "unknown_instrument"
    if psy.scored_at is None:
        return "psychometrics_date_required"
    if _as_utc(psy.scored_at) > _as_utc(payload.measured_at):
        return "psychometrics_after_encounter"
    score = float(psy.score)
    if score < float(spec["min"]) or score > float(spec["max"]):
        return "score_out_of_range"
    return None


def wellness_from_instrument(score: float, spec: dict[str, Any]) -> float:
    lo = float(spec["min"])
    hi = float(spec["max"])
    span = hi - lo
    if span <= 0:
        raise ValueError("invalid_instrument_span")
    if spec.get("direction") == "higher_better":
        return max(0.0, min(1.0, (score - lo) / span))
    return max(0.0, min(1.0, 1.0 - (score - lo) / span))
