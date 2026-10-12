from __future__ import annotations

from typing import Any

import httpx

from ukz16.config import Settings, get_settings


class VaultClient:
    """Hashicorp Vault KV v2 reader for research/ops secrets.

    Local/dev can keep using env vars. Production sets UKZ16_VAULT_ADDR + token.
    """

    def __init__(
        self,
        addr: str,
        token: str,
        *,
        mount: str = "secret",
        timeout_s: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.addr = addr.rstrip("/")
        self.token = token
        self.mount = mount.strip("/")
        self.timeout_s = timeout_s
        self._client = client
        self._owned = client is None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.addr,
                headers={"X-Vault-Token": self.token},
                timeout=self.timeout_s,
            )
        return self._client

    def close(self) -> None:
        if self._owned and self._client is not None:
            self._client.close()
            self._client = None

    def read_kv(self, path: str) -> dict[str, Any]:
        """Read KV v2 secret data at mount/data/{path}."""
        path = path.strip("/")
        response = self._http().get(f"/v1/{self.mount}/data/{path}")
        if response.status_code == 404:
            raise KeyError(f"vault_secret_not_found:{self.mount}/{path}")
        response.raise_for_status()
        body = response.json()
        data = ((body.get("data") or {}).get("data")) or {}
        if not isinstance(data, dict):
            raise ValueError("vault_invalid_secret_payload")
        return data


def resolve_secrets_into_environ(settings: Settings | None = None) -> dict[str, str]:
    """Fetch configured Vault paths and return key->value map (does not mutate OS env).

    Mapping config (comma-separated UKZ16_VAULT_SECRET_MAP):
      ecoz_token:ukz16/ecoz#token,model_signing_secret:ukz16/signing#hmac
    Means: settings field / logical name <- vault path # key
    """
    cfg = settings or get_settings()
    resolved: dict[str, str] = {}
    if not cfg.vault_addr or not cfg.vault_token or not cfg.vault_secret_map:
        return resolved

    client = VaultClient(cfg.vault_addr, cfg.vault_token, mount=cfg.vault_mount)
    try:
        for item in cfg.vault_secret_map.split(","):
            item = item.strip()
            if not item or ":" not in item or "#" not in item:
                continue
            logical, rest = item.split(":", 1)
            path, key = rest.split("#", 1)
            try:
                data = client.read_kv(path.strip())
            except Exception:
                continue
            value = data.get(key.strip())
            if value is None:
                continue
            resolved[logical.strip()] = str(value)
    finally:
        client.close()
    return resolved


def apply_vault_overrides(settings: Settings | None = None) -> Settings:
    """Return settings with Vault-resolved secrets overlayed onto critical fields."""
    cfg = settings or get_settings()
    secrets = resolve_secrets_into_environ(cfg)
    if not secrets:
        return cfg
    updates: dict[str, Any] = {}
    if "ecoz_token" in secrets:
        updates["ecoz_token"] = secrets["ecoz_token"]
    if "model_signing_secret" in secrets:
        updates["model_signing_secret"] = secrets["model_signing_secret"]
    if "api_keys" in secrets:
        updates["api_keys"] = secrets["api_keys"]
    if "oidc_audience" in secrets:
        updates["oidc_audience"] = secrets["oidc_audience"]
    if "pseudonym_pepper" in secrets:
        updates["pseudonym_pepper"] = secrets["pseudonym_pepper"]
    if updates:
        return cfg.model_copy(update=updates)
    return cfg
