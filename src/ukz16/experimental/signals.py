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
    """Return experimental HRV/rPPG/voice placeholders.

    Real NeuroKit2 / rPPG-Toolbox / openSMILE pipelines plug in here later.
    They must remain experimental and must not feed hMental or HEALTH_ID.
    """
    payload = payload or {}
    signals = payload.get("experimental_signals") or {}
    features = [
        ExperimentalFeature(name="HRV", reason=_reason(signals, "hrv")),
        ExperimentalFeature(name="rPPG", reason=_reason(signals, "rppg")),
        ExperimentalFeature(name="voice_SVS", reason=_reason(signals, "voice")),
    ]
    return features


def _reason(signals: dict[str, Any], key: str) -> str:
    if key not in signals:
        return "experimental_pipeline_not_enabled"
    item = signals[key] or {}
    if not item.get("consent_scope"):
        return "consent_required_for_experimental_signal"
    if item.get("quality_status") in {"reject", "bad"}:
        return "bad_signal_quality"
    return "awaiting_validated_protocol"
