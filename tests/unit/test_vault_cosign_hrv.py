from __future__ import annotations

import json

import httpx
import respx

from ukz16.config import get_settings
from ukz16.experimental.hrv import extract_hrv_feature
from ukz16.experimental.signals import extract_experimental_features
from ukz16.governance.cosign_bridge import verify_cosign_bundle, write_cosign_digest
from ukz16.governance.model_registry import load_model_package
from ukz16.governance.signing import DIGEST_FILE, sign_model_package, verify_model_package
from ukz16.security.vault import VaultClient, apply_vault_overrides, resolve_secrets_into_environ
from ukz16.config import Settings


def test_vault_kv_read_and_overrides(monkeypatch):
    monkeypatch.setenv("UKZ16_VAULT_ADDR", "https://vault.test")
    monkeypatch.setenv("UKZ16_VAULT_TOKEN", "t")
    monkeypatch.setenv("UKZ16_VAULT_MOUNT", "secret")
    monkeypatch.setenv(
        "UKZ16_VAULT_SECRET_MAP",
        "ecoz_token:ukz16/ecoz#token,model_signing_secret:ukz16/signing#hmac",
    )
    get_settings.cache_clear()

    with respx.mock:
        respx.get("https://vault.test/v1/secret/data/ukz16/ecoz").mock(
            return_value=httpx.Response(200, json={"data": {"data": {"token": "from-vault"}}})
        )
        respx.get("https://vault.test/v1/secret/data/ukz16/signing").mock(
            return_value=httpx.Response(200, json={"data": {"data": {"hmac": "vault-hmac"}}})
        )
        cfg = Settings(
            vault_addr="https://vault.test",
            vault_token="t",
            vault_mount="secret",
            vault_secret_map="ecoz_token:ukz16/ecoz#token,model_signing_secret:ukz16/signing#hmac",
        )
        secrets = resolve_secrets_into_environ(cfg)
        assert secrets["ecoz_token"] == "from-vault"
        assert secrets["model_signing_secret"] == "vault-hmac"
        overlay = apply_vault_overrides(cfg)
        assert overlay.ecoz_token == "from-vault"
        assert overlay.model_signing_secret == "vault-hmac"

        client = VaultClient("https://vault.test", "t", mount="secret")
        assert client.read_kv("ukz16/ecoz")["token"] == "from-vault"
        client.close()

    get_settings.cache_clear()


def test_cosign_digest_bridge(monkeypatch):
    monkeypatch.setenv("UKZ16_SIGNING_MODE", "cosign")
    get_settings.cache_clear()
    pkg = load_model_package("research-v0.2", enforce_signature=False)
    digest_path = pkg.path / DIGEST_FILE
    readme = pkg.path / "COSIGN.md"
    bundle = pkg.path / "package.sig.bundle"
    try:
        doc = write_cosign_digest("research-v0.2")
        assert doc["alg"] == "cosign-digest"
        assert digest_path.exists()
        assert readme.exists()
        # Without bundle: digest matches but verify fails until cosign signs
        missing = verify_cosign_bundle(pkg)
        assert missing["reason"] == "cosign_bundle_missing"
        assert missing.get("digest_ok") is True
        bundle.write_text(json.dumps({"mediaType": "application/vnd.dev.cosign.bundle+json"}), encoding="utf-8")
        structural = verify_cosign_bundle(pkg)
        assert structural["verified"] is True
        assert structural["mode"] == "structural_only"

        monkeypatch.setenv("UKZ16_SIGNING_MODE", "cosign")
        get_settings.cache_clear()
        via_signing = sign_model_package("research-v0.2")
        assert via_signing["digest_sha256"]
        verified = verify_model_package(pkg)
        assert verified["verified"] is True
    finally:
        for path in (digest_path, readme, bundle):
            if path.exists():
                path.unlink()
        get_settings.cache_clear()


def test_hrv_experimental_from_nn_intervals():
    feat = extract_hrv_feature(
        {
            "consent_scope": "research_hrv",
            "nn_intervals_ms": [800, 820, 790, 810, 805],
            "protocol_version": "hrv-r0",
            "device_id": "PPG-1",
        }
    )
    assert feat.name == "HRV"
    assert feat.status == "experimental"
    assert feat.enters_health_id is False
    assert feat.enters_hMental is False
    assert feat.value is not None
    assert feat.reason == "experimental_hrv_computed"

    features = extract_experimental_features(
        {
            "experimental_signals": {
                "hrv": {
                    "consent_scope": "research_hrv",
                    "nn_intervals_ms": [800, 820, 790, 810],
                }
            }
        }
    )
    assert features[0].value is not None
    assert features[1].name == "rPPG"
    assert features[1].reason == "experimental_pipeline_not_enabled"


def test_hrv_requires_consent():
    feat = extract_hrv_feature({"nn_intervals_ms": [800, 810, 820]})
    assert feat.value is None
    assert feat.reason == "consent_required_for_experimental_signal"
