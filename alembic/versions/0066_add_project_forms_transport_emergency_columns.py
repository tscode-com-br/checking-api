"""add forms_enabled, transport_enabled, emergency_phone to projects

Revision ID: 0066_add_project_forms_transport_emergency_columns
Revises: 0065_drop_users_cargo_column
Create Date: 2026-05-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0066_add_project_forms_transport_emergency_columns"
down_revision = "0065_drop_users_cargo_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("forms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("projects", sa.Column("transport_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("projects", sa.Column("emergency_phone", sa.String(length=32), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("projects", "emergency_phone")
    op.drop_column("projects", "transport_enabled")
    op.drop_column("projects", "forms_enabled")
