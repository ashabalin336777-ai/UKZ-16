from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from ukz16 import __version__
from ukz16.api.auth import Principal, ensure_role, get_principal
from ukz16.db.session import get_session, init_db
from ukz16.domain.contracts import EvaluationResult, PrMOIngest, ReviewDecisionRequest
from ukz16.domain.enums import Role
from ukz16.governance.model_card import load_model_card
from ukz16.governance.model_registry import list_model_versions, load_model_package
from ukz16.governance.signing import sign_model_package, verify_model_package
from ukz16.ingest.factory import build_ingest_adapter
from ukz16.observability.telemetry import setup_telemetry
from ukz16.services.evaluation import DriftBlockError, EvaluationService


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ukz16.config import get_resolved_settings

    init_db()
    app.state.telemetry = setup_telemetry(app)
    # Resolve Vault overlays once at startup (values never logged).
    app.state.settings = get_resolved_settings()
    yield


app = FastAPI(
    title="UKZ-16 HEALTH_ID",
    description=(
        "Исследовательский модуль воспроизводимого расчёта и клинической валидации HEALTH_ID. "
        "Research use only. Не ставит диагноз. Индивидуальный HEALTH_ID не передаётся работодателю."
    ),
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)


def _svc(session: Session = Depends(get_session)) -> EvaluationService:
    return EvaluationService(session)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


def _evaluate_impl(
    payload: PrMOIngest,
    principal: Principal,
    svc: EvaluationService,
    request: Request,
    idempotency_key: str | None,
) -> EvaluationResult:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER)
    try:
        return svc.evaluate(
            payload,
            actor_id=principal.subject,
            actor_role=principal.role.value,
            idempotency_key=idempotency_key,
            request_id=_request_id(request),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DriftBlockError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/v1/health-id/ingest/{encounter_id}", response_model=EvaluationResult, tags=["evaluate"])
def ingest_from_ecoz(
    encounter_id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EvaluationResult:
    """Fetch encounter from configured ECOZ adapter, then evaluate."""
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER)
    adapter = build_ingest_adapter()
    try:
        payload = adapter.fetch_encounter(encounter_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _evaluate_impl(payload, principal, svc, request, idempotency_key)


@app.post("/api/v1/health-id/evaluations", response_model=EvaluationResult, tags=["evaluate"])
def create_evaluation(
    payload: PrMOIngest,
    request: Request,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EvaluationResult:
    return _evaluate_impl(payload, principal, svc, request, idempotency_key)


@app.post("/v1/evaluate", response_model=EvaluationResult, tags=["evaluate"], deprecated=True)
def evaluate_alias(
    payload: PrMOIngest,
    request: Request,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EvaluationResult:
    return _evaluate_impl(payload, principal, svc, request, idempotency_key)


@app.get("/api/v1/health-id/evaluations/{evaluation_id}", response_model=EvaluationResult, tags=["evaluate"])
@app.get("/v1/evaluations/{evaluation_id}", response_model=EvaluationResult, tags=["evaluate"], deprecated=True)
def get_evaluation(
    evaluation_id: UUID,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> EvaluationResult:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER, Role.AUDITOR)
    result = svc.get_evaluation(evaluation_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evaluation_not_found")
    return result


@app.get("/api/v1/health-id/subjects/{worker_id}/trajectory", response_model=list[EvaluationResult], tags=["evaluate"])
@app.get("/v1/workers/{worker_id}/timeline", response_model=list[EvaluationResult], tags=["evaluate"], deprecated=True)
def worker_trajectory(
    worker_id: str,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[EvaluationResult]:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER, Role.AUDITOR)
    return svc.timeline(worker_id, date_from=date_from, date_to=date_to)


@app.post("/api/v1/health-id/evaluations/{evaluation_id}/clinical-review", tags=["review"])
@app.post("/v1/evaluations/{evaluation_id}/review", tags=["review"], deprecated=True)
def review_evaluation(
    evaluation_id: UUID,
    body: ReviewDecisionRequest,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> dict[str, Any]:
    ensure_role(principal, Role.MEDICAL_WORKER)
    try:
        result, audit_id = svc.review(evaluation_id, body, actor_role=principal.role.value)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evaluation_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "evaluation": result.model_dump(mode="json"),
        "review_status": result.clinical_review.status,
        "audit_id": audit_id,
    }


@app.get("/api/v1/health-id/model-card/{version}", tags=["governance"])
@app.get("/api/v1/health-id/model-card", tags=["governance"])
@app.get("/v1/model-card", tags=["governance"], deprecated=True)
def model_card(
    principal: Principal = Depends(get_principal),
    version: str | None = None,
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER, Role.AUDITOR)
    try:
        return load_model_card(version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model_version_not_found") from exc


@app.get("/v1/models", tags=["governance"], deprecated=True)
@app.get("/api/v1/health-id/models", tags=["governance"])
def models(principal: Principal = Depends(get_principal)) -> list[dict[str, Any]]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    return list_model_versions()


@app.get("/api/v1/health-id/validation/metrics", tags=["governance"])
def validation_metrics(
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
    version: str | None = Query(default=None),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    return svc.validation_metrics(model_version=version)


@app.post("/api/v1/health-id/validation/drift-check", tags=["governance"])
@app.post("/v1/governance/drift-check", tags=["governance"], deprecated=True)
def drift_check(
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    return svc.check_drift()


@app.post("/api/v1/health-id/validation/drift/{alert_id}/resolve", tags=["governance"])
def resolve_drift(
    alert_id: str,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    try:
        return svc.resolve_drift(alert_id, actor_id=principal.subject, actor_role=principal.role.value)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="drift_alert_not_found") from exc


@app.post("/api/v1/health-id/models/{version}/sign", tags=["governance"])
def sign_model(
    version: str,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    try:
        return sign_model_package(version)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model_version_not_found") from exc


@app.get("/api/v1/health-id/models/{version}/signature", tags=["governance"])
def verify_model(
    version: str,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    try:
        pkg = load_model_package(version, enforce_signature=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model_version_not_found") from exc
    return verify_model_package(pkg)


@app.post("/v1/employer/export")
@app.post("/api/v1/health-id/employer/export")
def employer_export_forbidden(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> None:
    """Explicitly blocked: individual HEALTH_ID must not be exported to employer."""
    from ukz16.review.service import write_audit

    write_audit(
        session,
        event_type="employer_export_denied",
        actor_id=principal.subject,
        actor_role=principal.role.value,
        entity_type="employer_export",
        entity_id=None,
        payload={"detail": "employer_export_forbidden", "phi_fields_omitted": True},
    )
    # Commit before HTTPException so denial is retained (dependency rollback won't undo).
    session.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="employer_export_forbidden",
    )


def run() -> None:
    uvicorn.run("ukz16.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
