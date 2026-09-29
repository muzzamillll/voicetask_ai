"""add Slack event idempotency table

Revision ID: 9b2f5d4c8e11
Revises: 8062a2186fd3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b2f5d4c8e11"
down_revision: Union[str, None] = "8062a2186fd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slack_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_slack_events_id"), "slack_events", ["id"], unique=False)
    op.create_index(op.f("ix_slack_events_event_id"), "slack_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_slack_events_event_id"), table_name="slack_events")
    op.drop_index(op.f("ix_slack_events_id"), table_name="slack_events")
    op.drop_table("slack_events")
