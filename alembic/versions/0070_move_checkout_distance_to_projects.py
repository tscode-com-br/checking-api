"""move minimum_checkout_distance_meters from project_auto_checkout_distances to projects

Revision ID: 0070_move_checkout_distance_to_projects
Revises: 0069_move_mixed_zone_interval_to_projects
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070_move_checkout_distance_to_projects"
down_revision = "0069_move_mixed_zone_interval_to_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("projects"):
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "minimum_checkout_distance_meters" not in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "minimum_checkout_distance_meters",
                        sa.Integer(),
                        nullable=False,
                        server_default="2000",
                    )
                )

        # Backfill from side table where available
        if inspector.has_table("project_auto_checkout_distances"):
            bind.execute(sa.text(
                "UPDATE projects SET minimum_checkout_distance_meters = ("
                "  SELECT minimum_checkout_distance_meters"
                "  FROM project_auto_checkout_distances"
                "  WHERE project_auto_checkout_distances.project_name = projects.name"
                ") WHERE EXISTS ("
                "  SELECT 1 FROM project_auto_checkout_distances"
                "  WHERE project_auto_checkout_distances.project_name = projects.name"
                ")"
            ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("projects"):
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "minimum_checkout_distance_meters" in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.drop_column("minimum_checkout_distance_meters")
