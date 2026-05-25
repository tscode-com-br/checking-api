"""Tests for Phase 8 / prompt 8.1 — emergency call notification SSE metadata.

These tests pin the canonical metadata shape emitted by:
  - make_emergency_call (status_event='requested') on every call, even when the
    Twilio SDK is absent (dev environment) — required by item 5.5.1 so the
    admin always sees a "solicitada" confirmation.
  - twilio_status_callback (status_event='completed' + duration_seconds +
    ended_by) when Twilio posts a status update — required by item 3.2.5.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# App bootstrap (must happen before importing the app)
# ---------------------------------------------------------------------------

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_checking.db")
os.environ.setdefault("FORMS_URL", "https://example.com/form")
os.environ.setdefault("DEVICE_SHARED_KEY", "device-test-key")
os.environ.setdefault("MOBILE_APP_SHARED_KEY", "mobile-test-key")
os.environ.setdefault("PROVIDER_SHARED_KEY", "TESTPROVIDER0001")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-session-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", "HR70")
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "eAcacdLe2")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("TRANSPORT_EXPORTS_DIR", "./test_transport_exports")

from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentCallLog,
    AdminUser,
    Project,
    User,
)
from sistema.app.services.twilio_caller import (  # noqa: E402
    format_call_number,
    make_emergency_call,
)

CALLBACK_URL = "/api/twilio/status-callback"
_NOW = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


def _make_project(db: Session) -> Project:
    p = Project(
        name="EMTEST",
        country_code="BR",
        country_name="Brasil",
        timezone_name="America/Sao_Paulo",
        address="Av Test 1",
        zip_code="01000000",
        emergency_phone="+5521988887777",
        twilio_account_sid="ACfake",
        twilio_auth_token="faketoken",
        twilio_phone_number="+15555550000",
        mobile_admin="+5521911112222",
        email_local_emergency="emergency@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _make_admin(db: Session) -> AdminUser:
    a = AdminUser(
        chave="ADM1",
        nome_completo="Adm Notif",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.flush()
    return a


def _make_accident(db: Session, proj: Project, admin: AdminUser, accident_number: int = 0) -> Accident:
    a = Accident(
        accident_number=accident_number,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Sala B",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=_NOW,
        description="Descrição teste",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.flush()
    return a


# ---------------------------------------------------------------------------
# format_call_number helper
# ---------------------------------------------------------------------------


def test_format_call_number_is_six_digits_zero_padded():
    assert format_call_number(1) == "000001"
    assert format_call_number(42) == "000042"
    assert format_call_number(999999) == "999999"
    # Numbers wider than 6 digits are not truncated — the spec is "vitalício"
    # and uses zfill, which only pads (never truncates).
    assert format_call_number(1234567) == "1234567"


# ---------------------------------------------------------------------------
# make_emergency_call without Twilio SDK (the dev path) — must still emit the
# 'requested' SSE so the admin sees a confirmation.
# ---------------------------------------------------------------------------


def test_make_emergency_call_emits_requested_sse_with_six_digit_label_when_sdk_missing(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin, accident_number=1)
    db.commit()

    mock_notify = MagicMock()

    # Force the lazy `from twilio.rest import Client` inside make_emergency_call
    # to ImportError. Patching the builtin import isolates the failure to the
    # SDK lookup without disabling the test runner's own imports.
    import builtins
    real_import = builtins.__import__

    def _import_blocker(name, *args, **kwargs):
        if name.startswith("twilio"):
            raise ImportError(f"blocked twilio import for test ({name})")
        return real_import(name, *args, **kwargs)

    with (
        patch("sistema.app.services.twilio_caller.notify_admin_data_changed", mock_notify),
        patch("sistema.app.services.twilio_caller.send_emergency_notification_email"),
        patch("builtins.__import__", side_effect=_import_blocker),
    ):
        log = make_emergency_call(
            db,
            accident=accident,
            project=proj,
            triggered_by_admin_user=admin,
            reporter_name="Adm Notif",
            reporter_local="Sala B",
            event_time=_NOW,
        )

    # No exception raised — the dev path now degrades gracefully.
    assert isinstance(log, AccidentCallLog)
    assert log.call_status == "queued"
    assert log.call_sid is None

    # The 'requested' notification must have fired with the canonical metadata.
    requested_calls = [
        call for call in mock_notify.call_args_list
        if call.args and call.args[0] == "emergency_call_initiated"
    ]
    assert len(requested_calls) == 1, mock_notify.call_args_list
    metadata = requested_calls[0].kwargs.get("metadata") or {}
    assert metadata["status_event"] == "requested"
    assert metadata["call_number"] == log.call_number
    assert metadata["call_number_label"] == format_call_number(log.call_number)
    assert len(metadata["call_number_label"]) == 6
    assert metadata["accident_id"] == accident.id
    assert metadata["project_id"] == proj.id
    assert metadata["project_name"] == "EMTEST"
    assert metadata["triggered_by_role"] == "admin"
    assert metadata["triggered_by_name"] == "Adm Notif"
    assert metadata["triggered_by_chave"] == "ADM1"


def test_make_emergency_call_call_number_is_strictly_increasing_per_db(tmp_path: Path):
    """call_number is global and vitalício — each call increments it by 1."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident_a = _make_accident(db, proj, admin, accident_number=10)
    # Close A before opening B because the partial unique index permits only one
    # active accident per project (ix_accidents_single_active_per_project).
    accident_a.closed_at = _NOW
    db.flush()
    accident_b = _make_accident(db, proj, admin, accident_number=11)
    db.commit()

    import builtins
    real_import = builtins.__import__

    def _import_blocker(name, *args, **kwargs):
        if name.startswith("twilio"):
            raise ImportError("blocked twilio import for test")
        return real_import(name, *args, **kwargs)

    with (
        patch("sistema.app.services.twilio_caller.notify_admin_data_changed"),
        patch("sistema.app.services.twilio_caller.send_emergency_notification_email"),
        patch("builtins.__import__", side_effect=_import_blocker),
    ):
        log1 = make_emergency_call(
            db, accident=accident_a, project=proj,
            triggered_by_admin_user=admin, reporter_name="A", reporter_local="loc", event_time=_NOW,
        )
        log2 = make_emergency_call(
            db, accident=accident_b, project=proj,
            triggered_by_admin_user=admin, reporter_name="A", reporter_local="loc", event_time=_NOW,
        )

    assert log2.call_number == log1.call_number + 1


