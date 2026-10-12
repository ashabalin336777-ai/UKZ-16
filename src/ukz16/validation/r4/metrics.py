from __future__ import annotations

from typing import Any

from ukz16.validation.r4.logs import ReviewLogRow


def override_rate(rows: list[ReviewLogRow]) -> float:
    return sum(1 for r in rows if r.override) / len(rows)


def mean_time_to_review(rows: list[ReviewLogRow]) -> float:
    return sum(r.time_to_review_sec for r in rows) / len(rows)


def decision_distribution(rows: list[ReviewLogRow]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.clinician_decision] = out.get(r.clinician_decision, 0) + 1
    return out


def net_benefit(
    rows: list[ReviewLogRow],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Simple decision-curve style net benefit for model-alert strategy.

    Treat model_alert (or risk>=threshold) as 'treat/review' recommendation.
    NB = TP/n - FP/n * (pt/(1-pt))
    """
    n = len(rows)
    if n == 0:
        return {"net_benefit_model": None, "net_benefit_all": None, "net_benefit_none": 0.0}
    pt = threshold
    odds = pt / (1.0 - pt) if pt < 1.0 else 0.0

    def _nb(use_model: bool, treat_all: bool) -> float:
        tp = fp = 0
        for r in rows:
            if treat_all:
                pred = True
            elif use_model:
                pred = r.model_alert if r.model_risk is None else (r.model_risk >= threshold)
            else:
                pred = False
            if pred and r.reference_label == 1:
                tp += 1
            elif pred and r.reference_label == 0:
                fp += 1
        return tp / n - fp / n * odds

    return {
        "threshold": threshold,
        "net_benefit_model": round(_nb(True, False), 6),
        "net_benefit_all": round(_nb(False, True), 6),
        "net_benefit_none": 0.0,
    }


def safety_summary(rows: list[ReviewLogRow]) -> dict[str, Any]:
    harms = [r for r in rows if r.harm_flag]
    missed = [
        r
        for r in rows
        if r.reference_label == 1 and r.clinician_decision in {"rejected", "no_action"} and not r.model_alert
    ]
    return {
        "n_harm_flags": len(harms),
        "harm_rate": round(len(harms) / len(rows), 6),
        "n_missed_positive_without_alert": len(missed),
        "diagnosis_auto_assigned": False,
    }
