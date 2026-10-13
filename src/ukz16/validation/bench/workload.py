from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Iterator

from ukz16.domain.contracts import (
    ContextInfo,
    PrMOIngest,
    Provenance,
    Psychometrics,
    SocialMetrics,
    Vitals,
)


def iter_synthetic_payloads(*, n: int, seed: int = 16) -> Iterator[PrMOIngest]:
    rng = random.Random(seed)
    base = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    for i in range(n):
        complete = rng.random() > 0.15
        psycho = rng.random() > 0.25
        social = rng.random() > 0.25
        yield PrMOIngest(
            worker_id=f"BENCH-W-{i % max(1, n // 10)}",
            encounter_id=f"BENCH-E-{i}",
            measured_at=base + timedelta(minutes=i),
            source_system="BENCH",
            consent_research=True,
            protocol_id="PRMO_STD_v1",
            protocol_version="1.0",
            vitals=Vitals(
                height_cm=170 + rng.uniform(-5, 15) if complete else None,
                weight_kg=70 + rng.uniform(-10, 20) if complete else None,
                bp_systolic_mmhg=110 + rng.uniform(-10, 40),
                bp_diastolic_mmhg=70 + rng.uniform(-10, 20),
                pulse_bpm=60 + rng.uniform(-10, 40),
            ),
            context=ContextInfo(age_years=30 + rng.uniform(0, 30), site_id=f"SITE-{i % 3}"),
            psychometrics=(
                Psychometrics(
                    instrument="PHQ-9",
                    score=rng.uniform(0, 20),
                    scored_at=base + timedelta(minutes=i),
                    validated=True,
                )
                if psycho
                else None
            ),
            social_metrics=(
                SocialMetrics(validated=True, engagement_score=rng.uniform(0.2, 0.95))
                if social
                else None
            ),
            provenance=Provenance(device_id="BENCH", input_ids=[f"in-{i}"]),
        )
