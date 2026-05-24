"""add awareness_status to accident_user_reports

Revision ID: 0074_add_accident_user_report_awareness
Revises: 0073_add_accident_description
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0074_add_accident_user_report_awareness"
down_revision = "0073_add_accident_description"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accident_user_reports"):
        return

    existing = {col["name"] for col in inspector.get_columns("accident_user_reports")}
    if "awareness_status" not in existing:
        with op.batch_alter_table("accident_user_reports") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "awareness_status",
                    sa.String(16),
                    nullable=False,
                    server_default="waiting",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accident_user_reports"):
        return

    existing = {col["name"] for col in inspector.get_columns("accident_user_reports")}
    if "awareness_status" in existing:
        with op.batch_alter_table("accident_user_reports") as batch_op:
            batch_op.drop_column("awareness_status")
