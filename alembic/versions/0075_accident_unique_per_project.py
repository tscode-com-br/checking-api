"""change accident unique-active constraint from global to per-project

Drops:  ix_accidents_single_active  (unique on closed_at WHERE NULL)
        ix_accidents_single_active_guard  (unique on (1) WHERE NULL)
Creates: ix_accidents_single_active_per_project  (unique on project_id WHERE NULL)

Revision ID: 0075_accident_unique_per_project
Revises: 0074_add_accident_user_report_awareness
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0075_accident_unique_per_project"
down_revision = "0074_add_accident_user_report_awareness"
branch_labels = None
depends_on = None

_OLD_INDEXES = ("ix_accidents_single_active", "ix_accidents_single_active_guard")
_NEW_INDEX = "ix_accidents_single_active_per_project"
_NEW_INDEX_DDL = (
    f"CREATE UNIQUE INDEX {_NEW_INDEX} "
    "ON accidents (project_id) WHERE closed_at IS NULL"
)
_OLD_GUARD_DDL = (
    "CREATE UNIQUE INDEX ix_accidents_single_active_guard "
    "ON accidents ((1)) WHERE closed_at IS NULL"
)
_OLD_ACTIVE_DDL = (
    "CREATE UNIQUE INDEX ix_accidents_single_active "
    "ON accidents (closed_at) WHERE closed_at IS NULL"
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    existing_idx = {idx["name"] for idx in inspector.get_indexes("accidents")}

    for idx_name in _OLD_INDEXES:
        if idx_name in existing_idx:
            op.drop_index(idx_name, table_name="accidents")

    if _NEW_INDEX not in existing_idx:
        op.execute(_NEW_INDEX_DDL)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    existing_idx = {idx["name"] for idx in inspector.get_indexes("accidents")}

    if _NEW_INDEX in existing_idx:
        op.drop_index(_NEW_INDEX, table_name="accidents")

    if "ix_accidents_single_active" not in existing_idx:
        op.execute(_OLD_ACTIVE_DDL)

    if "ix_accidents_single_active_guard" not in existing_idx:
        op.execute(_OLD_GUARD_DDL)
