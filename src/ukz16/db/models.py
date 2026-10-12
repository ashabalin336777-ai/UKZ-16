from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WorkerRow(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MeasurementRow(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint("worker_id", "encounter_id", name="uq_worker_encounter"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    worker_id: Mapped[str] = mapped_column(String(128), index=True)
    encounter_id: Mapped[str] = mapped_column(String(128))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    measured_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    payload_json: Mapped[dict] = mapped_column(JSON)
    quality_status: Mapped[str] = mapped_column(String(32))
    quality_report: Mapped[dict] = mapped_column(JSON, default=dict)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EvaluationRow(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    worker_id: Mapped[str] = mapped_column(String(128), index=True)
    encounter_id: Mapped[str] = mapped_column(String(128), index=True)
    measurement_id: Mapped[str] = mapped_column(String(36), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model_version: Mapped[str] = mapped_column(String(64))
    health_id_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_id_status: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[dict] = mapped_column(JSON)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ReviewDecisionRow(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    evaluation_id: Mapped[str] = mapped_column(String(36), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    medical_worker_id: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    signature_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    model_version: Mapped[str] = mapped_column(String(64))
    input_hash: Mapped[str] = mapped_column(String(64))


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)


class DriftAlertRow(Base):
    __tablename__ = "drift_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    alert_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=False)
    blocks_evaluation: Mapped[bool] = mapped_column(Boolean, default=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
