from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from ukz16.db.models import AuditEventRow, EvaluationRow, ReviewDecisionRow
from ukz16.domain.contracts import ClinicalReview, EvaluationResult, ReviewDecisionRequest


def write_audit(
    session: Session,
    *,
    event_type: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEventRow:
    row = AuditEventRow(
        id=str(uuid4()),
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        created_at=datetime.now(timezone.utc),
        immutable=True,
    )
    session.add(row)
    return row


def apply_review(
    session: Session,
    evaluation: EvaluationRow,
    request: ReviewDecisionRequest,
    *,
    actor_role: str,
) -> EvaluationResult:
    if request.decision == "pending":
        raise ValueError("decision must be confirmed or rejected")
    if request.decision not in ("confirmed", "rejected"):
        raise ValueError("invalid decision")

    now = datetime.now(timezone.utc)
    decision = ReviewDecisionRow(
        id=str(uuid4()),
        evaluation_id=evaluation.id,
        decision=request.decision,
        medical_worker_id=request.medical_worker_id,
        comment=request.comment,
        evidence_ids=list(request.evidence_ids),
        signature_ref=request.signature_ref,  # TODO: 63-FZ
        signed_at=now,
        model_version=evaluation.model_version,
        input_hash=evaluation.input_hash,
    )
    session.add(decision)

    result = EvaluationResult.model_validate(evaluation.result_json)
    result.clinical_review = ClinicalReview(
        status=request.decision,
        medical_worker_id=request.medical_worker_id,
        comment=request.comment,
        evidence_ids=list(request.evidence_ids),
        signed_at=now,
        signature_ref=request.signature_ref,
    )
    evaluation.result_json = result.model_dump(mode="json")
    evaluation.review_status = request.decision

    write_audit(
        session,
        event_type="clinical_review",
        actor_id=request.medical_worker_id,
        actor_role=actor_role,
        entity_type="evaluation",
        entity_id=evaluation.id,
        payload={
            "decision": request.decision,
            "model_version": evaluation.model_version,
            "input_hash": evaluation.input_hash,
        },
    )
    return result
