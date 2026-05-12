"""add endpoint api keys table

Revision ID: 0060_add_endpoint_api_keys
Revises: 0059_add_here_api_key_to_llm_settings
Create Date: 2026-05-12 00:00:00
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "0060_add_endpoint_api_keys"
down_revision = "0059_add_here_api_key_to_llm_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("endpoint_api_keys"):
        return

    op.create_table(
        "endpoint_api_keys",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("endpoint_name", sa.String(80), nullable=False),
        sa.Column("secret_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("endpoint_name", name="uq_endpoint_api_keys_name"),
    )

    now = datetime.now(tz=timezone.utc)
    initial_key = secrets.token_hex(16)  # 32 hex chars
    op.execute(
        sa.text(
            "INSERT INTO endpoint_api_keys (endpoint_name, secret_key, created_at, updated_at) "
            "VALUES (:name, :key, :now, :now)"
        ).bindparams(name="checkinginfo", key=initial_key, now=now)
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("endpoint_api_keys"):
        return

    op.drop_table("endpoint_api_keys")