# ---------------------------------------------------------------------------
# twilio_status_callback — when Twilio posts a 'completed' status, the SSE
# metadata must include duration_seconds, ended_by and status_event='completed'.
# ---------------------------------------------------------------------------


def test_twilio_status_callback_completed_emits_rich_sse(tmp_path: Path):
    """A 'completed' callback updates the log and fires SSE with full metadata."""
    # We cannot reuse the file-based session from helpers above because the API
    # uses its own SessionLocal. Instead set up the data via the global app DB.
    from sistema.app.database import SessionLocal as AppSessionLocal

    # Clean slate, then create the required rows in the app DB.
    with AppSessionLocal() as db:
        db.execute(sa.delete(AccidentCallLog))
        # Close any leftover active accident from previous test runs that
        # would otherwise collide with ix_accidents_single_active_per_project.
        db.execute(
            sa.update(Accident)
            .where(Accident.closed_at.is_(None))
            .values(closed_at=_NOW, updated_at=_NOW)
        )
        db.commit()
        # Reuse an existing project; create one if absent.
        proj = db.execute(sa.select(Project).where(Project.name == "EMTEST_CB")).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name="EMTEST_CB",
                country_code="BR",
                country_name="Brasil",
                timezone_name="America/Sao_Paulo",
                address="Av Test 2",
                zip_code="01001000",
                emergency_phone="+5521988887777",
            )
            db.add(proj)
            db.flush()
        admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == "ADCB")).scalar_one_or_none()
        if admin is None:
            admin = AdminUser(
                chave="ADCB", nome_completo="Adm Callback",
                created_at=_NOW, updated_at=_NOW,
            )
            db.add(admin)
            db.flush()
        # Pick an accident_number that does not collide with previous test runs
        # (the UniqueConstraint on accidents.accident_number is global).
        next_number = int(
            db.execute(sa.text("SELECT COALESCE(MAX(accident_number), 0) + 1 FROM accidents")).scalar_one()
        )
        accident = Accident(
            accident_number=next_number,
            project_id=proj.id,
            project_name_snapshot=proj.name,
            location_name_snapshot="Sala C",
            location_is_registered=False,
            origin="admin",
            opened_by_admin_id=admin.id,
            opened_at=_NOW,
            description="cb",
            created_at=_NOW,
            updated_at=_NOW,
        )
        db.add(accident)
        db.flush()
        log = AccidentCallLog(
            call_number=next_number,
            call_sid="CAcallbacktest123",
            accident_id=accident.id,
            project_id=proj.id,
            triggered_by_admin_id=admin.id,
            to_phone="+5521988887777",
            from_phone="+15555550000",
            call_status="initiated",
            message_twiml="<Response/>",
            created_at=_NOW,
            updated_at=_NOW,
        )
        db.add(log)
        db.commit()
        call_sid = log.call_sid
        log_id = log.id
        expected_call_number = log.call_number
        expected_label = format_call_number(expected_call_number)

    mock_notify = MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    with patch("sistema.app.routers.twilio_callbacks.notify_admin_data_changed", mock_notify):
        resp = client.post(
            CALLBACK_URL,
            data={"CallSid": call_sid, "CallStatus": "completed", "CallDuration": "47"},
        )
    assert resp.status_code == 200, resp.text

    # AccidentCallLog row was updated.
    with AppSessionLocal() as db:
        log_row = db.get(AccidentCallLog, log_id)
        assert log_row.call_status == "completed"
        assert log_row.duration_seconds == 47
        assert log_row.ended_by == "system"

    # SSE notification was emitted with the canonical metadata.
    notify_calls = [
        call for call in mock_notify.call_args_list
        if call.args and call.args[0] == "emergency_call_status_update"
    ]
    assert len(notify_calls) == 1, mock_notify.call_args_list
    metadata = notify_calls[0].kwargs.get("metadata") or {}
    assert metadata["status_event"] == "completed"
    assert metadata["call_status"] == "completed"
    assert metadata["duration_seconds"] == 47
    assert metadata["ended_by"] == "system"
    assert metadata["call_number_label"] == expected_label
    assert len(metadata["call_number_label"]) == 6


def test_twilio_status_callback_unknown_sid_is_no_op():
    """Callback for an unknown call_sid returns 200 and does not crash."""
    mock_notify = MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    with patch("sistema.app.routers.twilio_callbacks.notify_admin_data_changed", mock_notify):
        resp = client.post(
            CALLBACK_URL,
            data={"CallSid": "CAnonexistentsid", "CallStatus": "completed"},
        )
    assert resp.status_code == 200
    # No SSE fired because there was no matching log.
    mock_notify.assert_not_called()
