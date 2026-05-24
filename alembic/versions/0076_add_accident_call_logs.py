"""create accident_call_logs table

Revision ID: 0076_add_accident_call_logs
Revises: 0075_accident_unique_per_project
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0076_add_accident_call_logs"
down_revision = "0075_accident_unique_per_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("accident_call_logs"):
        return

    op.create_table(
        "accident_call_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("call_number", sa.Integer(), nullable=False),
        sa.Column("call_sid", sa.String(64), nullable=True),
        sa.Column(
            "accident_id",
            sa.Integer(),
            sa.ForeignKey("accidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "triggered_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "triggered_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id"),
            nullable=True,
        ),
        sa.Column("to_phone", sa.String(32), nullable=False),
        sa.Column("from_phone", sa.String(32), nullable=False),
        sa.Column("call_status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("ended_by", sa.String(16), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("message_twiml", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("call_number", name="uq_accident_call_logs_call_number"),
        sa.CheckConstraint(
            "call_status IN ('queued','initiated','ringing','in-progress','completed',"
            "'failed','busy','no-answer','canceled')",
            name="ck_accident_call_logs_status_allowed",
        ),
        sa.CheckConstraint(
            "ended_by IN ('system','receiver') OR ended_by IS NULL",
            name="ck_accident_call_logs_ended_by",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("accident_call_logs"):
        op.drop_table("accident_call_logs")
