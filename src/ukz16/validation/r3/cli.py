from __future__ import annotations

import argparse
from pathlib import Path

from ukz16.validation.r3.freeze import freeze_model_for_r3
from ukz16.validation.r3.runner import run_r3_validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UKZ-16 R3 external prospective validation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    freeze_p = sub.add_parser("freeze", help="Freeze model package before enrollment")
    freeze_p.add_argument("--out", type=Path, required=True)
    freeze_p.add_argument("--model-version", default=None)
    freeze_p.add_argument("--site", action="append", default=[])

    run_p = sub.add_parser("run", help="Evaluate external cohort against freeze file")
    run_p.add_argument("--cohort", type=Path, required=True)
    run_p.add_argument("--freeze", type=Path, required=True)
    run_p.add_argument("--out", type=Path, required=True)
    run_p.add_argument("--threshold", type=float, default=0.5)

    args = parser.parse_args(argv)
    if args.cmd == "freeze":
        doc = freeze_model_for_r3(output_path=args.out, model_version=args.model_version, sites=args.site)
        print(f"Frozen {doc['model_version']} hash={doc['model_package_hash']} -> {args.out}")
        return 0

    report = run_r3_validation(args.cohort, args.freeze, output_dir=args.out, threshold=args.threshold)
    print(f"R3 report written to {args.out}")
    print(f"sites={report.get('sites')} freeze_ok={report['freeze_check']['ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
