from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    EmailDeliveryLog,
    Project,
    User,
)


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _build_session_factory(tmp_path: Path, filename: str) -> tuple[sessionmaker[Session], sa.Engine]:
    engine = sa.create_engine(_build_database_url(tmp_path / filename))
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _create_project(session: Session, name: str = "P83") -> Project:
    project = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Test Street",
        zip_code="123456",
    )
    session.add(project)
    session.flush()
    return project


def _create_admin_user(session: Session, chave: str = "A001") -> AdminUser:
    now = datetime.now(timezone.utc)
    admin_user = AdminUser(
        chave=chave,
        nome_completo=f"Admin {chave}",
        password_hash=None,
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=None,
        password_reset_requested_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(admin_user)
    session.flush()
    return admin_user


def _create_user(session: Session, chave: str = "U001", projeto: str = "P83") -> User:
    now = datetime.now(timezone.utc)
    user = User(
        rfid=None,
        chave=chave,
        senha=None,
        perfil=0,
        admin_monitored_projects_json=None,
        nome=f"User {chave}",
        projeto=projeto,
        workplace=None,
        vehicle_id=None,
        placa=None,
        end_rua=None,
        zip=None,
        email=None,
        local=None,
        checkin=None,
        time=None,
        last_active_at=now,
        inactivity_days=0,
    )
    session.add(user)
    session.flush()
    return user


def _build_open_accident(*, number: int, project_id: int, opened_by_admin_id: int) -> Accident:
    now = datetime.now(timezone.utc)
    return Accident(
        accident_number=number,
        project_id=project_id,
        project_name_snapshot="P83",
        location_name_snapshot="Office",
        location_is_registered=True,
        origin="admin",
        opened_by_admin_id=opened_by_admin_id,
        opened_by_user_id=None,
        opened_at=now,
        closed_by_admin_id=None,
        closed_at=None,
        archive_object_key=None,
        created_at=now,
        updated_at=now,
    )


def test_accident_columns_match_spec(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_columns.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            now = datetime.now(timezone.utc)

            accident = Accident(
                accident_number=0,
                project_id=project.id,
                project_name_snapshot=project.name,
                location_name_snapshot="Office",
                location_is_registered=True,
                origin="admin",
                opened_by_admin_id=admin_user.id,
                opened_by_user_id=None,
                opened_at=now,
                closed_by_admin_id=admin_user.id,
                closed_at=now,
                archive_object_key="archives/accident-0.zip",
                created_at=now,
                updated_at=now,
            )
            session.add(accident)
            session.flush()

            assert accident.id is not None
    finally:
        engine.dispose()


def test_accident_origin_constraint(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_origin.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            now = datetime.now(timezone.utc)
            accident = Accident(
                accident_number=1,
                project_id=project.id,
                project_name_snapshot=project.name,
                location_name_snapshot="Office",
                location_is_registered=True,
                origin="invalid",
                opened_by_admin_id=admin_user.id,
                opened_by_user_id=None,
                opened_at=now,
                closed_by_admin_id=None,
                closed_at=now,
                archive_object_key=None,
                created_at=now,
                updated_at=now,
            )
            session.add(accident)

            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_accident_number_non_negative_constraint(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_number.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            now = datetime.now(timezone.utc)
            accident = Accident(
                accident_number=-1,
                project_id=project.id,
                project_name_snapshot=project.name,
                location_name_snapshot="Office",
                location_is_registered=True,
                origin="admin",
                opened_by_admin_id=admin_user.id,
                opened_by_user_id=None,
                opened_at=now,
                closed_by_admin_id=None,
                closed_at=now,
                archive_object_key=None,
                created_at=now,
                updated_at=now,
            )
            session.add(accident)

            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_single_active_accident_partial_index(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_active_index.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            first = _build_open_accident(
                number=10,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(first)
            session.commit()

            second = _build_open_accident(
                number=11,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(second)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
            session.rollback()

            first_persisted = session.get(Accident, first.id)
            assert first_persisted is not None
            first_persisted.closed_at = datetime.now(timezone.utc)
            first_persisted.closed_by_admin_id = admin_user.id
            first_persisted.updated_at = datetime.now(timezone.utc)
            session.commit()

            third = _build_open_accident(
                number=12,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(third)
            session.flush()
            assert third.id is not None
    finally:
        engine.dispose()


def test_accident_user_report_zone_status_constraints(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_user_report_constraints.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            user = _create_user(session, chave="U010", projeto=project.name)
            accident = _build_open_accident(
                number=20,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(accident)
            session.flush()

            now = datetime.now(timezone.utc)
            invalid_zone = AccidentUserReport(
                accident_id=accident.id,
                user_id=user.id,
                user_chave_snapshot=user.chave,
                user_name_snapshot=user.nome,
                user_phone_snapshot=None,
                user_projects_snapshot=json.dumps([project.name]),
                user_local_snapshot="Office",
                zone="invalid",
                status="waiting",
                reported_at=now,
                last_checkin_action=None,
                last_action_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(invalid_zone)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
            session.rollback()

            invalid_status = AccidentUserReport(
                accident_id=accident.id,
                user_id=user.id,
                user_chave_snapshot=user.chave,
                user_name_snapshot=user.nome,
                user_phone_snapshot=None,
                user_projects_snapshot=json.dumps([project.name]),
                user_local_snapshot="Office",
                zone="waiting",
                status="invalid",
                reported_at=now,
                last_checkin_action=None,
                last_action_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(invalid_status)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_accident_user_report_unique_per_user_per_accident(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_user_report_unique.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            user = _create_user(session, chave="U011", projeto=project.name)
            accident = _build_open_accident(
                number=30,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(accident)
            session.flush()
            now = datetime.now(timezone.utc)

            first = AccidentUserReport(
                accident_id=accident.id,
                user_id=user.id,
                user_chave_snapshot=user.chave,
                user_name_snapshot=user.nome,
                user_phone_snapshot="65550101",
                user_projects_snapshot=json.dumps([project.name]),
                user_local_snapshot="Office",
                zone="waiting",
                status="ok",
                reported_at=now,
                last_checkin_action="check-in",
                last_action_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(first)
            session.flush()

            duplicate = AccidentUserReport(
                accident_id=accident.id,
                user_id=user.id,
                user_chave_snapshot=user.chave,
                user_name_snapshot=user.nome,
                user_phone_snapshot="65550101",
                user_projects_snapshot=json.dumps([project.name]),
                user_local_snapshot="Office",
                zone="safety",
                status="help",
                reported_at=now,
                last_checkin_action="check-out",
                last_action_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(duplicate)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_accident_video_upload_idempotency_key_unique(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_video_upload_unique.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            user = _create_user(session, chave="U020", projeto=project.name)
            accident = _build_open_accident(
                number=40,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(accident)
            session.flush()
            now = datetime.now(timezone.utc)

            first = AccidentVideoUpload(
                idempotency_key="idem-key-001",
                accident_id=accident.id,
                user_id=user.id,
                object_key="videos/a.mp4",
                public_url="https://cdn.example.com/videos/a.mp4",
                content_type="video/mp4",
                size_bytes=1024,
                duration_seconds=5,
                captured_at=now,
                created_at=now,
            )
            session.add(first)
            session.flush()

            duplicate = AccidentVideoUpload(
                idempotency_key="idem-key-001",
                accident_id=accident.id,
                user_id=user.id,
                object_key="videos/b.mp4",
                public_url="https://cdn.example.com/videos/b.mp4",
                content_type="video/mp4",
                size_bytes=2048,
                duration_seconds=10,
                captured_at=now,
                created_at=now,
            )
            session.add(duplicate)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_accident_archive_unique_per_accident(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "accident_archive_unique.db")
    try:
        with session_factory() as session:
            project = _create_project(session)
            admin_user = _create_admin_user(session)
            accident = _build_open_accident(
                number=50,
                project_id=project.id,
                opened_by_admin_id=admin_user.id,
            )
            session.add(accident)
            session.flush()
            now = datetime.now(timezone.utc)

            first = AccidentArchive(
                accident_id=accident.id,
                snapshot_json=json.dumps({"accident_id": accident.id}),
                xlsx_object_key="archives/a.xlsx",
                zip_object_key="archives/a.zip",
                size_bytes=4096,
                generated_at=now,
            )
            session.add(first)
            session.flush()

            duplicate = AccidentArchive(
                accident_id=accident.id,
                snapshot_json=json.dumps({"accident_id": accident.id, "v": 2}),
                xlsx_object_key="archives/b.xlsx",
                zip_object_key="archives/b.zip",
                size_bytes=8192,
                generated_at=now,
            )
            session.add(duplicate)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_email_delivery_log_status_constraint(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path, "email_delivery_status.db")
    try:
        with session_factory() as session:
            user = _create_user(session, chave="U030", projeto="P83")
            now = datetime.now(timezone.utc)
            log = EmailDeliveryLog(
                accident_id=None,
                triggered_by_user_id=user.id,
                recipient_email="recipient@example.com",
                recipient_chave=user.chave,
                subject="Test subject",
                body_snapshot="Body",
                delivery_status="invalid",
                error_message=None,
                queued_at=now,
                sent_at=None,
                retry_count=0,
            )
            session.add(log)
            with pytest.raises(sa.exc.IntegrityError):
                session.flush()
    finally:
        engine.dispose()
