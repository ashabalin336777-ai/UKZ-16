from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ukz16 import __version__
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import load_model_package
from ukz16.quality.gates import run_quality_gates
from ukz16.validation.bench.workload import iter_synthetic_payloads


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def run_bench(
    output_dir: Path,
    *,
    n: int = 200,
    seed: int = 16,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Time pure evaluation path (no HTTP/DB) on synthetic payloads."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model_package(model_version, enforce_signature=False)
    latencies_ms: list[float] = []
    statuses: dict[str, int] = {}

    for payload in iter_synthetic_payloads(n=n, seed=seed):
        quality = run_quality_gates(payload, model)
        t0 = time.perf_counter()
        result = evaluate_health_id(payload, quality, model)
        elapsed = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed)
        key = result.health_id.status.value
        statuses[key] = statuses.get(key, 0) + 1

    ordered = sorted(latencies_ms)
    report = {
        "schema": "ukz16.bench.report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ukz16_version": __version__,
        "model_version": model.version,
        "n": n,
        "seed": seed,
        "path": "evaluate_health_id+quality_gates",
        "latency_ms": {
            "p50": round(_percentile(ordered, 50), 4),
            "p95": round(_percentile(ordered, 95), 4),
            "p99": round(_percentile(ordered, 99), 4),
            "mean": round(statistics.fmean(ordered), 4) if ordered else 0.0,
            "max": round(ordered[-1], 4) if ordered else 0.0,
        },
        "status_counts": statuses,
        "research_only": True,
        "sla_claim": False,
        "notes": [
            "Synthetic CPU path only; not production p95/99.5% SLA evidence.",
            "TZ operational targets require instrumented staging with real traffic.",
        ],
    }
    (output_dir / "bench_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md = "\n".join(
        [
            "# UKZ-16 synthetic bench",
            "",
            f"- n: {n}",
            f"- model: `{model.version}`",
            f"- p50_ms: {report['latency_ms']['p50']}",
            f"- p95_ms: {report['latency_ms']['p95']}",
            f"- p99_ms: {report['latency_ms']['p99']}",
            f"- sla_claim: false",
            "",
        ]
    )
    (output_dir / "bench_report.md").write_text(md, encoding="utf-8")
    return report
