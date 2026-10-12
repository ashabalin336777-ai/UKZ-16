from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ukz16.corridors.baseline import assert_no_future_leakage, patient_level_split_ok
from ukz16.validation.r2.cohort import CohortRow


@dataclass(frozen=True)
class SplitResult:
    train: list[CohortRow]
    test: list[CohortRow]
    method: str
    cutoff: str | None
    train_workers: set[str]
    test_workers: set[str]


def group_holdout_by_worker(
    rows: list[CohortRow],
    *,
    test_fraction: float = 0.3,
    seed: int = 16,
) -> SplitResult:
    """Hold out whole workers — never the same worker in train and test."""
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be in (0,1)")
    workers = sorted({r.worker_id for r in rows})
    # Deterministic shuffle via seed-based rotation
    rotated = workers[seed % len(workers) :] + workers[: seed % len(workers)]
    n_test = max(1, int(round(len(rotated) * test_fraction)))
    test_workers = set(rotated[:n_test])
    train_workers = set(rotated[n_test:])
    if not train_workers:
        raise ValueError("insufficient_workers_for_group_holdout")
    if not patient_level_split_ok(train_workers, test_workers):
        raise ValueError("patient_split_violation")
    train = [r for r in rows if r.worker_id in train_workers]
    test = [r for r in rows if r.worker_id in test_workers]
    return SplitResult(
        train=train,
        test=test,
        method="group_holdout_by_worker",
        cutoff=None,
        train_workers=train_workers,
        test_workers=test_workers,
    )


def temporal_split(
    rows: list[CohortRow],
    *,
    cutoff: datetime,
) -> SplitResult:
    """Train on events strictly before cutoff; test on cutoff and after.

    Also enforces group purity: any worker appearing after cutoff is removed from train
    entirely (no same worker across temporal regimes).
    """
    test_workers = {r.worker_id for r in rows if r.measured_at >= cutoff}
    train = [r for r in rows if r.measured_at < cutoff and r.worker_id not in test_workers]
    test = [r for r in rows if r.measured_at >= cutoff]
    train_workers = {r.worker_id for r in train}
    if not patient_level_split_ok(train_workers, test_workers):
        raise ValueError("patient_split_violation")
    # Leakage guard: for each test event, features must not be after event time
    # (payload.measured_at is the event time; synthetic features share that stamp)
    assert_no_future_leakage(
        [r.measured_at for r in test],
        [r.payload.measured_at for r in test],
    )
    return SplitResult(
        train=train,
        test=test,
        method="temporal_split_with_worker_purge",
        cutoff=cutoff.isoformat(),
        train_workers=train_workers,
        test_workers=test_workers,
    )
