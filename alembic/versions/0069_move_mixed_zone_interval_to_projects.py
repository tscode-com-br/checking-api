"""move mixed_zone_interval from mobile_app_settings to projects

Revision ID: 0069_move_mixed_zone_interval_to_projects
Revises: 0068_add_project_inactivity_days_threshold
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0069_move_mixed_zone_interval_to_projects"
down_revision = "0068_add_project_inactivity_days_threshold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("projects"):
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "mixed_zone_interval_minutes" not in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "mixed_zone_interval_minutes",
                        sa.Integer(),
                        nullable=False,
                        server_default="30",
                    )
                )

    if inspector.has_table("mobile_app_settings"):
        setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
        if "mixed_zone_interval_minutes" in setting_columns:
            with op.batch_alter_table("mobile_app_settings") as batch_op:
                batch_op.drop_column("mixed_zone_interval_minutes")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("mobile_app_settings"):
        setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
        if "mixed_zone_interval_minutes" not in setting_columns:
            with op.batch_alter_table("mobile_app_settings") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "mixed_zone_interval_minutes",
                        sa.Integer(),
                        nullable=False,
                        server_default="20",
                    )
                )

    if inspector.has_table("projects"):
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "mixed_zone_interval_minutes" in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.drop_column("mixed_zone_interval_minutes")
