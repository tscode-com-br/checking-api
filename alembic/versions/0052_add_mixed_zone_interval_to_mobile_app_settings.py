"""add mixed zone interval to mobile app settings

Revision ID: 0052_mixed_zone_interval
Revises: 0051_add_transport_ai_run_llm_snapshot
Create Date: 2026-05-04 11:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0052_mixed_zone_interval"
down_revision = "0051_add_transport_ai_run_llm_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "mixed_zone_interval_minutes" in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "mixed_zone_interval_minutes",
                sa.Integer(),
                nullable=False,
                server_default="20",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "mixed_zone_interval_minutes" not in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("mixed_zone_interval_minutes")