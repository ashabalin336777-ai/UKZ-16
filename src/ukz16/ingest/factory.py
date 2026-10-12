from __future__ import annotations

from pathlib import Path

from ukz16.config import Settings, get_settings
from ukz16.ingest.base import IngestAdapter
from ukz16.ingest.fixture_adapter import FixtureEcozAdapter
from ukz16.ingest.http_adapter import HttpEcozAdapter
from ukz16.ingest.mock import MockEcozAdapter


def build_ingest_adapter(settings: Settings | None = None) -> IngestAdapter:
    cfg = settings or get_settings()
    mode = (cfg.ingest_mode or "mock").lower()
    if mode == "http":
        if not cfg.ecoz_base_url:
            raise RuntimeError("UKZ16_ECOZ_BASE_URL required when ingest_mode=http")
        return HttpEcozAdapter(cfg.ecoz_base_url, token=cfg.ecoz_token, timeout_s=cfg.ecoz_timeout_s)
    if mode == "fixture":
        return FixtureEcozAdapter(Path(cfg.ecoz_fixtures_dir))
    return MockEcozAdapter()
