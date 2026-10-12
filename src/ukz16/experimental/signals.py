from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExperimentalFeature:
    name: str
    status: str = "experimental"
    value: float | None = None
    quality_status: str = "unavailable"
    protocol_version: str | None = None
    device_id: str | None = None
    consent_scope: str | None = None
    diagnostic_value: bool = False
    enters_health_id: bool = False
    enters_hMental: bool = False
    reason: str = "experimental_pipeline_not_enabled"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "quality_status": self.quality_status,
            "protocol_version": self.protocol_version,
            "device_id": self.device_id,
            "consent_scope": self.consent_scope,
            "diagnostic_value": self.diagnostic_value,
            "enters_health_id": self.enters_health_id,
            "enters_hMental": self.enters_hMental,
            "reason": self.reason,
        }


def extract_experimental_features(payload: dict[str, Any] | None = None) -> list[ExperimentalFeature]:
    """HRV/rPPG/voice experimental features. Never feed hMental or HEALTH_ID."""
    payload = payload or {}
    signals = payload.get("experimental_signals") or {}
    from ukz16.experimental.hrv import extract_hrv_feature
    from ukz16.experimental.rppg import extract_rppg_feature
    from ukz16.experimental.voice import extract_voice_svs_feature

    return [
        extract_hrv_feature(signals.get("hrv")),
        extract_rppg_feature(signals.get("rppg")),
        extract_voice_svs_feature(signals.get("voice")),
    ]
