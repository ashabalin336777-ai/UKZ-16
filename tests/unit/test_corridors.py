from __future__ import annotations

from datetime import datetime, timezone

from ukz16.corridors.baseline import PriorPoint, compute_personal_corridor
from ukz16.governance.model_registry import load_model_package


def test_exclude_current_date_from_baseline():
    priors = [
        PriorPoint(datetime(2026, 1, 1, tzinfo=timezone.utc), "2026-01-01", 0.8, True),
        PriorPoint(datetime(2026, 1, 2, tzinfo=timezone.utc), "2026-01-02", 0.82, True),
        PriorPoint(datetime(2026, 1, 3, tzinfo=timezone.utc), "2026-01-03", 0.79, True),
        PriorPoint(datetime(2026, 1, 4, tzinfo=timezone.utc), "2026-01-04", 0.1, True),  # current day prior attempt
    ]
    result = compute_personal_corridor(
        priors,
        current_value=0.1,
        current_date="2026-01-04",
        min_prior_unique_dates=3,
        acute_z=2.0,
        mad_floor=0.01,
        exclude_current=True,
    )
    assert result["baseline_n_unique_dates"] == 3
    assert result["outside_corridor"] is True


def test_default_corridor_flags_sharp_hbody_shift():
    """mad_floor must stay on the 0–1 score scale so a sharp drop leaves the corridor."""
    model = load_model_package("research-v0.2", enforce_signature=False)
    floor = float(model.config["corridor"]["mad_floor"])
    acute_z = float(model.config["thresholds"]["acute_z"])
    assert floor < 0.1
    priors = [
        PriorPoint(datetime(2026, 1, d, tzinfo=timezone.utc), f"2026-01-0{d}", 0.85, True)
        for d in (1, 2, 3)
    ]
    result = compute_personal_corridor(
        priors,
        current_value=0.40,
        current_date="2026-01-10",
        min_prior_unique_dates=int(model.config["corridor"]["min_prior_unique_dates"]),
        acute_z=acute_z,
        mad_floor=floor,
    )
    assert result["outside_corridor"] is True
    assert result["z_score"] is not None
    assert abs(result["z_score"]) >= acute_z
