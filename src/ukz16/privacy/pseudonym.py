from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from ukz16.config import get_resolved_settings, get_settings


class Pseudonymizer:
    """HMAC-based subject pseudonymization for research lane.

    Operational worker_id stays in operational tables; research/audit exports use
    `subject_pseudo_id`. Never log the pepper.
    """

    def __init__(self, pepper: str, *, prefix: str = "sub_") -> None:
        if not pepper:
            raise ValueError("pseudonym_pepper_required")
        self._pepper = pepper.encode("utf-8")
        self.prefix = prefix

    def subject_id(self, worker_id: str) -> str:
        digest = hmac.new(self._pepper, worker_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
        return f"{self.prefix}{digest}"

    def encounter_id(self, encounter_id: str) -> str:
        digest = hmac.new(self._pepper, f"enc:{encounter_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:24]
        return f"enc_{digest}"


@lru_cache
def get_pseudonymizer() -> Pseudonymizer | None:
    settings = get_resolved_settings()
    pepper = settings.pseudonym_pepper
    if not pepper:
        # Dev fallback: deterministic but clearly non-production
        pepper = settings.model_signing_secret or "ukz16-dev-pseudonym-pepper"
        if not get_settings().pseudonym_pepper and pepper == "ukz16-dev-pseudonym-pepper":
            pass
    return Pseudonymizer(pepper)
