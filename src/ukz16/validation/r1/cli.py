from __future__ import annotations

import argparse
from pathlib import Path

from ukz16.validation.r1.runner import run_r1_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UKZ-16 R0/R1 analytical acceptance report")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--skip-pytest", action="store_true", help="Only write checklist freeze")
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra pytest args (repeatable), e.g. --pytest-arg tests/golden",
    )
    args = parser.parse_args(argv)

    report = run_r1_report(
        args.out,
        run_pytest=not args.skip_pytest,
        pytest_args=args.pytest_arg or None,
    )
    print(f"R1 report written to {args.out}")
    print(
        f"model={report['model_version']} "
        f"r0_ok={report['r0']['all_present']} "
        f"a16_covered={report['a16']['covered']}/{report['a16']['total']} "
        f"pytest={report['pytest'].get('passed')} "
        f"ready={report['a16']['ready_for_signed_acceptance']}"
    )
    if report["pytest"].get("ran") and not report["pytest"].get("passed"):
        return 1
    if not report["r0"]["all_present"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
