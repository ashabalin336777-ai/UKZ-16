"""lane records for raw/normalized/research/audit planes

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lane_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("lane", sa.String(length=32), nullable=False),
        sa.Column("subject_pseudo_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evaluation_id", "lane", name="uq_lane_evaluation"),
    )
    op.create_index("ix_lane_records_evaluation_id", "lane_records", ["evaluation_id"])
    op.create_index("ix_lane_records_lane", "lane_records", ["lane"])
    op.create_index("ix_lane_records_subject_pseudo_id", "lane_records", ["subject_pseudo_id"])


def downgrade() -> None:
    op.drop_index("ix_lane_records_subject_pseudo_id", table_name="lane_records")
    op.drop_index("ix_lane_records_lane", table_name="lane_records")
    op.drop_index("ix_lane_records_evaluation_id", table_name="lane_records")
    op.drop_table("lane_records")
