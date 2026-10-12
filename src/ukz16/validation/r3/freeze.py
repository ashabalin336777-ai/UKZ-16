from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ukz16.governance.model_registry import load_model_package


def freeze_model_for_r3(
    *,
    output_path: Path,
    model_version: str | None = None,
    sites: list[str] | None = None,
    protocol_id: str = "R3_EXTERNAL_v1",
) -> dict[str, Any]:
    """Freeze model package identity before external enrollment (TZ R3 gate)."""
    pkg = load_model_package(model_version, enforce_signature=False)
    doc = {
        "stage": "R3",
        "protocol_id": protocol_id,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "model_version": pkg.version,
        "model_package_hash": pkg.package_hash,
        "sites_planned": sites or [],
        "auto_update_forbidden": True,
        "diagnosis_claim": False,
        "notes": [
            "Model must not change after freeze without new R3 protocol version.",
            "External sites enroll only against this package hash.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def load_freeze(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_model_matches_freeze(freeze: dict[str, Any], model_version: str | None = None) -> dict[str, Any]:
    pkg = load_model_package(model_version or freeze.get("model_version"), enforce_signature=False)
    ok = pkg.version == freeze.get("model_version") and pkg.package_hash == freeze.get("model_package_hash")
    return {
        "ok": ok,
        "expected_version": freeze.get("model_version"),
        "expected_hash": freeze.get("model_package_hash"),
        "actual_version": pkg.version,
        "actual_hash": pkg.package_hash,
        "auto_update": False,
    }
