"""add forms submission progress metadata

Revision ID: 0063_forms_submission_progress_metadata
Revises: 0062_backfill_admin_users_for_existing_admins
Create Date: 2026-05-21 16:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0063_forms_submission_progress_metadata"
down_revision = "0062_backfill_admin_users_for_existing_admins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("forms_submissions", sa.Column("event_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("forms_submissions", sa.Column("request_path", sa.String(length=120), nullable=True))
    op.add_column("forms_submissions", sa.Column("display_status", sa.String(length=24), nullable=True))
    op.add_column("forms_submissions", sa.Column("project_candidates_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("forms_submissions", "project_candidates_json")
    op.drop_column("forms_submissions", "display_status")
    op.drop_column("forms_submissions", "request_path")
    op.drop_column("forms_submissions", "event_time")