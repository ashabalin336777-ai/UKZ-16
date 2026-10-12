from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from ukz16.domain.contracts import PrMOIngest


@dataclass(frozen=True)
class CohortRow:
    """One retrospective event with independent reference label."""

    row_id: str
    worker_id: str
    measured_at: datetime
    payload: PrMOIngest
    reference_label: int  # 0/1 independent clinical/research reference
    reference_source: str
    subgroup: dict[str, Any]


def load_cohort_jsonl(path: Path) -> list[CohortRow]:
    rows: list[CohortRow] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            payload = PrMOIngest.model_validate(raw["payload"])
            ref = raw.get("reference") or {}
            label = int(ref["label"])
            if label not in (0, 1):
                raise ValueError(f"reference.label must be 0/1 at line {line_no}")
            rows.append(
                CohortRow(
                    row_id=str(raw.get("row_id") or f"row-{line_no}"),
                    worker_id=payload.worker_id,
                    measured_at=payload.measured_at,
                    payload=payload,
                    reference_label=label,
                    reference_source=str(ref.get("source") or "unspecified"),
                    subgroup=dict(raw.get("subgroup") or {}),
                )
            )
    if not rows:
        raise ValueError("empty_cohort")
    return rows


def iter_workers(rows: list[CohortRow]) -> Iterator[str]:
    seen: set[str] = set()
    for row in rows:
        if row.worker_id not in seen:
            seen.add(row.worker_id)
            yield row.worker_id
