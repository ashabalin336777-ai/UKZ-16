"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("worker_id", sa.String(length=128), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "measurements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("encounter_id", sa.String(length=128), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_date", sa.String(length=10), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("worker_id", "encounter_id", name="uq_worker_encounter"),
    )
    op.create_index("ix_measurements_worker_id", "measurements", ["worker_id"])
    op.create_index("ix_measurements_measured_at", "measurements", ["measured_at"])
    op.create_index("ix_measurements_measured_date", "measurements", ["measured_date"])
    op.create_index("ix_measurements_input_hash", "measurements", ["input_hash"])

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("encounter_id", sa.String(length=128), nullable=False),
        sa.Column("measurement_id", sa.String(length=36), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("health_id_value", sa.Float(), nullable=True),
        sa.Column("health_id_status", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluations_worker_id", "evaluations", ["worker_id"])
    op.create_index("ix_evaluations_encounter_id", "evaluations", ["encounter_id"])
    op.create_index("ix_evaluations_measurement_id", "evaluations", ["measurement_id"])
    op.create_index("ix_evaluations_input_hash", "evaluations", ["input_hash"])

    op.create_table(
        "review_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("medical_worker_id", sa.String(length=128), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("signature_ref", sa.String(length=256), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_review_decisions_evaluation_id", "review_decisions", ["evaluation_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("actor_role", sa.String(length=64), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("immutable", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])

    op.create_table(
        "drift_alerts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("auto_update", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("drift_alerts")
    op.drop_table("audit_events")
    op.drop_table("review_decisions")
    op.drop_table("evaluations")
    op.drop_table("measurements")
    op.drop_table("workers")
