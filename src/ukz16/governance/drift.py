from __future__ import annotations

from collections import Counter
from typing import Any


def detect_status_drift(
    reference_statuses: list[str],
    current_statuses: list[str],
    *,
    min_n: int = 20,
    max_shift: float = 0.25,
) -> dict[str, Any]:
    """Simple distribution drift stub on health_id_status. Never auto-updates model."""
    if len(reference_statuses) < min_n or len(current_statuses) < min_n:
        return {
            "alert": False,
            "reason": "insufficient_n",
            "auto_update": False,
            "ref_n": len(reference_statuses),
            "cur_n": len(current_statuses),
        }

    def _dist(items: list[str]) -> dict[str, float]:
        c = Counter(items)
        total = sum(c.values()) or 1
        return {k: v / total for k, v in c.items()}

    ref = _dist(reference_statuses)
    cur = _dist(current_statuses)
    keys = set(ref) | set(cur)
    l1 = sum(abs(ref.get(k, 0.0) - cur.get(k, 0.0)) for k in keys) / 2.0
    alert = l1 >= max_shift
    return {
        "alert": alert,
        "reason": "status_distribution_shift" if alert else "ok",
        "l1_distance": l1,
        "threshold": max_shift,
        "auto_update": False,
        "reference": ref,
        "current": cur,
    }
