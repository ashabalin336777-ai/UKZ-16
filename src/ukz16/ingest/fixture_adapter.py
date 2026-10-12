from __future__ import annotations

import json
from pathlib import Path

from ukz16.domain.contracts import PrMOIngest
from ukz16.ingest.base import IngestAdapter
from ukz16.ingest.mock import MockEcozAdapter


class FixtureEcozAdapter(IngestAdapter):
    """File-backed ECOZ stand-in for research. Replace with live MIS client later.

    Loads JSON payloads from a directory keyed by encounter_id.
    Does not change the explanation contract.
    """

    def __init__(self, fixtures_dir: Path, fallback: MockEcozAdapter | None = None) -> None:
        self.fixtures_dir = fixtures_dir
        self.fallback = fallback or MockEcozAdapter()

    def fetch_encounter(self, encounter_id: str) -> PrMOIngest:
        path = self.fixtures_dir / f"{encounter_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return self.validate_envelope(PrMOIngest.model_validate(data))
        return self.fallback.fetch_encounter(encounter_id)

    def validate_envelope(self, payload: PrMOIngest) -> PrMOIngest:
        return self.fallback.validate_envelope(payload)

    def put(self, payload: PrMOIngest) -> None:
        self.fallback.put(payload)
