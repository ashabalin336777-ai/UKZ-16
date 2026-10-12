from __future__ import annotations

from typing import Any

from ukz16.experimental.signals import ExperimentalFeature


def extract_voice_svs_feature(voice_payload: dict[str, Any] | None) -> ExperimentalFeature:
    """Experimental voice / SVS feature from precomputed acoustics. Never enters hMental.

    Accepts research feature dict (openSMILE/other upstream), not raw audio:
    - f0_hz, jitter_pct, shimmer_pct, hnr_db (optional subset)
    - or svs_score in 0..1 from an external research pipeline
    """
    if not voice_payload:
        return ExperimentalFeature(name="voice_SVS", reason="experimental_pipeline_not_enabled")
    if not voice_payload.get("consent_scope"):
        return ExperimentalFeature(name="voice_SVS", reason="consent_required_for_experimental_signal")
    consent = str(voice_payload.get("consent_scope"))
    protocol = voice_payload.get("protocol_version")
    device_id = voice_payload.get("device_id")
    if voice_payload.get("quality_status") in {"reject", "bad"}:
        return ExperimentalFeature(
            name="voice_SVS",
            quality_status="reject",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="bad_signal_quality",
        )

    if voice_payload.get("svs_score") is not None:
        score = float(voice_payload["svs_score"])
        if not (0.0 <= score <= 1.0):
            return ExperimentalFeature(
                name="voice_SVS",
                quality_status="reject",
                consent_scope=consent,
                protocol_version=protocol,
                device_id=device_id,
                reason="svs_score_out_of_range",
            )
        return ExperimentalFeature(
            name="voice_SVS",
            status="experimental",
            value=round(score, 6),
            quality_status="ok",
            protocol_version=protocol,
            device_id=device_id,
            consent_scope=consent,
            diagnostic_value=False,
            enters_health_id=False,
            enters_hMental=False,
            reason="experimental_voice_svs_passthrough",
        )

    # Lightweight composite from common acoustic scalars (research scaffold)
    parts: list[float] = []
    if voice_payload.get("f0_hz") is not None:
        f0 = float(voice_payload["f0_hz"])
        # Map 80–300 Hz speech band into 0..1 mid preference ~160 Hz
        parts.append(max(0.0, min(1.0, 1.0 - abs(f0 - 160.0) / 140.0)))
    if voice_payload.get("jitter_pct") is not None:
        jitter = float(voice_payload["jitter_pct"])
        parts.append(max(0.0, min(1.0, 1.0 - jitter / 5.0)))
    if voice_payload.get("shimmer_pct") is not None:
        shimmer = float(voice_payload["shimmer_pct"])
        parts.append(max(0.0, min(1.0, 1.0 - shimmer / 10.0)))
    if voice_payload.get("hnr_db") is not None:
        hnr = float(voice_payload["hnr_db"])
        parts.append(max(0.0, min(1.0, hnr / 30.0)))

    if len(parts) < 2:
        return ExperimentalFeature(
            name="voice_SVS",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="insufficient_voice_features",
        )

    value = sum(parts) / len(parts)
    return ExperimentalFeature(
        name="voice_SVS",
        status="experimental",
        value=round(value, 6),
        quality_status="ok",
        protocol_version=protocol,
        device_id=device_id,
        consent_scope=consent,
        diagnostic_value=False,
        enters_health_id=False,
        enters_hMental=False,
        reason="experimental_voice_svs_computed",
    )


def voice_trace_extras(feature: ExperimentalFeature, voice_payload: dict[str, Any] | None) -> dict[str, Any]:
    extras = feature.to_dict()
    if not voice_payload:
        return extras
    for key in ("f0_hz", "jitter_pct", "shimmer_pct", "hnr_db", "svs_score"):
        if voice_payload.get(key) is not None:
            extras[key] = float(voice_payload[key])
    return extras
