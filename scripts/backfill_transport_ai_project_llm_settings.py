from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sistema.app.core.config import settings
from sistema.app.models import Project, TransportAIProjectLlmSettings
from sistema.app.services.time_utils import now_sgt
from sistema.app.services.transport_ai_llm_settings import get_legacy_transport_ai_llm_settings


class TransportAILegacyBackfillError(RuntimeError):
    pass


def build_session_factory(database_url: str):
    engine = sa.create_engine(database_url)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _normalize_project_ids(project_ids: list[int]) -> list[int]:
    normalized_ids: list[int] = []
    seen_ids: set[int] = set()
    for project_id in project_ids:
        normalized_project_id = int(project_id)
        if normalized_project_id <= 0:
            raise TransportAILegacyBackfillError("Project ids must be positive integers.")
        if normalized_project_id in seen_ids:
            continue
        seen_ids.add(normalized_project_id)
        normalized_ids.append(normalized_project_id)
    if not normalized_ids:
        raise TransportAILegacyBackfillError("Provide at least one explicit --project-id target for the backfill.")
    return normalized_ids


def backfill_transport_ai_project_llm_settings(
    db: Session,
    *,
    project_ids: list[int],
    overwrite_existing: bool = False,
) -> dict[str, object]:
    normalized_project_ids = _normalize_project_ids(project_ids)
    legacy_settings = get_legacy_transport_ai_llm_settings(db)
    if legacy_settings is None:
        raise TransportAILegacyBackfillError(
            "Legacy Transport AI LLM settings do not exist. Export or backfill cannot continue."
        )
    if not legacy_settings.api_key_ciphertext or not legacy_settings.api_key_last4:
        raise TransportAILegacyBackfillError(
            "Legacy Transport AI LLM settings do not have an encrypted API key to backfill."
        )

    projects = (
        db.query(Project)
        .filter(Project.id.in_(normalized_project_ids))
        .all()
    )
    projects_by_id = {project.id: project for project in projects}
    missing_project_ids = [project_id for project_id in normalized_project_ids if project_id not in projects_by_id]
    if missing_project_ids:
        missing_list = ", ".join(str(project_id) for project_id in missing_project_ids)
        raise TransportAILegacyBackfillError(
            f"The requested projects do not exist: {missing_list}."
        )

    existing_rows = (
        db.query(TransportAIProjectLlmSettings)
        .filter(TransportAIProjectLlmSettings.project_id.in_(normalized_project_ids))
        .all()
    )
    existing_rows_by_project_id = {row.project_id: row for row in existing_rows}
    if existing_rows_by_project_id and not overwrite_existing:
        existing_projects = ", ".join(
            f"{project_id} ({projects_by_id[project_id].name})"
            for project_id in normalized_project_ids
            if project_id in existing_rows_by_project_id
        )
        raise TransportAILegacyBackfillError(
            "The following projects already have project-scoped Transport AI settings: "
            f"{existing_projects}. Rerun with --overwrite-existing only if replacement is intentional."
        )

    timestamp = now_sgt()
    project_summaries: list[dict[str, object]] = []
    for project_id in normalized_project_ids:
        project = projects_by_id[project_id]
        persisted_settings = existing_rows_by_project_id.get(project_id)
        action = "updated" if persisted_settings is not None else "created"
        if persisted_settings is None:
            persisted_settings = TransportAIProjectLlmSettings(
                project_id=project.id,
                provider=legacy_settings.provider,
                model_name=legacy_settings.model_name,
                reasoning_effort=legacy_settings.reasoning_effort,
                api_key_ciphertext=legacy_settings.api_key_ciphertext,
                api_key_last4=legacy_settings.api_key_last4,
                updated_by_admin_id=legacy_settings.updated_by_admin_id,
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(persisted_settings)
        else:
            persisted_settings.provider = legacy_settings.provider
            persisted_settings.model_name = legacy_settings.model_name
            persisted_settings.reasoning_effort = legacy_settings.reasoning_effort
            persisted_settings.api_key_ciphertext = legacy_settings.api_key_ciphertext
            persisted_settings.api_key_last4 = legacy_settings.api_key_last4
            persisted_settings.updated_by_admin_id = legacy_settings.updated_by_admin_id
            persisted_settings.updated_at = timestamp

        project_summaries.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "action": action,
            }
        )

    db.flush()
    return {
        "backfilled_at": timestamp.isoformat(),
        "legacy_settings_id": legacy_settings.id,
        "provider": legacy_settings.provider,
        "model_name": legacy_settings.model_name,
        "reasoning_effort": legacy_settings.reasoning_effort,
        "project_count": len(project_summaries),
        "overwrite_existing": overwrite_existing,
        "projects": project_summaries,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy the encrypted legacy Transport AI LLM settings row into explicit project-scoped rows. "
            "This command never chooses target projects automatically."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=settings.database_url,
        help="SQLAlchemy database URL. Defaults to the configured DATABASE_URL.",
    )
    parser.add_argument(
        "--project-id",
        dest="project_ids",
        action="append",
        type=int,
        required=True,
        help="Project id to receive the copied legacy Transport AI settings. Repeat for multiple projects.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Replace an existing project-scoped row for the explicit targets instead of failing closed.",
    )
    parser.add_argument(
        "--output",
        help="Optional path where the JSON summary should be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    engine, session_factory = build_session_factory(args.database_url)
    try:
        with session_factory() as db:
            try:
                payload = backfill_transport_ai_project_llm_settings(
                    db,
                    project_ids=args.project_ids,
                    overwrite_existing=args.overwrite_existing,
                )
            except TransportAILegacyBackfillError as exc:
                db.rollback()
                print(str(exc), file=sys.stderr)
                return 2
            db.commit()
    finally:
        engine.dispose()

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())