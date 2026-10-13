"""Import customer Drive CSV → PrMOIngest JSONL, evaluate UKZ-16, write pilot report.

Engineering check only — not a clinical claim (R2/R3/R4).
Does not use admission / result_medic_class as HEALTH_ID outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ukz16.domain.enums import HealthIdStatus
from ukz16.engine.sequence import WorkerSequence
from ukz16.governance.model_registry import load_model_package
from ukz16.ingest.customer_csv import customer_reference_fields, map_customer_exam_row

DEFAULT_CSV = Path("data/customer_drive/03_индексы_CSV/health_id_per_exam.csv")
DEFAULT_OUT = Path("reports/customer_pilot")


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 6)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None

    def ranks(vals: list[float]) -> list[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    return _pearson(ranks(xs), ranks(ys))


def _component_map(result) -> dict[str, Any]:
    return {
        c.name: {
            "status": c.status.value,
            "value": c.value,
            "reason": c.reason,
            "formula_id": c.formula_id,
        }
        for c in result.components
    }


def load_rows(path: Path, *, limit: int | None) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if limit is not None:
        rows = rows[:limit]
    return rows


def run_pilot(
    rows: list[dict[str, str]],
    *,
    model_version: str = "research-v0.2",
) -> dict[str, Any]:
    model = load_model_package(model_version, enforce_signature=False)
    # Chronological per worker for corridor / persistence
    by_worker: dict[str, list[tuple[datetime, dict[str, str]]]] = defaultdict(list)
    parse_errors: list[dict[str, str]] = []
    for row in rows:
        try:
            payload = map_customer_exam_row(row)
        except ValueError as exc:
            parse_errors.append(
                {
                    "exam_anon_id": str(row.get("exam_anon_id") or ""),
                    "error": str(exc),
                }
            )
            continue
        by_worker[payload.worker_id].append((payload.measured_at, row))

    for worker_id in by_worker:
        by_worker[worker_id].sort(key=lambda item: (item[0], item[1].get("exam_anon_id") or ""))

    eval_rows: list[dict[str, Any]] = []
    ingest_rows: list[dict[str, Any]] = []
    hbody_pairs: list[tuple[float, float]] = []
    status_counts: Counter[str] = Counter()
    hbody_status: Counter[str] = Counter()
    refuse_counts: Counter[str] = Counter()
    outside_corridor = 0
    persistent = 0
    evaluated = 0

    sequence = WorkerSequence(model)
    for worker_id, items in by_worker.items():
        for _measured_at, row in items:
            payload = map_customer_exam_row(row)
            ref = customer_reference_fields(row)
            quality, result = sequence.evaluate(payload)
            evaluated += 1
            status_counts[result.health_id.status.value] += 1
            if result.health_id.reason:
                refuse_counts[result.health_id.reason.split(":")[0]] += 1
            comps = _component_map(result)
            hb = comps.get("hBody", {})
            hbody_status[str(hb.get("status"))] += 1

            ukz_hbody = hb.get("value")
            cust_hbody = ref.get("hBody_ID")
            if isinstance(ukz_hbody, (int, float)) and isinstance(cust_hbody, (int, float)):
                hbody_pairs.append((float(ukz_hbody) * 100.0, float(cust_hbody)))

            if result.personal_deviation and result.personal_deviation.outside_corridor:
                outside_corridor += 1
            if result.persistence and result.persistence.is_persistent:
                persistent += 1

            ingest_rows.append(
                {
                    "row_id": payload.encounter_id,
                    "payload": payload.model_dump(mode="json"),
                    "customer_reference": ref,
                    "subgroup": {
                        "site_id": payload.context.site_id if payload.context else None,
                        "worker_id": worker_id,
                    },
                }
            )
            eval_rows.append(
                {
                    "encounter_id": payload.encounter_id,
                    "worker_id": worker_id,
                    "measured_at": payload.measured_at.isoformat(),
                    "ukz16": {
                        "health_id_status": result.health_id.status.value,
                        "health_id_value": result.health_id.value,
                        "health_id_reason": result.health_id.reason,
                        "model_version": result.health_id.version,
                        "hBody": hb,
                        "hMental": comps.get("hMental"),
                        "hSocial": comps.get("hSocial"),
                        "bmi": comps.get("bmi"),
                        "ap_baevsky": comps.get("ap_baevsky"),
                        "completeness": result.completeness.model_dump(),
                        "outside_corridor": bool(
                            result.personal_deviation and result.personal_deviation.outside_corridor
                        ),
                        "z_score": (
                            result.personal_deviation.z_score if result.personal_deviation else None
                        ),
                        "baseline_n": (
                            result.personal_deviation.baseline_n_unique_dates
                            if result.personal_deviation
                            else 0
                        ),
                        "is_persistent": bool(result.persistence and result.persistence.is_persistent),
                        "quality_status": quality.status.value,
                        "quality_refuse": quality.refuse,
                        "diagnosis_claim": False,
                        "employer_export_allowed": False,
                    },
                    "customer": ref,
                    "hBody_ukz_x100": (
                        round(float(ukz_hbody) * 100.0, 4) if isinstance(ukz_hbody, (int, float)) else None
                    ),
                    "hBody_delta_vs_customer": (
                        round(float(ukz_hbody) * 100.0 - float(cust_hbody), 4)
                        if isinstance(ukz_hbody, (int, float)) and isinstance(cust_hbody, (int, float))
                        else None
                    ),
                }
            )

    xs = [p[0] for p in hbody_pairs]
    ys = [p[1] for p in hbody_pairs]
    abs_err = [abs(a - b) for a, b in hbody_pairs]
    summary = {
        "clinical_claim": False,
        "purpose": "engineering_pilot_customer_csv",
        "model_version": model.version,
        "model_package_hash": model.package_hash,
        "n_csv_rows": len(rows),
        "n_parse_errors": len(parse_errors),
        "n_workers": len(by_worker),
        "n_evaluated": evaluated,
        "health_id_status_counts": dict(status_counts),
        "hBody_status_counts": dict(hbody_status),
        "health_id_reason_prefix_counts": dict(refuse_counts),
        "expected_health_id": HealthIdStatus.NOT_CALCULABLE.value,
        "expected_reason_contains": "insufficient_components:hMental,hSocial",
        "tz_note": (
            "Without validated psychometrics and social metrics, HEALTH_ID must stay null "
            "(no weight renormalization). Customer HEALTH_ID / proxies are comparison-only."
        ),
        "corridor": {
            "outside_corridor_n": outside_corridor,
            "persistent_n": persistent,
        },
        "hBody_vs_customer_hBody_ID": {
            "scale": "ukz_hBody_0_1_x100_vs_customer_0_100",
            "n_paired": len(hbody_pairs),
            "pearson_r": _pearson(xs, ys),
            "spearman_rho": _spearman(xs, ys),
            "mae": round(statistics.mean(abs_err), 4) if abs_err else None,
            "rmse": (
                round(math.sqrt(statistics.mean([(a - b) ** 2 for a, b in hbody_pairs])), 4)
                if hbody_pairs
                else None
            ),
            "ukz_mean_x100": round(statistics.mean(xs), 4) if xs else None,
            "customer_mean": round(statistics.mean(ys), 4) if ys else None,
        },
        "hard_rules": {
            "admission_not_used_as_health_id": True,
            "customer_proxies_not_substituted": True,
            "diagnosis_claim": False,
            "employer_export_allowed": False,
        },
        "gaps_for_full_contract": [
            "height_cm",
            "weight_kg",
            "psychometrics.validated",
            "social_metrics.validated",
            "emr chronic codes",
            "multi-site for R3",
            "clinician R4 review GT",
        ],
        "parse_errors_sample": parse_errors[:20],
    }
    return {
        "summary": summary,
        "ingest_rows": ingest_rows,
        "eval_rows": eval_rows,
    }


def write_outputs(bundle: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(bundle["summary"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "ingest.jsonl").open("w", encoding="utf-8") as fh:
        for row in bundle["ingest_rows"]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (out_dir / "evaluations.jsonl").open("w", encoding="utf-8") as fh:
        for row in bundle["eval_rows"]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    s = bundle["summary"]
    hb = s["hBody_vs_customer_hBody_ID"]
    md = f"""# Customer pilot report (engineering only)

