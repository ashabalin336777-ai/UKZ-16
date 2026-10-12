from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ukz16.config import get_settings


@dataclass(frozen=True)
class ModelPackage:
    version: str
    config: dict[str, Any]
    normals: dict[str, Any]
    package_hash: str
    path: Path


def _hash_files(*paths: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p)):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def load_model_package(version: str | None = None, *, enforce_signature: bool = True) -> ModelPackage:
    settings = get_settings()
    ver = version or settings.model_version
    root = settings.models_dir / ver
    model_path = root / "model.yaml"
    normals_path = root / "normals.yaml"
    if not model_path.exists():
        raise FileNotFoundError(f"model package not found: {root}")
    with model_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with normals_path.open(encoding="utf-8") as f:
        normals = yaml.safe_load(f)
    package_hash = _hash_files(model_path, normals_path)
    package = ModelPackage(
        version=config["version"],
        config=config,
        normals=normals,
        package_hash=package_hash,
        path=root,
    )
    if enforce_signature:
        from ukz16.governance.signing import ensure_model_signature

        ensure_model_signature(package)
    return package



def list_model_versions() -> list[dict[str, Any]]:
    settings = get_settings()
    versions: list[dict[str, Any]] = []
    if not settings.models_dir.exists():
        return versions
    for child in sorted(settings.models_dir.iterdir()):
        if not child.is_dir():
            continue
        model_path = child / "model.yaml"
        if not model_path.exists():
            continue
        pkg = load_model_package(child.name)
        versions.append(
            {
                "version": pkg.version,
                "status": pkg.config.get("status"),
                "package_hash": pkg.package_hash,
                "weights": pkg.config.get("weights"),
                "path": str(pkg.path),
            }
        )
    return versions


def stable_input_hash(payload_dict: dict[str, Any], model_version: str) -> str:
    """Deterministic hash over canonical JSON of inputs + model version."""
    canonical = json.dumps(
        {"payload": payload_dict, "model_version": model_version},
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
