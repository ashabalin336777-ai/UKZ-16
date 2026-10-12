from __future__ import annotations

from ukz16.domain.contracts import PrMOIngest
from ukz16.ingest.base import IngestAdapter


class MockEcozAdapter(IngestAdapter):
    """In-memory / passthrough adapter for research Phase 1 (no live ЕЦОЗ)."""

    def __init__(self) -> None:
        self._store: dict[str, PrMOIngest] = {}

    def put(self, payload: PrMOIngest) -> None:
        self._store[payload.encounter_id] = payload

    def fetch_encounter(self, encounter_id: str) -> PrMOIngest:
        if encounter_id not in self._store:
            raise KeyError(f"encounter not found in mock ECOZ: {encounter_id}")
        return self._store[encounter_id]

    def validate_envelope(self, payload: PrMOIngest) -> PrMOIngest:
        if not payload.consent_research:
            raise PermissionError("consent_required")
        if not payload.worker_id or not payload.encounter_id:
            raise ValueError("worker_id and encounter_id required")
        return payload
