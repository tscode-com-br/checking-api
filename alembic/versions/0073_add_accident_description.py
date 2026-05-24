"""add description field to accidents

Revision ID: 0073_add_accident_description
Revises: 0072_add_project_twilio_emergency_fields
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0073_add_accident_description"
down_revision = "0072_add_project_twilio_emergency_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    existing = {col["name"] for col in inspector.get_columns("accidents")}
    if "description" not in existing:
        with op.batch_alter_table("accidents") as batch_op:
            batch_op.add_column(
                sa.Column("description", sa.Text(), nullable=False, server_default="")
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    existing = {col["name"] for col in inspector.get_columns("accidents")}
    if "description" in existing:
        with op.batch_alter_table("accidents") as batch_op:
            batch_op.drop_column("description")
