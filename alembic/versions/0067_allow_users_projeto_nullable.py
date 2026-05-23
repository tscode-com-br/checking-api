"""allow users.projeto to be NULL (user with no project memberships)

Revision ID: 0067_allow_users_projeto_nullable
Revises: 0066_add_project_forms_transport_emergency_columns
Create Date: 2026-05-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0067_allow_users_projeto_nullable"
down_revision = "0066_add_project_forms_transport_emergency_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table necessario para SQLite (ALTER COLUMN nao suportado nativamente).
    # Em Postgres roda como ALTER COLUMN regular.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "projeto",
            existing_type=sa.String(length=120),
            nullable=True,
        )


def downgrade() -> None:
    # Antes de reaplicar NOT NULL, preenche linhas que ficaram NULL com string vazia
    # para nao quebrar a constraint.
    op.execute("UPDATE users SET projeto = '' WHERE projeto IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "projeto",
            existing_type=sa.String(length=120),
            nullable=False,
        )
