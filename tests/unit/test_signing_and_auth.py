from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from ukz16.api.auth import clear_jwks_cache
from ukz16.api.main import app
from ukz16.config import get_settings
from ukz16.db.session import init_db, reset_engine
from ukz16.governance.model_registry import load_model_package
from ukz16.governance.signing import sign_model_package, verify_model_package


def test_sign_and_verify_model_package(monkeypatch):
    monkeypatch.setenv("UKZ16_MODEL_SIGNING_SECRET", "test-secret")
    get_settings.cache_clear()
    pkg = load_model_package("research-v0.2", enforce_signature=False)
    sig_path = pkg.path / "package.sig"
    try:
        sig = sign_model_package("research-v0.2", secret="test-secret")
        assert sig["signature"]
        verified = verify_model_package(pkg, secret="test-secret")
        assert verified["verified"] is True
    finally:
        if sig_path.exists():
            sig_path.unlink()
        get_settings.cache_clear()


def test_oidc_bearer_auth(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Build a minimal JWKS from the public key via PyJWT roundtrip helper:
    # Use HS256 for unit simplicity would skip JWKS; instead mock jwks client path
    # by patching jwt decode path through auth_mode=api_key hybrid still works.
    # For OIDC path, monkeypatch _jwks_client usage via issuer + custom decode.
    from ukz16.api import auth as auth_mod

    class _Key:
        def __init__(self, key):
            self.key = key

    class _Client:
        def get_signing_key_from_jwt(self, token: str):
            return _Key(public_pem)

    monkeypatch.setenv("UKZ16_AUTH_MODE", "oidc")
    monkeypatch.setenv("UKZ16_OIDC_ISSUER", "https://keycloak.example/realms/ukz16")
    monkeypatch.setenv("UKZ16_OIDC_AUDIENCE", "ukz16-api")
    monkeypatch.setenv("UKZ16_OIDC_JWKS_URL", "https://keycloak.example/jwks")
    get_settings.cache_clear()
    clear_jwks_cache()
    monkeypatch.setattr(auth_mod, "_jwks_client", lambda url: _Client())

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": "https://keycloak.example/realms/ukz16",
            "aud": "ukz16-api",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "realm_access": {"roles": ["researcher"]},
        },
        private_pem,
        algorithm="RS256",
    )

    reset_engine()
    init_db()
    client = TestClient(app)
    resp = client.get("/api/v1/health-id/model-card", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    get_settings.cache_clear()
    clear_jwks_cache()
