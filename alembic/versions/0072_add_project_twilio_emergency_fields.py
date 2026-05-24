"""add Twilio and emergency fields to projects

Revision ID: 0072_add_project_twilio_emergency_fields
Revises: 0071_rename_profile_12_to_3
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0072_add_project_twilio_emergency_fields"
down_revision = "0071_rename_profile_12_to_3"
branch_labels = None
depends_on = None

_NEW_COLUMNS = [
    ("twilio_account_sid",    sa.String(64),  ""),
    ("twilio_auth_token",     sa.String(64),  ""),
    ("twilio_phone_number",   sa.String(32),  ""),
    ("mobile_admin",          sa.String(32),  ""),
    ("email_local_emergency", sa.Text(),      ""),
    ("emergency_call_message",sa.Text(),      ""),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        return

    existing = {col["name"] for col in inspector.get_columns("projects")}
    with op.batch_alter_table("projects") as batch_op:
        for col_name, col_type, default in _NEW_COLUMNS:
            if col_name not in existing:
                batch_op.add_column(
                    sa.Column(col_name, col_type, nullable=False, server_default=default)
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        return

    existing = {col["name"] for col in inspector.get_columns("projects")}
    with op.batch_alter_table("projects") as batch_op:
        for col_name, _, _ in _NEW_COLUMNS:
            if col_name in existing:
                batch_op.drop_column(col_name)
