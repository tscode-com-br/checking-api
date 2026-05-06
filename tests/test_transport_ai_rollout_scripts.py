from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from scripts.backfill_transport_ai_project_llm_settings import (
    TransportAILegacyBackfillError,
    backfill_transport_ai_project_llm_settings,
)
from scripts.export_transport_ai_legacy_llm_settings import export_legacy_transport_ai_llm_settings
from sistema.app.database import Base
from sistema.app.models import AdminUser, Project, TransportAILlmSettings, TransportAIProjectLlmSettings


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _build_session_factory(db_path: Path):
    engine = sa.create_engine(_build_database_url(db_path))
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 5, 10, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _create_admin_user(session: Session, *, chave: str = "AI08") -> AdminUser:
    timestamp = _fixture_timestamp()
    admin_user = AdminUser(
        chave=chave,
        nome_completo="Transport AI Rollout Admin",
        password_hash=None,
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=None,
        password_reset_requested_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(admin_user)
    session.flush()
    return admin_user


def _create_project(session: Session, *, name: str) -> Project:
    project = Project(
        name=name,
        country_code="BR",
        country_name="Brazil",
        timezone_name="America/Sao_Paulo",
        address="Rua Teste, 100",
        zip_code="01000-000",
    )
    session.add(project)
    session.flush()
    return project


def _create_legacy_settings(session: Session, *, admin_user_id: int) -> TransportAILlmSettings:
    timestamp = _fixture_timestamp()
    legacy_settings = TransportAILlmSettings(
        id=1,
        provider="deepseek",
        model_name="deepseek-v4-pro",
        reasoning_effort="high",
        api_key_ciphertext="encrypted-ciphertext",
        api_key_last4="367a",
        updated_by_admin_id=admin_user_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(legacy_settings)
    session.flush()
    return legacy_settings


def test_export_legacy_transport_ai_llm_settings_redacts_ciphertext_only_when_requested(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_rollout_export.db")
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            _create_legacy_settings(session, admin_user_id=admin_user.id)
            session.commit()

            exported_payload = export_legacy_transport_ai_llm_settings(session)
            redacted_payload = export_legacy_transport_ai_llm_settings(session, include_ciphertext=False)

        assert exported_payload["legacy_settings_present"] is True
        assert exported_payload["settings"]["api_key_hint"] == "***367a"
        assert exported_payload["settings"]["api_key_ciphertext"] == "encrypted-ciphertext"
        assert redacted_payload["settings"]["api_key_ciphertext"] is None
    finally:
        engine.dispose()


def test_transport_ai_project_llm_settings_do_not_backfill_automatically(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_rollout_no_auto_backfill.db")
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            _create_project(session, name="Projeto Sem Backfill 1")
            _create_project(session, name="Projeto Sem Backfill 2")
            _create_legacy_settings(session, admin_user_id=admin_user.id)
            session.commit()

            persisted_rows = session.query(TransportAIProjectLlmSettings).all()

        assert persisted_rows == []
    finally:
        engine.dispose()


def test_backfill_transport_ai_project_llm_settings_requires_explicit_targets_and_copies_legacy_values(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_rollout_backfill.db")
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            first_project = _create_project(session, name="Projeto Primeiro")
            second_project = _create_project(session, name="Projeto Segundo")
            _create_legacy_settings(session, admin_user_id=admin_user.id)

            payload = backfill_transport_ai_project_llm_settings(
                session,
                project_ids=[first_project.id, second_project.id],
            )
            session.commit()

            persisted_rows = (
                session.query(TransportAIProjectLlmSettings)
                .order_by(TransportAIProjectLlmSettings.project_id.asc())
                .all()
            )

        assert payload["project_count"] == 2
        assert [row["action"] for row in payload["projects"]] == ["created", "created"]
        assert [row.project_id for row in persisted_rows] == [first_project.id, second_project.id]
        assert all(row.provider == "deepseek" for row in persisted_rows)
        assert all(row.model_name == "deepseek-v4-pro" for row in persisted_rows)
        assert all(row.reasoning_effort == "high" for row in persisted_rows)
        assert all(row.api_key_ciphertext == "encrypted-ciphertext" for row in persisted_rows)
        assert all(row.api_key_last4 == "367a" for row in persisted_rows)
        assert all(row.updated_by_admin_id == admin_user.id for row in persisted_rows)
    finally:
        engine.dispose()


def test_backfill_transport_ai_project_llm_settings_fails_closed_when_target_already_has_settings(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_rollout_existing.db")
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="Projeto Existente")
            legacy_settings = _create_legacy_settings(session, admin_user_id=admin_user.id)
            session.add(
                TransportAIProjectLlmSettings(
                    project_id=project.id,
                    provider="openai",
                    model_name="gpt-5.4-2026-03-05",
                    reasoning_effort="high",
                    api_key_ciphertext="already-present",
                    api_key_last4="1234",
                    updated_by_admin_id=admin_user.id,
                    created_at=legacy_settings.created_at,
                    updated_at=legacy_settings.updated_at,
                )
            )
            session.commit()

            try:
                backfill_transport_ai_project_llm_settings(session, project_ids=[project.id])
                raise AssertionError("backfill should fail when the destination project already has settings")
            except TransportAILegacyBackfillError as exc:
                assert "already have project-scoped Transport AI settings" in str(exc)
                session.rollback()
    finally:
        engine.dispose()