from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from ukz16.validation.r2.runner import run_r2_validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UKZ-16 R2 retrospective validation")
    parser.add_argument("--cohort", type=Path, required=True, help="JSONL cohort path")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--model-version", default=None)
    parser.add_argument("--split", choices=["group", "temporal", "both"], default="both")
    parser.add_argument("--cutoff", default=None, help="ISO datetime for temporal split")
    parser.add_argument("--test-fraction", type=float, default=0.3)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=16)
    args = parser.parse_args(argv)

    cutoff = datetime.fromisoformat(args.cutoff.replace("Z", "+00:00")) if args.cutoff else None
    report = run_r2_validation(
        args.cohort,
        output_dir=args.out,
        model_version=args.model_version,
        split=args.split,
        temporal_cutoff=cutoff,
        test_fraction=args.test_fraction,
        threshold=args.threshold,
        seed=args.seed,
    )
    print(f"R2 report written to {args.out}")
    print(f"model={report['model_version']} rows={report['n_rows']} workers={report['n_workers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
