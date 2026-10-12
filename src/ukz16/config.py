from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UKZ16_", env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'ukz16.db'}"
    use_sqlite: bool = True
    model_version: str = "research-v0.1"
    models_dir: Path = ROOT / "models" / "health_id"
    docs_dir: Path = ROOT / "docs"
    # role:key pairs comma-separated
    api_keys: str = "researcher:researcher-key,medical_worker:medical-key,auditor:auditor-key"

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
