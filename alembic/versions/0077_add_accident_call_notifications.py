"""create accident_call_notifications table (phase 8.2 persistence)

Revision ID: 0077_add_accident_call_notifications
Revises: 0076_add_accident_call_logs
Create Date: 2026-05-25

Stores the per-event notification feed that powers the admin "barra de
notificações persistente" (item 3.2.3 of docs/temp002_alteracoes.txt). Each
emergency-call SSE event (`status_event` in
twilio_caller._build_call_notification_metadata) is also written to this
table so the admin can refresh the page and still see the history.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0077_add_accident_call_notifications"
down_revision = "0076_add_accident_call_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("accident_call_notifications"):
        return

    op.create_table(
        "accident_call_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "call_log_id",
            sa.Integer(),
            sa.ForeignKey("accident_call_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accident_id",
            sa.Integer(),
            sa.ForeignKey("accidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("message_pt", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_accident_call_notifications_accident_occurred",
        "accident_call_notifications",
        ["accident_id", "occurred_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("accident_call_notifications"):
        existing_idx = {idx["name"] for idx in inspector.get_indexes("accident_call_notifications")}
        if "ix_accident_call_notifications_accident_occurred" in existing_idx:
            op.drop_index(
                "ix_accident_call_notifications_accident_occurred",
                table_name="accident_call_notifications",
            )
        op.drop_table("accident_call_notifications")
