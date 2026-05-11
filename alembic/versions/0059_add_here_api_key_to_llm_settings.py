"""add here api key to transport ai llm settings

Revision ID: 0059_add_here_api_key_to_llm_settings
Revises: 0058_add_transport_ai_applied_route_stop_legs
Create Date: 2026-05-11 10:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0059_add_here_api_key_to_llm_settings"
down_revision = "0058_add_transport_ai_applied_route_stop_legs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_llm_settings"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("transport_ai_llm_settings")
    }
    with op.batch_alter_table("transport_ai_llm_settings") as batch_op:
        if "here_api_key_ciphertext" not in existing_columns:
            batch_op.add_column(
                sa.Column("here_api_key_ciphertext", sa.Text, nullable=True)
            )
        if "here_api_key_last4" not in existing_columns:
            batch_op.add_column(
                sa.Column("here_api_key_last4", sa.String(length=8), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_llm_settings"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("transport_ai_llm_settings")
    }
    with op.batch_alter_table("transport_ai_llm_settings") as batch_op:
        if "here_api_key_last4" in existing_columns:
            batch_op.drop_column("here_api_key_last4")
        if "here_api_key_ciphertext" in existing_columns:
            batch_op.drop_column("here_api_key_ciphertext")
