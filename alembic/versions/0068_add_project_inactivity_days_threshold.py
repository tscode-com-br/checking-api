"""add inactivity_days_threshold to projects

Revision ID: 0068_add_project_inactivity_days_threshold
Revises: 0067_allow_users_projeto_nullable
Create Date: 2026-05-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0068_add_project_inactivity_days_threshold"
down_revision = "0067_allow_users_projeto_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "inactivity_days_threshold",
                sa.Integer(),
                nullable=False,
                server_default="60",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("inactivity_days_threshold")
