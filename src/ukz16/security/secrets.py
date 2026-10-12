from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ukz16.config import get_settings
from ukz16.security.vault import VaultClient


@dataclass
class SecretStore:
    """Resolve secrets from Vault KV v2 when configured, else process env.

    Prefer `UKZ16_VAULT_SECRET_MAP` + `apply_vault_overrides` for typed settings.
    This store is for ad-hoc key lookup (never logs values).
    """

    vault_addr: str | None
    vault_token: str | None
    vault_mount: str
    vault_path: str

    def get(self, key: str, default: str | None = None) -> str | None:
        if self.vault_addr and self.vault_token:
            value = self._from_vault(key)
            if value is not None:
                return value
        for env_key in (key, f"UKZ16_{key.upper()}", key.upper()):
            if env_key in os.environ:
                return os.environ[env_key]
        return default

    def _from_vault(self, key: str) -> str | None:
        assert self.vault_addr and self.vault_token
        client = VaultClient(self.vault_addr, self.vault_token, mount=self.vault_mount)
        try:
            data: dict[str, Any] = client.read_kv(self.vault_path)
            value = data.get(key)
            if value is None:
                # allow short aliases without UKZ16_ prefix
                value = data.get(key.removeprefix("UKZ16_"))
            return None if value is None else str(value)
        except Exception:
            return None
        finally:
            client.close()


@lru_cache
def get_secret_store() -> SecretStore:
    settings = get_settings()
    return SecretStore(
        vault_addr=settings.vault_addr,
        vault_token=settings.vault_token,
        vault_mount=settings.vault_mount,
        vault_path=settings.vault_path,
    )


def resolve_runtime_secrets() -> dict[str, str | None]:
    """Materialize commonly used secrets without printing them."""
    store = get_secret_store()
    settings = get_settings()
    return {
        "ecoz_token": settings.ecoz_token or store.get("ECOZ_TOKEN") or store.get("ecoz_token"),
        "model_signing_secret": (
            settings.model_signing_secret
            or store.get("MODEL_SIGNING_SECRET")
            or store.get("model_signing_secret")
        ),
        "oidc_client_secret": store.get("OIDC_CLIENT_SECRET"),
    }
