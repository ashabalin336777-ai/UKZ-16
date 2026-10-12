from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ukz16.domain.contracts import EvaluationResult, PrMOIngest
from ukz16.privacy.pseudonym import Pseudonymizer, get_pseudonymizer


LANES = ("raw", "normalized", "research", "audit")


@dataclass(frozen=True)
class LaneBundle:
    evaluation_id: str
    raw: dict[str, Any]
    normalized: dict[str, Any]
    research: dict[str, Any]
    audit: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "raw": self.raw,
            "normalized": self.normalized,
            "research": self.research,
            "audit": self.audit,
        }


def build_lane_bundle(
    payload: PrMOIngest,
    result: EvaluationResult,
    *,
    actor_id: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    pseudonymizer: Pseudonymizer | None = None,
) -> LaneBundle:
    """Split one evaluation into TZ-style data planes.

    - raw: source envelope as received (operational)
    - normalized: validated PrMO contract
    - research: pseudonymized export without free-text operator notes
    - audit: access/event metadata without vital values
    """
    pz = pseudonymizer or get_pseudonymizer()
    assert pz is not None
    now = datetime.now(timezone.utc).isoformat()
    eid = str(result.evaluation_id)
    raw_payload = payload.model_dump(mode="json")
    normalized = {
        "schema": "ukz16.prmo.normalized.v1",
        "captured_at": now,
        "envelope": raw_payload,
        "quality": (result.evidence.quality if result.evidence else {}),
    }
    research = {
        "schema": "ukz16.research.record.v1",
        "captured_at": now,
        "subject_pseudo_id": pz.subject_id(payload.worker_id),
        "encounter_pseudo_id": pz.encounter_id(payload.encounter_id),
        "measured_at": payload.measured_at.isoformat(),
        "model_version": result.health_id.version,
        "health_id_status": result.health_id.status.value,
        # Research may retain vitals under pseudo id; never employer-exportable
        "vitals": raw_payload.get("vitals"),
        "components": [
            {
                "name": c.name,
                "status": c.status.value,
                "value": c.value,
                "weight": c.weight,
            }
            for c in result.components
        ],
        "employer_export_allowed": False,
        "diagnosis_claim": False,
    }
    audit = {
        "schema": "ukz16.audit.event.v1",
        "event_id": str(uuid4()),
        "event_type": "evaluate",
        "occurred_at": now,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "request_id": request_id,
        "entity_type": "evaluation",
        "entity_id": eid,
        "subject_pseudo_id": pz.subject_id(payload.worker_id),
        "model_version": result.health_id.version,
        "input_hash": result.evidence.input_hash,
        "health_id_status": result.health_id.status.value,
        # Explicitly omit vital values / HEALTH_ID numeric value
        "phi_fields_omitted": True,
    }
    return LaneBundle(
        evaluation_id=eid,
        raw={"schema": "ukz16.raw.envelope.v1", "captured_at": now, "envelope": raw_payload},
        normalized=normalized,
        research=research,
        audit=audit,
    )
