from __future__ import annotations

from abc import ABC, abstractmethod

from ukz16.domain.contracts import PrMOIngest


class IngestAdapter(ABC):
    """Contract for МИС ЕЦОЗ / mock providers."""

    @abstractmethod
    def fetch_encounter(self, encounter_id: str) -> PrMOIngest:
        raise NotImplementedError

    @abstractmethod
    def validate_envelope(self, payload: PrMOIngest) -> PrMOIngest:
        raise NotImplementedError

    def put(self, payload: PrMOIngest) -> None:
        """Optional local cache for research evaluate path."""
        return None
