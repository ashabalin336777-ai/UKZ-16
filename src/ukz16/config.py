from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UKZ16_", env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'ukz16.db'}"
    use_sqlite: bool = True
    model_version: str = "research-v0.2"
    models_dir: Path = ROOT / "models" / "health_id"
    docs_dir: Path = ROOT / "docs"
    # role:key pairs comma-separated (dev fallback when auth_mode=api_key)
    api_keys: str = "researcher:researcher-key,medical_worker:medical-key,auditor:auditor-key"
    block_evaluation_on_drift: bool = True

    # Ingest: mock | fixture | http
    ingest_mode: str = "mock"
    ecoz_base_url: str | None = None
    ecoz_token: str | None = None
    ecoz_timeout_s: float = 10.0
    ecoz_fixtures_dir: Path = ROOT / "samples" / "ecoz"

    # Auth: api_key | oidc | hybrid (Bearer JWT preferred, API key fallback)
    auth_mode: str = "hybrid"
    oidc_issuer: str | None = None
    oidc_audience: str = "ukz16-api"
    oidc_jwks_url: str | None = None
    oidc_role_claim: str = "realm_access.roles"
    oidc_algorithms: str = "RS256"

    # Model package signing
    model_signing_secret: str | None = None
    require_signed_model: bool = False

    # Observability
    otel_enabled: bool = False
    otel_service_name: str = "ukz16-api"
    otel_exporter_otlp_endpoint: str | None = None

    def parsed_api_keys(self) -> dict[str, str]:
        """Map api_key -> role."""
        mapping: dict[str, str] = {}
        for part in self.api_keys.split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            role, key = part.split(":", 1)
            mapping[key.strip()] = role.strip()
        return mapping


@lru_cache
def get_settings() -> Settings:
    return Settings()
