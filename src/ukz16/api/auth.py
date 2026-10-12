from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from ukz16.config import get_settings
from ukz16.domain.enums import Role

_bearer = HTTPBearer(auto_error=False)
_jwks_clients: dict[str, PyJWKClient] = {}


@dataclass(frozen=True)
class Principal:
    role: Role
    subject: str
    auth_method: str  # api_key | oidc


def _extract_roles(claims: dict[str, Any], role_claim: str) -> list[str]:
    parts = role_claim.split(".")
    cur: Any = claims
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            flat = claims.get("roles") or claims.get("role") or []
            if isinstance(flat, str):
                return [flat]
            return list(flat) if isinstance(flat, list) else []
        cur = cur[part]
    if isinstance(cur, list):
        return [str(x) for x in cur]
    if isinstance(cur, str):
        return [cur]
    return []


def _map_role(roles: list[str]) -> Role | None:
    normalized = {r.lower() for r in roles}
    for candidate in (Role.MEDICAL_WORKER, Role.AUDITOR, Role.RESEARCHER):
        if candidate.value in normalized:
            return candidate
    aliases = {
        "medical": Role.MEDICAL_WORKER,
        "clinician": Role.MEDICAL_WORKER,
        "doctor": Role.MEDICAL_WORKER,
        "research": Role.RESEARCHER,
        "audit": Role.AUDITOR,
    }
    for role in roles:
        mapped = aliases.get(role.lower())
        if mapped:
            return mapped
    return None


def _jwks_client(url: str) -> PyJWKClient:
    if url not in _jwks_clients:
        _jwks_clients[url] = PyJWKClient(url)
    return _jwks_clients[url]


def clear_jwks_cache() -> None:
    _jwks_clients.clear()


def _principal_from_jwt(token: str) -> Principal:
    settings = get_settings()
    if not settings.oidc_issuer or not settings.oidc_jwks_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="oidc_not_configured")
    try:
        client = _jwks_client(settings.oidc_jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        algorithms = [a.strip() for a in settings.oidc_algorithms.split(",") if a.strip()]
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=algorithms,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_bearer_token") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="oidc_jwks_unavailable") from exc

    role = _map_role(_extract_roles(claims, settings.oidc_role_claim))
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing_role_claim")
    subject = str(claims.get("sub") or claims.get("preferred_username") or "oidc-user")
    return Principal(role=role, subject=subject, auth_method="oidc")


def _principal_from_api_key(api_key: str) -> Principal:
    mapping = get_settings().parsed_api_keys()
    role = mapping.get(api_key)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    try:
        return Principal(role=Role(role), subject=f"api-key:{role}", auth_method="api_key")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_role") from exc


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Principal:
    settings = get_settings()
    mode = (settings.auth_mode or "hybrid").lower()

    if credentials and credentials.scheme.lower() == "bearer":
        if mode in {"oidc", "hybrid"}:
            return _principal_from_jwt(credentials.credentials)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer_not_enabled")

    if x_api_key:
        if mode in {"api_key", "hybrid"}:
            return _principal_from_api_key(x_api_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="api_key_not_enabled")

    detail = "missing_credentials"
    if mode == "oidc":
        detail = "missing_bearer_token"
    elif mode == "api_key":
        detail = "missing_api_key"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def ensure_role(principal: Principal, *allowed: Role) -> None:
    if principal.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_role")
