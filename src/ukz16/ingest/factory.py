from __future__ import annotations

from pathlib import Path

from ukz16.config import Settings, get_resolved_settings
from ukz16.ingest.base import IngestAdapter
from ukz16.ingest.fixture_adapter import FixtureEcozAdapter
from ukz16.ingest.http_adapter import HttpEcozAdapter
from ukz16.ingest.mock import MockEcozAdapter


def build_ingest_adapter(settings: Settings | None = None) -> IngestAdapter:
    cfg = settings or get_resolved_settings()
    if cfg.ecoz_token is None:
        from ukz16.security.secrets import resolve_runtime_secrets

        token = resolve_runtime_secrets().get("ecoz_token")
        if token:
            cfg = cfg.model_copy(update={"ecoz_token": token})
    mode = (cfg.ingest_mode or "mock").lower()
    if mode == "http":
        if not cfg.ecoz_base_url:
            raise RuntimeError("UKZ16_ECOZ_BASE_URL required when ingest_mode=http")
        return HttpEcozAdapter(cfg.ecoz_base_url, token=cfg.ecoz_token, timeout_s=cfg.ecoz_timeout_s)
    if mode == "fixture":
        return FixtureEcozAdapter(Path(cfg.ecoz_fixtures_dir))
    return MockEcozAdapter()
