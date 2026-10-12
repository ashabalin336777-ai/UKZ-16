from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from ukz16.config import get_settings
from ukz16.governance.model_registry import ModelPackage, load_model_package


SIGNATURE_FILE = "package.sig"
DIGEST_FILE = "package.digest"
COSIGN_BUNDLE = "package.sig.bundle"
COSIGN_README = "COSIGN.md"
_SIGNING_ARTIFACTS = frozenset({SIGNATURE_FILE, DIGEST_FILE, COSIGN_BUNDLE, COSIGN_README})


def _canonical_package_bytes(package_dir: Path) -> bytes:
    parts: list[tuple[str, bytes]] = []
    for path in sorted(package_dir.iterdir()):
        if not path.is_file() or path.name in _SIGNING_ARTIFACTS:
            continue
        parts.append((path.name, path.read_bytes()))
    payload = [{"name": n, "sha256": hashlib.sha256(b).hexdigest()} for n, b in parts]
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _resolve_signing_secret(secret: str | None) -> str | None:
    if secret:
        return secret
    from ukz16.config import get_resolved_settings
    from ukz16.security.secrets import resolve_runtime_secrets

    settings = get_resolved_settings()
    if settings.model_signing_secret:
        return settings.model_signing_secret
    return resolve_runtime_secrets().get("model_signing_secret")


def sign_model_package(version: str, secret: str | None = None) -> dict[str, Any]:
    from ukz16.config import get_resolved_settings

    settings = get_resolved_settings()
    if (settings.signing_mode or "hmac").lower() == "cosign":
        from ukz16.governance.cosign_bridge import write_cosign_digest

        return write_cosign_digest(version)

    key = _resolve_signing_secret(secret)
    if not key:
        raise RuntimeError("model_signing_secret_required")
    pkg = load_model_package(version, enforce_signature=False)
    digest = _canonical_package_bytes(pkg.path)
    signature = hmac.new(key.encode(), digest, hashlib.sha256).hexdigest()
    sig_doc = {
        "version": pkg.version,
        "alg": "HMAC-SHA256",
        "package_hash": pkg.package_hash,
        "signature": signature,
        "note": "Research HMAC signing. Prefer signing_mode=cosign for production releases.",
    }
    (pkg.path / SIGNATURE_FILE).write_text(json.dumps(sig_doc, indent=2) + "\n", encoding="utf-8")
    return sig_doc


def verify_model_package(package: ModelPackage, secret: str | None = None) -> dict[str, Any]:
    from ukz16.config import get_resolved_settings

    settings = get_resolved_settings()
    if (settings.signing_mode or "hmac").lower() == "cosign":
        from ukz16.governance.cosign_bridge import verify_cosign_bundle

        return verify_cosign_bundle(package)

    key = _resolve_signing_secret(secret)
    sig_path = package.path / SIGNATURE_FILE
    if not sig_path.exists():
        return {"verified": False, "reason": "signature_missing"}
    if not key:
        return {"verified": False, "reason": "signing_secret_missing"}
    sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
    digest = _canonical_package_bytes(package.path)
    expected = hmac.new(key.encode(), digest, hashlib.sha256).hexdigest()
    ok = hmac.compare_digest(expected, sig_doc.get("signature", ""))
    return {
        "verified": ok,
        "reason": None if ok else "signature_mismatch",
        "alg": sig_doc.get("alg"),
        "package_hash": package.package_hash,
        "auto_update": False,
    }


def ensure_model_signature(package: ModelPackage) -> None:
    settings = get_settings()
    if not settings.require_signed_model:
        return
    result = verify_model_package(package)
    if not result.get("verified"):
        raise RuntimeError(f"unsigned_or_invalid_model:{result.get('reason')}")
