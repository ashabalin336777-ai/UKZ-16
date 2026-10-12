from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from typing import Any

from ukz16.governance.model_registry import ModelPackage, load_model_package
from ukz16.governance.signing import (
    COSIGN_BUNDLE,
    COSIGN_README,
    DIGEST_FILE,
    _canonical_package_bytes,
)


def write_cosign_digest(version: str) -> dict[str, Any]:
    """Write deterministic digest artifact for `cosign sign-blob`."""
    pkg = load_model_package(version, enforce_signature=False)
    digest_bytes = _canonical_package_bytes(pkg.path)
    digest_hex = hashlib.sha256(digest_bytes).hexdigest()
    digest_path = pkg.path / DIGEST_FILE
    digest_path.write_bytes(digest_bytes)
    readme = "\n".join(
        [
            f"# Cosign signing for {pkg.version}",
            "",
            "Research bridge to Sigstore/Cosign. Do not commit private keys.",
            "",
            "```bash",
            f"cosign sign-blob --bundle {COSIGN_BUNDLE} {DIGEST_FILE}",
            f"cosign verify-blob --bundle {COSIGN_BUNDLE} {DIGEST_FILE}",
            "```",
            "",
            f"package_hash: `{pkg.package_hash}`",
            f"digest_sha256: `{digest_hex}`",
            "",
        ]
    )
    (pkg.path / COSIGN_README).write_text(readme, encoding="utf-8")
    return {
        "version": pkg.version,
        "package_hash": pkg.package_hash,
        "alg": "cosign-digest",
        "digest_file": str(digest_path),
        "digest_sha256": digest_hex,
        "bundle_file": COSIGN_BUNDLE,
        "cosign_available": shutil.which("cosign") is not None,
        "auto_update": False,
        "note": "Digest written for external cosign sign-blob; HMAC package.sig unused in cosign mode.",
    }


def verify_cosign_bundle(package: ModelPackage) -> dict[str, Any]:
    digest_path = package.path / DIGEST_FILE
    bundle_path = package.path / COSIGN_BUNDLE
    if not digest_path.exists():
        return {"verified": False, "reason": "digest_missing", "alg": "cosign"}

    expected = _canonical_package_bytes(package.path)
    on_disk = digest_path.read_bytes()
    if not hmac_digest_equal(expected, on_disk):
        return {
            "verified": False,
            "reason": "digest_mismatch",
            "alg": "cosign",
            "package_hash": package.package_hash,
            "auto_update": False,
        }

    if not bundle_path.exists():
        return {
            "verified": False,
            "reason": "cosign_bundle_missing",
            "alg": "cosign",
            "digest_ok": True,
            "package_hash": package.package_hash,
            "auto_update": False,
        }

    cosign = shutil.which("cosign")
    if cosign is None:
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except Exception:
            return {"verified": False, "reason": "bundle_unreadable", "alg": "cosign"}
        ok = isinstance(bundle, dict) and bool(bundle)
        return {
            "verified": ok,
            "reason": None if ok else "empty_bundle",
            "alg": "cosign",
            "mode": "structural_only",
            "digest_ok": True,
            "package_hash": package.package_hash,
            "auto_update": False,
        }
    try:
        proc = subprocess.run(
            [cosign, "verify-blob", "--bundle", str(bundle_path), str(digest_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        return {
            "verified": ok,
            "reason": None if ok else "cosign_verify_failed",
            "alg": "cosign",
            "mode": "cosign_cli",
            "digest_ok": True,
            "package_hash": package.package_hash,
            "auto_update": False,
        }
    except Exception:
        return {"verified": False, "reason": "cosign_exec_error", "alg": "cosign"}


def hmac_digest_equal(a: bytes, b: bytes) -> bool:
    import hmac

    return hmac.compare_digest(a, b)
