"""Generate synthetic R3 multi-site cohort and R4 review log (no PHI)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_r3_cohort(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
    lines: list[str] = []
    sites = [("SITE-EXT-1", "DEV-A"), ("SITE-EXT-2", "DEV-B")]
    for s_i, (site, device) in enumerate(sites):
        for w in range(1, 6):
            worker = f"W-R3-{site[-1]}-{w}"
            for d in range(4):
                pulse = 68 + d * 3 + s_i * 2
                sbp = 118 + d * 4 + s_i * 3
                label = 1 if pulse >= 78 or sbp >= 136 else 0
                row = {
                    "row_id": f"{worker}-D{d}",
                    "payload": {
                        "worker_id": worker,
                        "encounter_id": f"{worker}-D{d}",
                        "measured_at": (base + timedelta(days=d * 5 + w + s_i * 20)).isoformat(),
                        "source_system": "SYNTHETIC_R3",
                        "consent_research": True,
                        "protocol_id": "PRMO_STD_v1",
                        "protocol_version": "1.0",
                        "vitals": {
                            "height_cm": 172,
                            "weight_kg": 71,
                            "bp_systolic_mmhg": sbp,
                            "bp_diastolic_mmhg": 78,
                            "pulse_bpm": pulse,
                        },
                        "context": {"site_id": site, "age_years": 35 + w},
                        "psychometrics": {
                            "instrument": "PHQ-9",
                            "score": 1 + (4 if label else 0),
                            "validated": True,
                        },
                        "social_metrics": {
                            "validated": True,
                            "engagement_score": 0.85 if label == 0 else 0.35,
                        },
                        "emr_flags": {
                            "clinically_confirmed_chronic": False,
                            "chronic_condition_codes": [],
                        },
                        "provenance": {
                            "device_id": device,
                            "operator_id": "OP-R3",
                            "input_ids": [f"{worker}-{d}"],
                            "unit_system": "SI_medical",
                        },
                    },
                    "reference": {"label": label, "source": "synthetic_external_rule_v1"},
                    "subgroup": {"site_id": site, "device_id": device, "sex": "F" if w % 2 == 0 else "M"},
                }
                lines.append(json.dumps(row, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def generate_r4_log(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i in range(1, 41):
        label = 1 if i % 3 == 0 else 0
        # Mix true/false alerts so overrides actually occur
        if label == 1:
            risk = 0.75 if i % 5 != 0 else 0.35  # occasional miss
        else:
            risk = 0.15 if i % 4 != 0 else 0.65  # occasional false alert
        alert = risk >= 0.5
        if alert and label == 1:
            decision = "confirmed"
            override = False
        elif alert and label == 0:
            decision = "rejected" if i % 2 == 0 else "confirmed"
            override = decision == "rejected"
        elif not alert and label == 1:
            decision = "escalated"
            override = True
        else:
            decision = "no_action"
            override = False
        row = {
            "case_id": f"C-R4-{i:03d}",
            "worker_id": f"W-R4-{(i % 8) + 1}",
            "model_alert": alert,
            "model_risk": round(min(risk, 0.95), 3),
            "clinician_decision": decision,
            "time_to_review_sec": 30 + (i % 7) * 15,
            "override": override,
            "reference_label": label,
            "harm_flag": bool(label == 1 and decision == "no_action" and i % 11 == 0),
            "site_id": "SITE-EXT-1" if i <= 20 else "SITE-EXT-2",
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> None:
    n3 = generate_r3_cohort(Path("samples/validation/r3_synthetic_multisite.jsonl"))
    n4 = generate_r4_log(Path("samples/validation/r4_synthetic_review_log.jsonl"))
    print(f"R3 cohort rows={n3}; R4 review log rows={n4}")


if __name__ == "__main__":
    main()
