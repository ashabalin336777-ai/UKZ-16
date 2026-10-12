from __future__ import annotations

from typing import Any

import httpx

from ukz16.domain.contracts import PrMOIngest
from ukz16.ingest.base import IngestAdapter
from ukz16.ingest.ecoz_mapper import map_ecoz_encounter


class HttpEcozAdapter(IngestAdapter):
    """Live ECOZ/MIS HTTP client behind IngestAdapter.

    GET {base_url}/encounters/{encounter_id} with Bearer or API token.
    Response is mapped via ecoz_mapper; explanation contract stays unchanged.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout_s: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s
        self._client = client
        self._owned_client = client is None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers: dict[str, str] = {"Accept": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout_s)
        return self._client

    def close(self) -> None:
        if self._owned_client and self._client is not None:
            self._client.close()
            self._client = None

    def fetch_encounter(self, encounter_id: str) -> PrMOIngest:
        client = self._get_client()
        response = client.get(f"/encounters/{encounter_id}")
        if response.status_code == 404:
            raise KeyError(f"ecoz_encounter_not_found:{encounter_id}")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return self.validate_envelope(map_ecoz_encounter(data))

    def validate_envelope(self, payload: PrMOIngest) -> PrMOIngest:
        if not payload.consent_research:
            raise PermissionError("consent_required")
        if not payload.worker_id or not payload.encounter_id:
            raise ValueError("worker_id and encounter_id required")
        return payload

    def put(self, payload: PrMOIngest) -> None:
        # Research evaluate path may receive payloads already mapped; no remote write.
        return None