**clinical_claim = false**

Model: `{s["model_version"]}` · evaluated: **{s["n_evaluated"]}** · workers: **{s["n_workers"]}**

## TZ / contract check

- HEALTH_ID status counts: `{s["health_id_status_counts"]}`
- Expected without psychometrics/social: `not_calculable` (no renormalization)
- hBody status: `{s["hBody_status_counts"]}`
- BMI/AP stay `missing` without height/weight (see per-row evaluations)

## hBody vs customer `hBody_ID` (UKZ×100)

| Metric | Value |
|--------|-------|
| Paired n | {hb["n_paired"]} |
| Pearson r | {hb["pearson_r"]} |
| Spearman ρ | {hb["spearman_rho"]} |
| MAE | {hb["mae"]} |
| RMSE | {hb["rmse"]} |
| UKZ mean×100 | {hb["ukz_mean_x100"]} |
| Customer mean | {hb["customer_mean"]} |

## Corridor

- Outside corridor: {s["corridor"]["outside_corridor_n"]}
- Persistent: {s["corridor"]["persistent_n"]}

## Gaps still blocking clinical R2–R4

{chr(10).join("- " + g for g in s["gaps_for_full_contract"])}

## Artifacts

- `summary.json`
- `ingest.jsonl` — PrMOIngest (+ customer_reference side-car)
- `evaluations.jsonl` — per-exam UKZ-16 vs customer columns

Hard rules: admission / `result_medic_class` не использованы как выход HEALTH_ID; proxy заказчика не подставлялись в индекс.
"""
    (out_dir / "REPORT.md").write_text(md, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None, help="Optional row cap for smoke runs")
    parser.add_argument("--model-version", default="research-v0.2")
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    rows = load_rows(args.csv, limit=args.limit)
    bundle = run_pilot(rows, model_version=args.model_version)
    write_outputs(bundle, args.out)
    s = bundle["summary"]
    print(json.dumps({k: s[k] for k in (
        "clinical_claim",
        "n_evaluated",
        "n_workers",
        "health_id_status_counts",
        "hBody_status_counts",
        "hBody_vs_customer_hBody_ID",
        "corridor",
    )}, ensure_ascii=False, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
