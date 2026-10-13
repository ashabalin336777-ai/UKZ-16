"""Generate a small synthetic R2 cohort (no PHI) for pipeline smoke tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    out = Path("samples/validation/r2_synthetic_cohort.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    base = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    lines: list[str] = []
    for w in range(1, 11):
        worker = f"W-R2-{w:02d}"
        site = "SITE-A" if w <= 5 else "SITE-B"
        sex = "F" if w % 2 == 0 else "M"
        for d in range(6):
            # Later days for higher workers trend worse vitals → higher risk labels
            pulse = 65 + d * 2 + (8 if w > 7 else 0)
            sbp = 115 + d * 3 + (10 if w > 7 else 0)
            label = 1 if (pulse >= 78 or sbp >= 135) else 0
            measured_at = (base + timedelta(days=d * 7 + w)).isoformat()
            payload = {
                "worker_id": worker,
                "encounter_id": f"{worker}-D{d}",
                "measured_at": measured_at,
                "source_system": "SYNTHETIC_R2",
                "consent_research": True,
                "protocol_id": "PRMO_STD_v1",
                "protocol_version": "1.0",
                "vitals": {
                    "height_cm": 170,
                    "weight_kg": 70,
                    "bp_systolic_mmhg": sbp,
                    "bp_diastolic_mmhg": 75,
                    "pulse_bpm": pulse,
                },
                "context": {"site_id": site, "age_years": 30 + w},
                "psychometrics": {
                    "instrument": "PHQ-9",
                    "score": 2 + (3 if label else 0),
                    "scored_at": measured_at,
                    "validated": True,
                },
                "social_metrics": {"validated": True, "engagement_score": 0.8 if label == 0 else 0.4},
                "emr_flags": {"clinically_confirmed_chronic": False, "chronic_condition_codes": []},
                "provenance": {
                    "device_id": "SYN-1",
                    "operator_id": "OP-R2",
                    "input_ids": [f"{worker}-D{d}-in"],
                    "unit_system": "SI_medical",
                },
            }
            row = {
                "row_id": f"{worker}-D{d}",
                "payload": payload,
                "reference": {
                    "label": label,
                    "source": "synthetic_independent_rule_v1",
                },
                "subgroup": {"site_id": site, "sex": sex},
            }
            lines.append(json.dumps(row, ensure_ascii=False))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} rows to {out}")


if __name__ == "__main__":
    main()
