"""Enrich customer Drive CSV with synthetic height/weight/psychometrics/EMR/sites.

Outputs R2/R3 cohorts + R4 review log for engineering validation.
clinical_claim = false — synthetic fields are not real clinical measurements.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from ukz16.domain.contracts import PrMOIngest
from ukz16.engine.sequence import WorkerSequence
from ukz16.governance.model_registry import load_model_package
from ukz16.ingest.customer_csv import map_customer_exam_row
from ukz16.ingest.synthetic_enrichment import (
    SITES,
    enrich_prmo,
    remap_worker_id,
    synthetic_reference_label,
    worker_enrichment_profile,
)
from ukz16.validation.r2.metrics import score_to_risk

DEFAULT_CSV = Path("data/customer_drive/03_индексы_CSV/health_id_per_exam.csv")
DEFAULT_OUT = Path("samples/validation")


def _load_csv(path: Path, limit: int | None) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if limit is not None:
        rows = rows[:limit]
    return rows


def build_enriched_rows(
    csv_rows: list[dict[str, str]],
    *,
    seed: int = 16,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    workers_sorted = sorted({str(r["employee_anon_id"]).strip() for r in csv_rows})
    remap = {wid: remap_worker_id(wid, i + 1) for i, wid in enumerate(workers_sorted)}
    profiles = {}
    for i, wid in enumerate(workers_sorted):
        base_prof = worker_enrichment_profile(remap[wid], seed=seed)
        # Round-robin sites so R3 always sees ≥2 external sites
        profiles[wid] = replace(base_prof, site_id=SITES[i % len(SITES)])

    enriched: list[dict[str, Any]] = []
    for row in csv_rows:
        raw_worker = str(row["employee_anon_id"]).strip()
        base = map_customer_exam_row(row)
        public_worker = remap[raw_worker]
        prof = profiles[raw_worker]
        # Remap ids in payload for portable samples
        base = base.model_copy(
            update={
                "worker_id": public_worker,
                "encounter_id": f"{public_worker}-{base.encounter_id[:12]}",
            }
        )
        payload = enrich_prmo(base, seed=seed, profile=prof)
        label, src = synthetic_reference_label(row, payload)
        enriched.append(
            {
                "row_id": payload.encounter_id,
                "payload": payload.model_dump(mode="json"),
                "reference": {
                    "label": label,
                    "source": src,
                    "enrichment": "synthetic_enrichment_v1",
                },
                "subgroup": {
                    "site_id": payload.context.site_id if payload.context else None,
                    "sex": prof.sex,
                    "device_id": payload.provenance.device_id,
                },
                "meta": {
                    "clinical_claim": False,
                    "vitals_source": "customer_drive_csv",
                    "anthropometrics_source": "synthetic",
                    "psychometrics_source": "synthetic",
                    "social_source": "synthetic",
                    "emr_source": "synthetic",
                    "site_source": "synthetic",
                },
            }
        )

    summary = {
        "clinical_claim": False,
        "n_rows": len(enriched),
        "n_workers": len(remap),
        "sites": {s: sum(1 for e in enriched if e["subgroup"]["site_id"] == s) for s in SITES},
        "label_positive": sum(1 for e in enriched if e["reference"]["label"] == 1),
        "label_negative": sum(1 for e in enriched if e["reference"]["label"] == 0),
        "instruments": _count_instruments(enriched),
        "chronic_workers": sum(1 for p in profiles.values() if p.chronic),
    }
    return enriched, remap, summary


def _count_instruments(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for r in rows:
        inst = (r["payload"].get("psychometrics") or {}).get("instrument")
        if inst:
            out[str(inst)] += 1
    return dict(out)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_r4_review_log(
    enriched: list[dict[str, Any]],
    *,
    model_version: str = "research-v0.2",
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Synthetic clinician review log from enriched evaluations."""
    model = load_model_package(model_version, enforce_signature=False)
    ordered = sorted(
        enriched,
        key=lambda row: (row["payload"]["worker_id"], row["payload"]["measured_at"], row["row_id"]),
    )
    sequence = WorkerSequence(model)
    log: list[dict[str, Any]] = []
    case_i = 0
    for row in ordered:
        payload = PrMOIngest.model_validate(row["payload"])
        _quality, result = sequence.evaluate(payload)
        value = result.health_id.value
        if value is None:
            continue
        risk = float(score_to_risk(value))
        label = int(row["reference"]["label"])
        alert = risk >= threshold
        case_i += 1
        # Keep alerts, positives, and a sparse negative sample
        if not (alert or label == 1 or case_i % 7 == 0):
            continue
        if alert and label == 1:
            decision, override = "confirmed", False
        elif alert and label == 0:
            decision = "rejected" if (case_i % 2 == 0) else "confirmed"
            override = decision == "rejected"
        elif (not alert) and label == 1:
            decision, override = "escalated", True
        else:
            decision, override = "no_action", False
        log.append(
            {
                "case_id": f"C-ENR-{case_i:04d}",
                "worker_id": payload.worker_id,
                "model_alert": alert,
                "model_risk": round(risk, 4),
                "clinician_decision": decision,
                "time_to_review_sec": 25 + (case_i % 9) * 12,
                "override": override,
                "reference_label": label,
                "harm_flag": bool(label == 1 and decision == "no_action"),
                "site_id": row["subgroup"].get("site_id"),
                "enrichment": "synthetic_enrichment_v1",
                "clinical_claim": False,
            }
        )
    return log


def smoke_subset(rows: list[dict[str, Any]], *, max_workers: int = 9, max_per_worker: int = 8) -> list[dict[str, Any]]:
    """Small portable subset for CI / samples without dumping full customer vitals."""
    by_w: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_w[r["payload"]["worker_id"]].append(r)
    out: list[dict[str, Any]] = []
    for i, wid in enumerate(sorted(by_w.keys())):
        if i >= max_workers:
            break
        chunk = sorted(by_w[wid], key=lambda x: x["payload"]["measured_at"])[:max_per_worker]
        out.extend(chunk)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reports", type=Path, default=Path("reports/customer_enriched"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=16)
    parser.add_argument("--skip-r4-eval", action="store_true", help="Skip building R4 log (faster)")
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    csv_rows = _load_csv(args.csv, args.limit)
    enriched, _remap, summary = build_enriched_rows(csv_rows, seed=args.seed)

    full_r2 = args.reports / "r2_cohort.jsonl"
    write_jsonl(full_r2, enriched)
    # R3 uses same rows (multi-site already in subgroup)
    write_jsonl(args.reports / "r3_cohort.jsonl", enriched)

    smoke = smoke_subset(enriched)
    write_jsonl(args.out / "customer_enriched_r2_smoke.jsonl", smoke)
    write_jsonl(args.out / "customer_enriched_r3_smoke.jsonl", smoke)

    if not args.skip_r4_eval:
        r4 = build_r4_review_log(enriched)
        write_jsonl(args.reports / "r4_review_log.jsonl", r4)
        write_jsonl(args.out / "customer_enriched_r4_smoke.jsonl", r4[:80] if len(r4) > 80 else r4)
        summary["n_r4_cases"] = len(r4)

    args.reports.mkdir(parents=True, exist_ok=True)
    (args.reports / "generation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "customer_enriched_generation_summary.json").write_text(
        json.dumps({**summary, "note": "full cohorts under reports/customer_enriched/"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Full cohorts -> {args.reports}")
    print(f"Smoke samples -> {args.out}")


if __name__ == "__main__":
    main()
