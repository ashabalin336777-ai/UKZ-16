from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from ukz16.db.session import get_session
from ukz16.services.evaluation import EvaluationService


def db_session() -> Generator[Session, None, None]:
    yield from get_session()


def evaluation_service(session: Session) -> EvaluationService:
    return EvaluationService(session)
