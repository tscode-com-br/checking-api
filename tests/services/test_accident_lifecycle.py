"""Tests for Task C2 — accident_lifecycle service."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    ManagedLocation,
    Project,
    User,
)
from sistema.app.services.accident_lifecycle import (
    AccidentAlreadyActiveError,
    InvalidAccidentLocationError,
    NoActiveAccidentError,
    attach_video_upload,
    close_accident,
    list_active_accident,
    open_accident,
    update_accident_membership_for_check_event,
    upsert_user_safety_report,
)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

def _make_session(tmp_path: Path, name: str = "test.db") -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / name).as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _create_project(db: Session, name: str = "PROJ") -> Project:
    now = datetime.now(timezone.utc)
    proj = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="123456",
    )
    db.add(proj)
    db.flush()
    return proj


def _create_admin(db: Session, chave: str = "A001") -> AdminUser:
    now = datetime.now(timezone.utc)
    admin = AdminUser(
        chave=chave,
        nome_completo="Admin Test",
        created_at=now,
        updated_at=now,
    )
    db.add(admin)
    db.flush()
    return admin


def _create_user(
    db: Session,
    chave: str,
    *,
    checkin: bool = True,
    local: str | None = "Sala 1",
) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        chave=chave,
        nome=f"User {chave}",
        projeto="PROJ",
        checkin=checkin,
        local=local,
        time=now if checkin else None,
        last_active_at=now,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    return user


def _create_location(
    db: Session,
    local: str = "Gate A",
    projects: list[str] | None = None,
) -> ManagedLocation:
    now = datetime.now(timezone.utc)
    loc = ManagedLocation(
        local=local,
        latitude=1.0,
        longitude=103.0,
        projects_json=json.dumps(projects or []),
        tolerance_meters=50,
        created_at=now,
        updated_at=now,
    )
    db.add(loc)
    db.flush()
    return loc


def _open_simple(db: Session, project: Project, admin: AdminUser) -> Accident:
    """Open an accident with minimal kwargs for convenience."""
    return open_accident(
        db,
        origin="admin",
        project_id=project.id,
        custom_location_name="Zone A",
        opened_by_admin_id=admin.id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_open_accident_creates_with_number_zero(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    accident = _open_simple(db, proj, admin)

    assert accident.accident_number == 0
    assert accident.origin == "admin"
    assert accident.project_name_snapshot == proj.name
    assert accident.location_name_snapshot == "Zone A"
    assert accident.location_is_registered is False
    assert accident.closed_at is None


def test_open_accident_raises_when_already_active(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    _open_simple(db, proj, admin)

    with pytest.raises(AccidentAlreadyActiveError):
        _open_simple(db, proj, admin)


def test_close_accident_marks_closed_at_and_admin(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    accident = _open_simple(db, proj, admin)
    closed = close_accident(db, accident=accident, closed_by_admin_id=admin.id)

    assert closed.closed_at is not None
    assert closed.closed_by_admin_id == admin.id


def test_close_then_open_increments_number(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    acc1 = _open_simple(db, proj, admin)
    close_accident(db, accident=acc1, closed_by_admin_id=admin.id)
    acc2 = _open_simple(db, proj, admin)

    assert acc1.accident_number == 0
    assert acc2.accident_number == 1


def test_open_admin_validates_location_belongs_to_project(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db, name="ALPHA")
    admin = _create_admin(db)
    # Location belongs to a different project
    loc = _create_location(db, projects=["BETA"])

    with pytest.raises(InvalidAccidentLocationError):
        open_accident(
            db,
            origin="admin",
            project_id=proj.id,
            location_id=loc.id,
            opened_by_admin_id=admin.id,
        )


def test_open_web_accepts_location_from_other_project(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db, name="ALPHA")
    user = _create_user(db, "U001", checkin=False)
    # Location belongs to a different project — web should accept it anyway
    loc = _create_location(db, projects=["BETA"])

    accident = open_accident(
        db,
        origin="web",
        project_id=proj.id,
        location_id=loc.id,
        opened_by_user_id=user.id,
        reporter_zone="safety",
        reporter_status="ok",
    )

    assert accident.location_name_snapshot == loc.local
    assert accident.location_is_registered is True


def test_open_prepopulates_user_reports_for_checked_in_users(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    u1 = _create_user(db, "U001", checkin=True)
    u2 = _create_user(db, "U002", checkin=True)
    _create_user(db, "U003", checkin=False)  # not checked in — should be skipped

    accident = _open_simple(db, proj, admin)

    reports = db.execute(
        select(AccidentUserReport).where(AccidentUserReport.accident_id == accident.id)
    ).scalars().all()
    user_ids = {r.user_id for r in reports}

    assert len(reports) == 2
    assert u1.id in user_ids
    assert u2.id in user_ids
    assert all(r.zone == "waiting" for r in reports)
    assert all(r.status == "waiting" for r in reports)


def test_open_web_sets_reporter_zone_status_for_author(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    # Author is checked-in
    author = _create_user(db, "AUTH", checkin=True)

    accident = open_accident(
        db,
        origin="web",
        project_id=proj.id,
        custom_location_name="Field B",
        opened_by_user_id=author.id,
        reporter_zone="safety",
        reporter_status="ok",
    )

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == author.id,
        )
    ).scalar_one()

    assert report.zone == "safety"
    assert report.status == "ok"
    assert report.reported_at is not None


def test_open_web_creates_report_for_non_checkedin_author(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    # Author is NOT checked-in
    author = _create_user(db, "AUTH", checkin=False)

    accident = open_accident(
        db,
        origin="web",
        project_id=proj.id,
        custom_location_name="Field B",
        opened_by_user_id=author.id,
        reporter_zone="accident",
        reporter_status="help",
    )

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == author.id,
        )
    ).scalar_one()

    assert report.zone == "accident"
    assert report.status == "help"
    assert report.reported_at is not None


def test_close_raises_when_not_active(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    accident = _open_simple(db, proj, admin)
    close_accident(db, accident=accident, closed_by_admin_id=admin.id)

    with pytest.raises(NoActiveAccidentError):
        close_accident(db, accident=accident, closed_by_admin_id=admin.id)


def test_open_publishes_to_both_brokers(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed") as mock_admin,
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed") as mock_web,
    ):
        _open_simple(db, proj, admin)

    mock_admin.assert_called_once_with(
        "accident_opened",
        metadata={
            "accident_id": mock_admin.call_args.kwargs["metadata"]["accident_id"],
            "accident_number_label": "0000",
            "project_name": proj.name,
        },
    )
    mock_web.assert_called_once()
    assert mock_web.call_args.args[0] == "accident_opened"


def test_close_publishes_to_both_brokers(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed") as mock_admin,
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed") as mock_web,
    ):
        close_accident(db, accident=accident, closed_by_admin_id=admin.id)

    mock_admin.assert_called_once_with("accident_closed", metadata=mock_admin.call_args.kwargs["metadata"])
    mock_web.assert_called_once_with("accident_closed", metadata=mock_web.call_args.kwargs["metadata"])


# ---------------------------------------------------------------------------
# Task C3 — upsert_user_safety_report / attach_video_upload / check event
# ---------------------------------------------------------------------------

def test_upsert_creates_when_missing(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U001", checkin=False)

    report, fired = upsert_user_safety_report(
        db, accident=accident, user=user, zone="safety", status="ok"
    )

    assert report.accident_id == accident.id
    assert report.user_id == user.id
    assert report.zone == "safety"
    assert report.status == "ok"
    assert report.created_at is not None
    assert fired is False


def test_upsert_updates_when_existing_and_preserves_created_at(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U002", checkin=False)

    report1, _ = upsert_user_safety_report(
        db, accident=accident, user=user, zone="waiting", status="waiting"
    )
    original_created_at = report1.created_at

    report2, _ = upsert_user_safety_report(
        db, accident=accident, user=user, zone="accident", status="ok"
    )

    assert report2.id == report1.id
    assert report2.zone == "accident"
    assert report2.status == "ok"
    assert report2.created_at == original_created_at


def test_upsert_fires_help_only_on_transition(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U003", checkin=False)

    _, fired1 = upsert_user_safety_report(
        db, accident=accident, user=user, zone="accident", status="ok"
    )
    assert fired1 is False

    _, fired2 = upsert_user_safety_report(
        db, accident=accident, user=user, zone="accident", status="help"
    )
    assert fired2 is True


def test_upsert_does_not_fire_help_on_consecutive_help(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U004", checkin=False)

    upsert_user_safety_report(db, accident=accident, user=user, zone="accident", status="help")
    _, fired = upsert_user_safety_report(
        db, accident=accident, user=user, zone="accident", status="help"
    )
    assert fired is False


def test_attach_video_inserts_first_time(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U005", checkin=False)

    upload = attach_video_upload(
        db,
        accident=accident,
        user=user,
        object_key="videos/test.mp4",
        public_url="https://example.com/videos/test.mp4",
        content_type="video/mp4",
        size_bytes=1024 * 1024,
        duration_seconds=30,
        idempotency_key="idem-001",
    )

    assert upload.id is not None
    assert upload.accident_id == accident.id
    assert upload.idempotency_key == "idem-001"


def test_attach_video_idempotent_by_key(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U006", checkin=False)

    upload1 = attach_video_upload(
        db,
        accident=accident,
        user=user,
        object_key="videos/test.mp4",
        public_url="https://example.com/videos/test.mp4",
        content_type="video/mp4",
        size_bytes=1024,
        duration_seconds=None,
        idempotency_key="idem-002",
    )
    upload2 = attach_video_upload(
        db,
        accident=accident,
        user=user,
        object_key="videos/different.mp4",
        public_url="https://example.com/different.mp4",
        content_type="video/mp4",
        size_bytes=2048,
        duration_seconds=None,
        idempotency_key="idem-002",
    )

    assert upload1.id == upload2.id
    assert upload2.object_key == "videos/test.mp4"


def test_check_event_hook_creates_waiting_row_for_new_user(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U007", checkin=False)

    from datetime import datetime, timezone as tz
    event_time = datetime.now(tz.utc)

    update_accident_membership_for_check_event(
        db, accident=accident, user=user, action="check-in", event_time=event_time
    )

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one()

    assert report.zone == "waiting"
    assert report.status == "waiting"
    assert report.last_checkin_action == "check-in"
    assert report.last_action_at == event_time.replace(tzinfo=None)


def test_check_event_hook_preserves_zone_status_when_user_already_reported(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    accident = _open_simple(db, proj, admin)
    user = _create_user(db, "U008", checkin=False)

    upsert_user_safety_report(db, accident=accident, user=user, zone="accident", status="ok")

    from datetime import datetime, timezone as tz
    event_time = datetime.now(tz.utc)

    update_accident_membership_for_check_event(
        db, accident=accident, user=user, action="check-out", event_time=event_time
    )

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one()

    assert report.zone == "accident"
    assert report.status == "ok"
    assert report.last_checkin_action == "check-out"
