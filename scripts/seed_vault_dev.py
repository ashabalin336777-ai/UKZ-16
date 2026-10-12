#!/usr/bin/env python3
"""Seed Hashicorp Vault (dev) with UKZ-16 research secrets.

Usage:
  set VAULT_ADDR=http://127.0.0.1:8200
  set VAULT_TOKEN=ukz16-dev-root
  python scripts/seed_vault_dev.py
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx


def put_kv(addr: str, token: str, mount: str, path: str, data: dict[str, str]) -> None:
    url = f"{addr.rstrip('/')}/v1/{mount.strip('/')}/data/{path.strip('/')}"
    response = httpx.post(
        url,
        headers={"X-Vault-Token": token},
        json={"data": data},
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise SystemExit(f"vault_put_failed {path}: {response.status_code} {response.text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed Vault KV for UKZ-16 local/dev")
    parser.add_argument("--addr", default=os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200"))
    parser.add_argument("--token", default=os.environ.get("VAULT_TOKEN", "ukz16-dev-root"))
    parser.add_argument("--mount", default="secret")
    args = parser.parse_args(argv)

    put_kv(args.addr, args.token, args.mount, "ukz16/ecoz", {"token": "dev-ecoz-token"})
    put_kv(args.addr, args.token, args.mount, "ukz16/signing", {"hmac": "dev-hmac-secret"})
    print("Seeded secret/ukz16/ecoz#token and secret/ukz16/signing#hmac")
    print("Map: UKZ16_VAULT_SECRET_MAP=ecoz_token:ukz16/ecoz#token,model_signing_secret:ukz16/signing#hmac")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
