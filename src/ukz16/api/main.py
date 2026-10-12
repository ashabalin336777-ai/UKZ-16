from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from ukz16 import __version__
from ukz16.api.auth import Principal, ensure_role, get_principal
from ukz16.db.session import get_session, init_db
from ukz16.domain.contracts import EvaluationResult, PrMOIngest, ReviewDecisionRequest
from ukz16.domain.enums import Role
from ukz16.governance.model_card import load_model_card
from ukz16.governance.model_registry import list_model_versions
from ukz16.services.evaluation import EvaluationService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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


def _svc(session: Session = Depends(get_session)) -> EvaluationService:
    return EvaluationService(session)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/v1/evaluate", response_model=EvaluationResult, tags=["evaluate"])
def evaluate(
    payload: PrMOIngest,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> EvaluationResult:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER)
    try:
        return svc.evaluate(payload, actor_id=principal.api_key, actor_role=principal.role.value)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/v1/evaluations/{evaluation_id}", response_model=EvaluationResult, tags=["evaluate"])
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


@app.get("/v1/workers/{worker_id}/timeline", response_model=list[EvaluationResult], tags=["evaluate"])
def worker_timeline(
    worker_id: str,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> list[EvaluationResult]:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER, Role.AUDITOR)
    return svc.timeline(worker_id)


@app.post("/v1/evaluations/{evaluation_id}/review", response_model=EvaluationResult, tags=["review"])
def review_evaluation(
    evaluation_id: UUID,
    body: ReviewDecisionRequest,
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> EvaluationResult:
    ensure_role(principal, Role.MEDICAL_WORKER)
    try:
        return svc.review(evaluation_id, body, actor_role=principal.role.value)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evaluation_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/v1/model-card", tags=["governance"])
def model_card(principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.MEDICAL_WORKER, Role.AUDITOR)
    return load_model_card()


@app.get("/v1/models", tags=["governance"])
def models(principal: Principal = Depends(get_principal)) -> list[dict[str, Any]]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    return list_model_versions()


@app.post("/v1/governance/drift-check", tags=["governance"])
def drift_check(
    principal: Principal = Depends(get_principal),
    svc: EvaluationService = Depends(_svc),
) -> dict[str, Any]:
    ensure_role(principal, Role.RESEARCHER, Role.AUDITOR)
    return svc.check_drift()


@app.post("/v1/employer/export")
def employer_export_forbidden(principal: Principal = Depends(get_principal)) -> None:
    """Explicitly blocked: individual HEALTH_ID must not be exported to employer."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="employer_export_forbidden",
    )


def run() -> None:
    uvicorn.run("ukz16.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
