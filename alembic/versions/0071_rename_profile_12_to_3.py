"""rename profile 12 to profile 3 (admin + transport combined role)

Revision ID: 0071_rename_profile_12_to_3
Revises: 0070_move_checkout_distance_to_projects
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0071_rename_profile_12_to_3"
down_revision = "0070_move_checkout_distance_to_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("users"):
        # Both 12 (1+2) and 21 (2+1) encoded the same combined role.
        bind.execute(sa.text("UPDATE users SET perfil = 3 WHERE perfil IN (12, 21)"))

    if inspector.has_table("admin_access_requests"):
        bind.execute(sa.text(
            "UPDATE admin_access_requests SET requested_profile = 3"
            " WHERE requested_profile IN (12, 21)"
        ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("users"):
        bind.execute(sa.text("UPDATE users SET perfil = 12 WHERE perfil = 3"))

    if inspector.has_table("admin_access_requests"):
        bind.execute(sa.text(
            "UPDATE admin_access_requests SET requested_profile = 12"
            " WHERE requested_profile = 3"
        ))
