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
    """HRV/rPPG/voice experimental features. Never feed hMental or HEALTH_ID.

    HRV may compute a research score from NN intervals (optional NeuroKit2).
    rPPG / voice_SVS remain protocol placeholders until validated pipelines land.
    """
    payload = payload or {}
    signals = payload.get("experimental_signals") or {}
    from ukz16.experimental.hrv import extract_hrv_feature

    return [
        extract_hrv_feature(signals.get("hrv")),
        _placeholder("rPPG", signals, "rppg"),
        _placeholder("voice_SVS", signals, "voice"),
    ]


def _placeholder(name: str, signals: dict[str, Any], key: str) -> ExperimentalFeature:
    if key not in signals:
        return ExperimentalFeature(name=name, reason="experimental_pipeline_not_enabled")
    item = signals[key] or {}
    if not item.get("consent_scope"):
        return ExperimentalFeature(name=name, reason="consent_required_for_experimental_signal")
    if item.get("quality_status") in {"reject", "bad"}:
        return ExperimentalFeature(
            name=name,
            quality_status="reject",
            consent_scope=str(item.get("consent_scope")),
            reason="bad_signal_quality",
        )
    return ExperimentalFeature(
        name=name,
        consent_scope=str(item.get("consent_scope")),
        protocol_version=item.get("protocol_version"),
        device_id=item.get("device_id"),
        reason="awaiting_validated_protocol",
    )
