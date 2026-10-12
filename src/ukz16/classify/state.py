from __future__ import annotations

from typing import Any

from ukz16.domain.contracts import AcuteState, EmrFlags, PersistenceInfo, PersonalDeviation


def classify_state(
    *,
    personal: dict[str, Any],
    prior_deviation_dates: list[str],
    current_date: str,
    current_outside: bool,
    persistence_threshold: int,
    emr_flags: EmrFlags | None,
    population_flags: list[str],
) -> tuple[AcuteState, PersonalDeviation, PersistenceInfo, bool]:
    """Return acute, personal deviation, persistence, and chronic_from_emr flag.

    Chronic is NEVER inferred from persistence — only from EMR/MIS flag.
    """
    deviation = PersonalDeviation(
        outside_corridor=bool(personal.get("outside_corridor")),
        z_score=personal.get("z_score"),
        corridor_low=personal.get("corridor_low"),
        corridor_high=personal.get("corridor_high"),
        baseline_n_unique_dates=int(personal.get("baseline_n_unique_dates") or 0),
        method=personal.get("method"),
        reason=personal.get("reason"),
    )

    acute_flags: list[str] = []
    if deviation.outside_corridor:
        acute_flags.append("personal_corridor")
    acute_flags.extend(population_flags)
    acute = AcuteState(
        is_acute=bool(acute_flags),
        flags=acute_flags,
        method="personal_corridor_or_population_band",
    )

    dates = sorted(set(prior_deviation_dates))
    if current_outside and current_date not in dates:
        dates.append(current_date)
        dates = sorted(set(dates))
    # unique dates only — same day never counted twice
    persistence = PersistenceInfo(
        unique_dates_with_deviation=len(dates),
        unique_dates_rule="prior_quality_dates_only",
        same_day_attempts_do_not_increase_persistence=True,
        is_persistent=len(dates) >= persistence_threshold,
        dates=dates,
    )

    chronic_from_emr = bool(emr_flags and emr_flags.clinically_confirmed_chronic)
    return acute, deviation, persistence, chronic_from_emr
