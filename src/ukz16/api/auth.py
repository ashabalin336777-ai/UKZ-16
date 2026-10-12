from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from ukz16.config import get_settings
from ukz16.domain.enums import Role


@dataclass(frozen=True)
class Principal:
    role: Role
    api_key: str


def get_principal(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Principal:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_api_key")
    mapping = get_settings().parsed_api_keys()
    role = mapping.get(x_api_key)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    try:
        return Principal(role=Role(role), api_key=x_api_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_role") from exc


def require_roles(*allowed: Role):
    def _dep(principal: Principal = None) -> Principal:  # type: ignore[assignment]
        # FastAPI will inject via Depends in routes; this helper used manually
        return principal

    _dep.allowed = allowed  # type: ignore[attr-defined]
    return _dep


def ensure_role(principal: Principal, *allowed: Role) -> None:
    if principal.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_role")
