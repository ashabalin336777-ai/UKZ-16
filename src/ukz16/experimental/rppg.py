from __future__ import annotations

from statistics import mean
from typing import Any

from ukz16.experimental.signals import ExperimentalFeature


def _peak_indices(signal: list[float], min_distance: int) -> list[int]:
    if len(signal) < 3 or min_distance < 1:
        return []
    peaks: list[int] = []
    last = -min_distance
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] > signal[i + 1] and (i - last) >= min_distance:
            peaks.append(i)
            last = i
    return peaks


def extract_rppg_feature(rppg_payload: dict[str, Any] | None) -> ExperimentalFeature:
    """Experimental rPPG feature from waveform or BPM estimate. Never enters HEALTH_ID.

    Accepts:
    - signal: list[float] + sampling_rate (Hz), or
    - bpm_estimate: float (research device pre-estimate)
    """
    if not rppg_payload:
        return ExperimentalFeature(name="rPPG", reason="experimental_pipeline_not_enabled")
    if not rppg_payload.get("consent_scope"):
        return ExperimentalFeature(name="rPPG", reason="consent_required_for_experimental_signal")
    consent = str(rppg_payload.get("consent_scope"))
    protocol = rppg_payload.get("protocol_version")
    device_id = rppg_payload.get("device_id")
    if rppg_payload.get("quality_status") in {"reject", "bad"}:
        return ExperimentalFeature(
            name="rPPG",
            quality_status="reject",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="bad_signal_quality",
        )

    bpm: float | None = None
    raw = rppg_payload.get("signal")
    if isinstance(raw, list) and len(raw) >= 16:
        fs = float(rppg_payload.get("sampling_rate") or 30.0)
        if fs <= 0:
            return ExperimentalFeature(
                name="rPPG",
                consent_scope=consent,
                protocol_version=protocol,
                device_id=device_id,
                reason="invalid_sampling_rate",
            )
        signal = [float(x) for x in raw]
        # Detrend by mean for simple peak finder
        mu = mean(signal)
        centered = [x - mu for x in signal]
        min_distance = max(1, int(fs * 0.4))  # ~150 bpm ceiling
        peaks = _peak_indices(centered, min_distance)
        if len(peaks) < 3:
            return ExperimentalFeature(
                name="rPPG",
                consent_scope=consent,
                protocol_version=protocol,
                device_id=device_id,
                reason="insufficient_rppg_peaks",
            )
        intervals = [(peaks[i + 1] - peaks[i]) / fs for i in range(len(peaks) - 1)]
        clean = [iv for iv in intervals if 0.33 <= iv <= 1.5]  # 40–180 bpm
        if len(clean) < 2:
            return ExperimentalFeature(
                name="rPPG",
                quality_status="reject",
                consent_scope=consent,
                protocol_version=protocol,
                device_id=device_id,
                reason="rppg_intervals_out_of_band",
            )
        bpm = 60.0 / mean(clean)
    elif rppg_payload.get("bpm_estimate") is not None:
        bpm = float(rppg_payload["bpm_estimate"])
    else:
        return ExperimentalFeature(
            name="rPPG",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="insufficient_rppg_signal",
        )

    if bpm is None or not (40.0 <= bpm <= 180.0):
        return ExperimentalFeature(
            name="rPPG",
            quality_status="reject",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="bpm_out_of_physiological_band",
        )

    # Research score: proximity to 60–80 bpm resting band → higher
    if bpm <= 70:
        value = max(0.0, min(1.0, 1.0 - abs(bpm - 70.0) / 30.0))
    else:
        value = max(0.0, min(1.0, 1.0 - abs(bpm - 70.0) / 50.0))

    return ExperimentalFeature(
        name="rPPG",
        status="experimental",
        value=round(value, 6),
        quality_status="ok",
        protocol_version=protocol,
        device_id=device_id,
        consent_scope=consent,
        diagnostic_value=False,
        enters_health_id=False,
        enters_hMental=False,
        reason="experimental_rppg_computed",
    )


def rppg_trace_extras(feature: ExperimentalFeature, rppg_payload: dict[str, Any] | None) -> dict[str, Any]:
    extras = feature.to_dict()
    if not rppg_payload:
        return extras
    if rppg_payload.get("bpm_estimate") is not None:
        extras["bpm_estimate"] = float(rppg_payload["bpm_estimate"])
    raw = rppg_payload.get("signal")
    if isinstance(raw, list) and len(raw) >= 16:
        fs = float(rppg_payload.get("sampling_rate") or 30.0)
        mu = mean(float(x) for x in raw)
        signal = [float(x) - mu for x in raw]
        peaks = _peak_indices(signal, max(1, int(fs * 0.4)))
        if len(peaks) >= 3:
            intervals = [(peaks[i + 1] - peaks[i]) / fs for i in range(len(peaks) - 1)]
            clean = [iv for iv in intervals if 0.33 <= iv <= 1.5]
            if clean:
                extras["bpm_from_signal"] = round(60.0 / mean(clean), 4)
                extras["n_peaks"] = len(peaks)
    return extras
