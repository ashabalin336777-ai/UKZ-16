from __future__ import annotations

from pathlib import Path

from ukz16.ingest.fixture_adapter import FixtureEcozAdapter


def test_fixture_adapter_loads_sample(tmp_path: Path):
    src = Path("samples/prmo_ok.json")
    target = tmp_path / "ENC-001.json"
    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    adapter = FixtureEcozAdapter(tmp_path)
    payload = adapter.fetch_encounter("ENC-001")
    assert payload.encounter_id == "ENC-001"
    assert payload.consent_research is True
