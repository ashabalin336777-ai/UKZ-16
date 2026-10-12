"""idempotency key and drift gate fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evaluations", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("evaluations", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.create_index("ix_evaluations_request_id", "evaluations", ["request_id"])
    op.create_unique_constraint("uq_evaluations_idempotency_key", "evaluations", ["idempotency_key"])
    op.add_column(
        "drift_alerts",
        sa.Column("blocks_evaluation", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "drift_alerts",
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("drift_alerts", "resolved")
    op.drop_column("drift_alerts", "blocks_evaluation")
    op.drop_constraint("uq_evaluations_idempotency_key", "evaluations", type_="unique")
    op.drop_index("ix_evaluations_request_id", table_name="evaluations")
    op.drop_column("evaluations", "request_id")
    op.drop_column("evaluations", "idempotency_key")
