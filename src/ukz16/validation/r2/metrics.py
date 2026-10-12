from __future__ import annotations

import math
from typing import Any


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def brier_score(y_true: list[int], y_prob: list[float]) -> float | None:
    if not y_true:
        return None
    return sum((p - y) ** 2 for y, p in zip(y_true, y_prob, strict=True)) / len(y_true)


def expected_calibration_error(
    y_true: list[int],
    y_prob: list[float],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    if not y_true:
        return {"ece": None, "bins": []}
    bins: list[dict[str, Any]] = []
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [i for i, p in enumerate(y_prob) if (p >= lo and (p < hi or (b == n_bins - 1 and p <= hi)))]
        if not idx:
            continue
        acc = sum(y_true[i] for i in idx) / len(idx)
        conf = sum(y_prob[i] for i in idx) / len(idx)
        weight = len(idx) / n
        ece += abs(acc - conf) * weight
        bins.append(
            {
                "bin": b,
                "lo": lo,
                "hi": hi,
                "n": len(idx),
                "accuracy": round(acc, 6),
                "confidence": round(conf, 6),
            }
        )
    return {"ece": round(ece, 6), "bins": bins}


def bootstrap_ci(
    values: list[float],
    *,
    n_boot: int = 200,
    seed: int = 16,
    alpha: float = 0.05,
) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "low": None, "high": None}
    mean = sum(values) / len(values)
    # Deterministic LCG bootstrap
    state = seed
    samples: list[float] = []
    n = len(values)
    for _ in range(n_boot):
        total = 0.0
        for _j in range(n):
            state = (1103515245 * state + 12345) % (2**31)
            idx = state % n
            total += values[idx]
        samples.append(total / n)
    samples.sort()
    lo_i = int(math.floor(alpha / 2 * (n_boot - 1)))
    hi_i = int(math.ceil((1 - alpha / 2) * (n_boot - 1)))
    return {
        "mean": round(mean, 6),
        "low": round(samples[lo_i], 6),
        "high": round(samples[hi_i], 6),
    }


def confusion_at_threshold(
    y_true: list[int],
    y_prob: list[float],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for y, p in zip(y_true, y_prob, strict=True):
        pred = 1 if p >= threshold else 0
        if pred == 1 and y == 1:
            tp += 1
        elif pred == 1 and y == 0:
            fp += 1
        elif pred == 0 and y == 0:
            tn += 1
        else:
            fn += 1
    sens = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "sensitivity": None if sens is None else round(sens, 6),
        "specificity": None if spec is None else round(spec, 6),
        "false_negative_rate": None if sens is None else round(1 - sens, 6),
    }


def score_to_risk(health_id_value: float) -> float:
    """Map wellness-like HEALTH_ID (higher=better) to risk probability (higher=worse)."""
    return _clamp01(1.0 - health_id_value)


def subgroup_metrics(
    labels: list[int],
    probs: list[float],
    subgroups: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    buckets: dict[str, tuple[list[int], list[float]]] = {}
    for y, p, sg in zip(labels, probs, subgroups, strict=True):
        name = str(sg.get(key, "unknown"))
        buckets.setdefault(name, ([], []))
        buckets[name][0].append(y)
        buckets[name][1].append(p)
    out: dict[str, Any] = {}
    for name, (ys, ps) in sorted(buckets.items()):
        out[name] = {
            "n": len(ys),
            "brier": None if not ys else round(brier_score(ys, ps) or 0.0, 6),
            "positive_rate": round(sum(ys) / len(ys), 6) if ys else None,
        }
    return out
