from __future__ import annotations

from datetime import datetime, timezone

from ukz16.corridors.baseline import PriorPoint, compute_personal_corridor


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
