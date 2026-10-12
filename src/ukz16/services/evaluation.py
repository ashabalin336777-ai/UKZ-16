from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ukz16.corridors.baseline import PriorPoint
from ukz16.db.models import DriftAlertRow, EvaluationRow, MeasurementRow, WorkerRow
from ukz16.domain.contracts import EvaluationResult, PrMOIngest, ReviewDecisionRequest
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.drift import detect_status_drift
from ukz16.governance.model_registry import load_model_package, stable_input_hash
from ukz16.ingest.mock import MockEcozAdapter
from ukz16.quality.gates import run_quality_gates
from ukz16.review.service import apply_review, write_audit


class EvaluationService:
    def __init__(self, session: Session, adapter: MockEcozAdapter | None = None) -> None:
        self.session = session
        self.adapter = adapter or MockEcozAdapter()
        self.model = load_model_package()

    def evaluate(self, payload: PrMOIngest, *, actor_id: str | None = None, actor_role: str | None = None) -> EvaluationResult:
        payload = self.adapter.validate_envelope(payload)
        self.adapter.put(payload)

        existing = self.session.scalar(
            select(MeasurementRow).where(
                MeasurementRow.worker_id == payload.worker_id,
                MeasurementRow.encounter_id == payload.encounter_id,
            )
        )
        if existing is not None:
            raise ValueError("duplicate_encounter")

        quality = run_quality_gates(payload, self.model)

        worker = self.session.get(WorkerRow, payload.worker_id)
        if worker is None:
            worker = WorkerRow(worker_id=payload.worker_id, created_at=datetime.now(timezone.utc))
            self.session.add(worker)

        input_hash = stable_input_hash(payload.model_dump(mode="json"), self.model.version)
        measured_date = payload.measured_at.date().isoformat()

        measurement = MeasurementRow(
            id=str(uuid4()),
            worker_id=payload.worker_id,
            encounter_id=payload.encounter_id,
            measured_at=payload.measured_at,
            measured_date=measured_date,
            payload_json=payload.model_dump(mode="json"),
            quality_status=quality.status.value,
            quality_report=quality.to_dict(),
            input_hash=input_hash,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(measurement)

        priors, prior_dev_dates = self._load_priors(payload.worker_id, measured_date)
        eid = uuid4()
        result = evaluate_health_id(
            payload,
            quality,
            self.model,
            prior_points=priors,
            prior_deviation_dates=prior_dev_dates,
            evaluation_id=eid,
        )

        row = EvaluationRow(
            id=str(eid),
            worker_id=payload.worker_id,
            encounter_id=payload.encounter_id,
            measurement_id=measurement.id,
            measured_at=payload.measured_at,
            model_version=self.model.version,
            health_id_value=result.health_id.value,
            health_id_status=result.health_id.status.value,
            result_json=result.model_dump(mode="json"),
            input_hash=input_hash,
            review_status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        write_audit(
            self.session,
            event_type="evaluate",
            actor_id=actor_id,
            actor_role=actor_role,
            entity_type="evaluation",
            entity_id=str(eid),
            payload={"model_version": self.model.version, "input_hash": input_hash, "status": result.health_id.status.value},
        )
        self.session.flush()
        return result

    def _load_priors(self, worker_id: str, current_date: str) -> tuple[list[PriorPoint], list[str]]:
        stmt = (
            select(EvaluationRow, MeasurementRow)
            .join(MeasurementRow, MeasurementRow.id == EvaluationRow.measurement_id)
            .where(EvaluationRow.worker_id == worker_id)
            .order_by(EvaluationRow.measured_at.asc())
        )
        priors: list[PriorPoint] = []
        deviation_dates: list[str] = []
        for ev, meas in self.session.execute(stmt).all():
            if meas.measured_date >= current_date:
                continue
            result = ev.result_json or {}
            hbody = None
            for c in result.get("components", []):
                if c.get("name") == "hBody" and c.get("value") is not None:
                    hbody = float(c["value"])
                    break
            quality_ok = meas.quality_status == "ok" and hbody is not None
            if hbody is not None:
                priors.append(
                    PriorPoint(
                        measured_at=meas.measured_at,
                        measured_date=meas.measured_date,
                        value=hbody,
                        quality_ok=quality_ok,
                    )
                )
            pd = result.get("personal_deviation") or {}
            if pd.get("outside_corridor"):
                deviation_dates.append(meas.measured_date)
        return priors, sorted(set(deviation_dates))

    def get_evaluation(self, evaluation_id: UUID | str) -> EvaluationResult | None:
        row = self.session.get(EvaluationRow, str(evaluation_id))
        if row is None:
            return None
        return EvaluationResult.model_validate(row.result_json)

    def timeline(self, worker_id: str) -> list[EvaluationResult]:
        stmt = (
            select(EvaluationRow)
            .where(EvaluationRow.worker_id == worker_id)
            .order_by(EvaluationRow.measured_at.asc())
        )
        return [EvaluationResult.model_validate(r.result_json) for r in self.session.scalars(stmt).all()]

    def review(
        self,
        evaluation_id: UUID | str,
        request: ReviewDecisionRequest,
        *,
        actor_role: str,
    ) -> EvaluationResult:
        row = self.session.get(EvaluationRow, str(evaluation_id))
        if row is None:
            raise KeyError("evaluation_not_found")
        return apply_review(self.session, row, request, actor_role=actor_role)

    def check_drift(self, reference_n: int = 50) -> dict:
        stmt = select(EvaluationRow.health_id_status).order_by(EvaluationRow.created_at.asc())
        statuses = list(self.session.scalars(stmt).all())
        if len(statuses) < reference_n * 2:
            mid = max(len(statuses) // 2, 1)
            ref, cur = statuses[:mid], statuses[mid:]
        else:
            ref, cur = statuses[:reference_n], statuses[-reference_n:]
        report = detect_status_drift(ref, cur, min_n=5)
        if report.get("alert"):
            self.session.add(
                DriftAlertRow(
                    id=str(uuid4()),
                    alert_type="status_distribution",
                    message=str(report.get("reason")),
                    metrics=report,
                    auto_update=False,
                    created_at=datetime.now(timezone.utc),
                )
            )
            write_audit(
                self.session,
                event_type="drift_alert",
                entity_type="model",
                entity_id=self.model.version,
                payload=report,
            )
        return report
