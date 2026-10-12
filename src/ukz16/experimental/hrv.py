from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from ukz16.experimental.signals import ExperimentalFeature


def _rmssd(nn_ms: list[float]) -> float | None:
    if len(nn_ms) < 3:
        return None
    diffs = [nn_ms[i + 1] - nn_ms[i] for i in range(len(nn_ms) - 1)]
    return (sum(d * d for d in diffs) / len(diffs)) ** 0.5


def _sdnn(nn_ms: list[float]) -> float | None:
    if len(nn_ms) < 2:
        return None
    return pstdev(nn_ms)


def extract_hrv_feature(hrv_payload: dict[str, Any] | None) -> ExperimentalFeature:
    """Experimental HRV feature. Never enters HEALTH_ID / hMental.

    Accepts:
    - nn_intervals_ms: list[float]
    - optional use_neurokit + signal/sampling_rate if neurokit2 installed
    """
    if not hrv_payload:
        return ExperimentalFeature(name="HRV", reason="experimental_pipeline_not_enabled")
    if not hrv_payload.get("consent_scope"):
        return ExperimentalFeature(name="HRV", reason="consent_required_for_experimental_signal")
    if hrv_payload.get("quality_status") in {"reject", "bad"}:
        return ExperimentalFeature(
            name="HRV",
            quality_status="reject",
            consent_scope=str(hrv_payload.get("consent_scope")),
            reason="bad_signal_quality",
        )

    nn = hrv_payload.get("nn_intervals_ms")
    protocol = hrv_payload.get("protocol_version")
    device_id = hrv_payload.get("device_id")
    consent = str(hrv_payload.get("consent_scope"))

    if hrv_payload.get("use_neurokit") and hrv_payload.get("signal") is not None:
        try:
            import neurokit2 as nk  # type: ignore

            signal = hrv_payload["signal"]
            fs = float(hrv_payload.get("sampling_rate") or 100.0)
            processed, _ = nk.ppg_process(signal, sampling_rate=fs)
            peaks = processed.get("PPG_Peaks")
            if peaks is not None:
                idx = [i for i, v in enumerate(peaks) if v]
                if len(idx) >= 3:
                    nn = [(idx[i + 1] - idx[i]) * 1000.0 / fs for i in range(len(idx) - 1)]
        except Exception:
            return ExperimentalFeature(
                name="HRV",
                consent_scope=consent,
                protocol_version=protocol,
                device_id=device_id,
                reason="neurokit_unavailable_or_failed",
            )

    if not isinstance(nn, list) or len(nn) < 3:
        return ExperimentalFeature(
            name="HRV",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="insufficient_nn_intervals",
        )

    nn_f = [float(x) for x in nn]
    # Basic artifact gate: drop intervals outside 300–2000 ms
    clean = [x for x in nn_f if 300.0 <= x <= 2000.0]
    artifact_ratio = 1.0 - (len(clean) / len(nn_f))
    if artifact_ratio > 0.2 or len(clean) < 3:
        return ExperimentalFeature(
            name="HRV",
            quality_status="reject",
            consent_scope=consent,
            protocol_version=protocol,
            device_id=device_id,
            reason="artifact_ratio_too_high",
        )

    sdnn = _sdnn(clean)
    rmssd = _rmssd(clean)
    # Research-only composite in 0..1 from RMSSD around 20–80 ms band
    value = None
    if rmssd is not None:
        value = max(0.0, min(1.0, (rmssd - 20.0) / 60.0))

    return ExperimentalFeature(
        name="HRV",
        status="experimental",
        value=None if value is None else round(value, 6),
        quality_status="ok",
        protocol_version=protocol,
        device_id=device_id,
        consent_scope=consent,
        diagnostic_value=False,
        enters_health_id=False,
        enters_hMental=False,
        reason="experimental_hrv_computed",
    )


def hrv_trace_extras(feature: ExperimentalFeature, hrv_payload: dict[str, Any] | None) -> dict[str, Any]:
    extras = feature.to_dict()
    if not hrv_payload or not isinstance(hrv_payload.get("nn_intervals_ms"), list):
        return extras
    nn = [float(x) for x in hrv_payload["nn_intervals_ms"] if 300.0 <= float(x) <= 2000.0]
    extras["sdnn_ms"] = None if len(nn) < 2 else round(_sdnn(nn) or 0.0, 4)
    extras["rmssd_ms"] = None if len(nn) < 3 else round(_rmssd(nn) or 0.0, 4)
    extras["mean_nn_ms"] = None if not nn else round(mean(nn), 4)
    return extras
