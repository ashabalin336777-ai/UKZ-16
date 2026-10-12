from __future__ import annotations

import argparse
from pathlib import Path

from ukz16.validation.r4.runner import run_r4_utility


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UKZ-16 R4 clinical utility evaluation")
    parser.add_argument("--log", type=Path, required=True, help="Review log JSONL")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--model-version", default=None)
    args = parser.parse_args(argv)
    report = run_r4_utility(
        args.log,
        output_dir=args.out,
        threshold=args.threshold,
        model_version=args.model_version,
    )
    print(f"R4 report written to {args.out}")
    print(f"cases={report['n_cases']} override_rate={report['metrics']['override_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
