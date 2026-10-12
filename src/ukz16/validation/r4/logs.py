from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewLogRow:
    case_id: str
    worker_id: str
    model_alert: bool
    model_risk: float | None
    clinician_decision: str  # confirmed | rejected | escalated | no_action
    time_to_review_sec: float
    override: bool
    reference_label: int
    harm_flag: bool
    site_id: str


def load_review_log_jsonl(path: Path) -> list[ReviewLogRow]:
    rows: list[ReviewLogRow] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            decision = str(raw["clinician_decision"])
            if decision not in {"confirmed", "rejected", "escalated", "no_action"}:
                raise ValueError(f"invalid clinician_decision at line {line_no}")
            rows.append(
                ReviewLogRow(
                    case_id=str(raw["case_id"]),
                    worker_id=str(raw["worker_id"]),
                    model_alert=bool(raw.get("model_alert")),
                    model_risk=None if raw.get("model_risk") is None else float(raw["model_risk"]),
                    clinician_decision=decision,
                    time_to_review_sec=float(raw.get("time_to_review_sec") or 0.0),
                    override=bool(raw.get("override")),
                    reference_label=int(raw["reference_label"]),
                    harm_flag=bool(raw.get("harm_flag", False)),
                    site_id=str(raw.get("site_id") or "unknown"),
                )
            )
    if not rows:
        raise ValueError("empty_review_log")
    return rows
