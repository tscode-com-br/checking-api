"""drop users.cargo column (no longer collected)

Revision ID: 0065_drop_users_cargo_column
Revises: 0063_forms_submission_progress_metadata
Create Date: 2026-05-22 04:25:00

Background
----------
The "Cargo" field on user records was removed from the admin UI and the
backend code no longer references it (see commit ``02be916``). This
migration drops the ``users.cargo`` column from the database.

**Destructive.** Existing ``cargo`` values are lost on upgrade. The
deploy that introduces this migration was preceded by a ``pg_dump`` of
production saved in ``/var/backups/checking/pre-cargo-drop-*.pgdump``
for emergency restore.

Idempotent: skips the drop if the column has already been removed (safe
to re-run on partially-migrated hosts).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0065_drop_users_cargo_column"
down_revision = "0063_forms_submission_progress_metadata"
branch_labels = None
depends_on = None


def _has_column(connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    connection = op.get_bind()
    if _has_column(connection, "users", "cargo"):
        op.drop_column("users", "cargo")


def downgrade() -> None:
    connection = op.get_bind()
    if not _has_column(connection, "users", "cargo"):
        op.add_column("users", sa.Column("cargo", sa.String(length=255), nullable=True))
    # Data is irrecoverable on downgrade — column is recreated empty.
