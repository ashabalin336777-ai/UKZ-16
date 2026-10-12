from __future__ import annotations

from pathlib import Path
from typing import Any

from ukz16.config import get_settings
from ukz16.governance.model_registry import load_model_package


def load_model_card(version: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    pkg = load_model_package(version)
    card_path: Path = settings.docs_dir / "model_card.md"
    markdown = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
    return {
        "model_id": pkg.config["model_id"],
        "version": pkg.version,
        "status": pkg.config.get("status"),
        "intended_use": pkg.config.get("intended_use"),
        "weights": pkg.config.get("weights"),
        "policies": pkg.config.get("policies"),
        "package_hash": pkg.package_hash,
        "markdown": markdown,
        "employer_export_allowed": False,
        "diagnosis_claim": False,
        "auto_update_on_drift": False,
    }
