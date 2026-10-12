from __future__ import annotations

import argparse
from pathlib import Path

from ukz16.validation.bench.runner import run_bench


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UKZ-16 synthetic evaluation latency bench")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=16)
    parser.add_argument("--model-version", default=None)
    args = parser.parse_args(argv)
    report = run_bench(args.out, n=args.n, seed=args.seed, model_version=args.model_version)
    lat = report["latency_ms"]
    print(f"Bench written to {args.out}")
    print(f"n={report['n']} p50={lat['p50']}ms p95={lat['p95']}ms p99={lat['p99']}ms (no SLA claim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
