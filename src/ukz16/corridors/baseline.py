from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Any


@dataclass(frozen=True)
class PriorPoint:
    measured_at: datetime
    measured_date: str
    value: float
    quality_ok: bool


def _mad(values: list[float], med: float) -> float:
    return median([abs(v - med) for v in values]) if values else 0.0


def compute_personal_corridor(
    priors: list[PriorPoint],
    current_value: float | None,
    current_date: str,
    *,
    min_prior_unique_dates: int,
    acute_z: float,
    mad_floor: float,
    exclude_current: bool = True,
) -> dict[str, Any]:
    """Baseline from prior unique quality dates only; current point excluded."""
    by_date: dict[str, PriorPoint] = {}
    for p in priors:
        if not p.quality_ok:
            continue
        if exclude_current and p.measured_date == current_date:
            continue
        # one point per unique date — keep earliest for determinism
        if p.measured_date not in by_date or p.measured_at < by_date[p.measured_date].measured_at:
            by_date[p.measured_date] = p

    values = [p.value for p in sorted(by_date.values(), key=lambda x: x.measured_date)]
    n = len(values)
    if current_value is None:
        return {
            "outside_corridor": False,
            "z_score": None,
            "corridor_low": None,
            "corridor_high": None,
            "baseline_n_unique_dates": n,
            "method": "robust_z",
            "reason": "current_value_missing",
        }
    if n < min_prior_unique_dates:
        return {
            "outside_corridor": False,
            "z_score": None,
            "corridor_low": None,
            "corridor_high": None,
            "baseline_n_unique_dates": n,
            "method": "robust_z",
            "reason": "insufficient_baseline",
        }

    med = median(values)
    mad = max(_mad(values, med), mad_floor)
    # robust z ≈ 0.6745 * (x - med) / MAD; use simple (x-med)/MAD for scaffold
    z = (current_value - med) / mad
    half_width = acute_z * mad
    return {
        "outside_corridor": abs(z) >= acute_z,
        "z_score": round(z, 6),
        "corridor_low": round(med - half_width, 6),
        "corridor_high": round(med + half_width, 6),
        "baseline_n_unique_dates": n,
        "method": "robust_z",
        "reason": None,
    }


def assert_no_future_leakage(
    event_times: list[datetime],
    feature_times: list[datetime],
) -> None:
    """Raise if any feature timestamp is after its event (leakage guard for tests/splits)."""
    for i, (event_t, feat_t) in enumerate(zip(event_times, feature_times, strict=False)):
        if feat_t > event_t:
            raise ValueError(f"future_feature_leakage at index {i}: feature {feat_t} > event {event_t}")


def patient_level_split_ok(train_ids: set[str], test_ids: set[str]) -> bool:
    return train_ids.isdisjoint(test_ids)
