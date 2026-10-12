from __future__ import annotations

import httpx
import pytest
import respx

from ukz16.ingest.ecoz_mapper import map_ecoz_encounter
from ukz16.ingest.http_adapter import HttpEcozAdapter


def test_map_ecoz_observations():
    payload = {
        "subject_pseudonym": "W-1",
        "event_id": "E-1",
        "measured_at": "2026-01-01T10:00:00+00:00",
        "consent": {"research": True},
        "protocol": {"id": "PRMO_STD_v1", "version": "1.0"},
        "device": {"id": "D1"},
        "observations": [
            {"id": "i1", "metric_code": "pulse_bpm", "value": 70, "unit": "bpm"},
            {"id": "i2", "metric_code": "bp_systolic_mmhg", "value": 120, "unit": "mmHg"},
            {"id": "i3", "metric_code": "bp_diastolic_mmhg", "value": 80, "unit": "mmHg"},
        ],
    }
    mapped = map_ecoz_encounter(payload)
    assert mapped.worker_id == "W-1"
    assert mapped.vitals.pulse_bpm == 70
    assert mapped.provenance.input_ids == ["i1", "i2", "i3"]


@respx.mock
def test_http_adapter_fetch():
    route = respx.get("https://ecoz.example/encounters/E-9").mock(
        return_value=httpx.Response(
            200,
            json={
                "subject_pseudonym": "W-9",
                "event_id": "E-9",
                "measured_at": "2026-01-01T10:00:00+00:00",
                "consent": {"research": True},
                "protocol": {"id": "PRMO_STD_v1", "version": "1.0"},
                "device": {"id": "D9"},
                "observations": [
                    {"id": "a", "metric_code": "pulse_bpm", "value": 66, "unit": "bpm"},
                    {"id": "b", "metric_code": "bp_systolic_mmhg", "value": 110, "unit": "mmHg"},
                    {"id": "c", "metric_code": "bp_diastolic_mmhg", "value": 70, "unit": "mmHg"},
                ],
            },
        )
    )
    adapter = HttpEcozAdapter("https://ecoz.example", token="t")
    result = adapter.fetch_encounter("E-9")
    assert route.called
    assert result.encounter_id == "E-9"
    assert result.vitals.pulse_bpm == 66
    adapter.close()


@respx.mock
def test_http_adapter_not_found():
    respx.get("https://ecoz.example/encounters/missing").mock(return_value=httpx.Response(404))
    adapter = HttpEcozAdapter("https://ecoz.example")
    with pytest.raises(KeyError):
        adapter.fetch_encounter("missing")
    adapter.close()
