"""Tests for Phase 8.2 — persistent emergency call notification feed.

Validates:
1. record_call_notification persists a row with localized pt-BR message.
2. make_emergency_call (without SDK) writes the 'requested' notification row.
3. twilio_status_callback writes a 'completed' notification row.
4. GET /api/admin/accidents/{id}/notifications returns the rows ordered by occurred_at.
5. Cascade: deleting the parent Accident deletes its notification rows.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
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
from sistema.app.database import SessionLocal as AppSessionLocal  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentArchive,
    AccidentCallLog,
    AccidentCallNotification,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    Project,
    User,
)
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.twilio_caller import (  # noqa: E402
    _build_call_notification_metadata,
    make_emergency_call,
    record_call_notification,
)

CALLBACK_URL = "/api/twilio/status-callback"
ADMIN_LOGIN_URL = "/api/admin/auth/login"
_NOW = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)

_ADMIN_CHAVE = "PERS"
_ADMIN_PASSWORD = "PersTest!1"


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


def _make_project(db: Session, name: str = "PERS_PROJ") -> Project:
    p = Project(
        name=name,
        country_code="BR",
        country_name="Brasil",
        timezone_name="America/Sao_Paulo",
        address="Av 1",
        zip_code="01010101",
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


def _make_admin(db: Session, chave: str = "ADP1") -> AdminUser:
    a = AdminUser(
        chave=chave,
        nome_completo="Adm Pers",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.flush()
    return a


def _make_accident(db: Session, proj: Project, admin: AdminUser, accident_number: int) -> Accident:
    a = Accident(
        accident_number=accident_number,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Sala P",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=_NOW,
        description="persistência",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.flush()
    return a


def _make_call_log(db: Session, accident: Accident, project: Project, admin: AdminUser, call_number: int) -> AccidentCallLog:
    log = AccidentCallLog(
        call_number=call_number,
        call_sid=None,
        accident_id=accident.id,
        project_id=project.id,
        triggered_by_admin_id=admin.id,
        to_phone="+5521988887777",
        from_phone="+15555550000",
        call_status="queued",
        message_twiml="<Response/>",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(log)
    db.flush()
    return log


# ---------------------------------------------------------------------------
# record_call_notification — unit
# ---------------------------------------------------------------------------


def test_record_call_notification_persists_localized_message(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin, accident_number=100)
    log = _make_call_log(db, accident, proj, admin, call_number=1)
    db.commit()

    metadata = _build_call_notification_metadata(
        log=log,
        accident=accident,
        project=proj,
        triggered_by_name="Adm Pers",
        triggered_by_chave="ADP1",
        triggered_by_role="admin",
        status_event="requested",
        occurred_at=_NOW,
    )
    record_call_notification(db, log=log, metadata=metadata, project_timezone_name=proj.timezone_name)
    db.commit()

    rows = db.execute(sa.select(AccidentCallNotification)).scalars().all()
    assert len(rows) == 1, rows
    row = rows[0]
    assert row.call_log_id == log.id
    assert row.accident_id == accident.id
    assert row.event_type == "requested"
    # The canonical pt-BR line — check key tokens. We use São Paulo (UTC-3), so
    # 2026-05-25 10:00 UTC renders as 07:00:00 locally.
    assert "Ligação 000001 solicitada por Adm Pers (ADP1)" in row.message_pt
    assert "para o projeto PERS_PROJ" in row.message_pt
    assert "25/05/2026 07:00:00" in row.message_pt


def test_record_call_notification_handles_each_status_event(tmp_path: Path):
    """Every status_event maps to a stable, distinct pt-BR phrase."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin, accident_number=101)
    log = _make_call_log(db, accident, proj, admin, call_number=2)
    db.commit()

    cases = {
        "requested": "solicitada por",
        "initiated": "está sendo completada",
        "ringing": "está sendo completada",
        "answered": "foi atendida",
        "completed": "foi finalizada",
        "fallback_success": "foi solicitada com sucesso",
        "failed": "falhou",
        "busy": "destino ocupado",
        "no_answer": "sem resposta",
        "canceled": "foi cancelada",
    }
    for event, expected_fragment in cases.items():
        metadata = _build_call_notification_metadata(
            log=log, accident=accident, project=proj,
            triggered_by_name="Adm Pers", triggered_by_chave="ADP1",
            triggered_by_role="admin", status_event=event,
            occurred_at=_NOW + timedelta(seconds=hash(event) % 60),
            duration_seconds=42 if event == "completed" else None,
        )
        record_call_notification(db, log=log, metadata=metadata, project_timezone_name=proj.timezone_name)
    db.commit()

    rows = db.execute(sa.select(AccidentCallNotification)).scalars().all()
    msgs_by_event = {r.event_type: r.message_pt for r in rows}
    for event, fragment in cases.items():
        assert event in msgs_by_event, f"missing event {event}"
        assert fragment in msgs_by_event[event], (
            f"event {event} did not surface fragment {fragment!r}; got {msgs_by_event[event]!r}"
        )
    assert "42 segundos" in msgs_by_event["completed"]


# ---------------------------------------------------------------------------
# make_emergency_call persists 'requested' row even without Twilio SDK
# ---------------------------------------------------------------------------


def test_make_emergency_call_persists_requested_notification(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin, accident_number=200)
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
        log = make_emergency_call(
            db,
            accident=accident,
            project=proj,
            triggered_by_admin_user=admin,
            reporter_name="Adm Pers",
            reporter_local="Sala P",
            event_time=_NOW,
        )

    notifications = db.execute(
        sa.select(AccidentCallNotification).where(AccidentCallNotification.accident_id == accident.id)
    ).scalars().all()
    assert len(notifications) == 1, notifications
    n = notifications[0]
    assert n.event_type == "requested"
    assert n.call_log_id == log.id
    assert "Ligação" in n.message_pt and "solicitada por" in n.message_pt


# ---------------------------------------------------------------------------
# twilio_status_callback persists 'completed' row
# ---------------------------------------------------------------------------


def _close_all_accidents_app_db() -> None:
    with AppSessionLocal() as db:
        db.execute(sa.delete(AccidentCallNotification))
        db.execute(sa.delete(AccidentCallLog))
        db.execute(sa.delete(AccidentArchive))
        db.execute(sa.delete(AccidentVideoUpload))
        db.execute(sa.delete(AccidentUserReport))
        db.execute(
            sa.update(Accident)
            .where(Accident.closed_at.is_(None))
            .values(closed_at=_NOW, updated_at=_NOW)
        )
        db.commit()


def test_twilio_status_callback_persists_completed_notification():
    _close_all_accidents_app_db()

    with AppSessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == "PERS_CB_PROJ")).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name="PERS_CB_PROJ",
                country_code="BR",
                country_name="Brasil",
                timezone_name="America/Sao_Paulo",
                address="Av CB",
                zip_code="03030303",
                emergency_phone="+5521988887777",
            )
            db.add(proj)
            db.flush()
        admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == "PCBA")).scalar_one_or_none()
        if admin is None:
            admin = AdminUser(chave="PCBA", nome_completo="Adm CB",
                              created_at=_NOW, updated_at=_NOW)
            db.add(admin)
            db.flush()

        next_number = int(
            db.execute(sa.text("SELECT COALESCE(MAX(accident_number), 0) + 1 FROM accidents")).scalar_one()
        )
        accident = Accident(
            accident_number=next_number, project_id=proj.id,
            project_name_snapshot=proj.name, location_name_snapshot="Sala CB",
            location_is_registered=False, origin="admin",
            opened_by_admin_id=admin.id, opened_at=_NOW,
            description="cb persist", created_at=_NOW, updated_at=_NOW,
        )
        db.add(accident)
        db.flush()

        next_call_number = int(
            db.execute(sa.text("SELECT COALESCE(MAX(call_number), 0) + 1 FROM accident_call_logs")).scalar_one()
        )
        log = AccidentCallLog(
            call_number=next_call_number, call_sid="CApersistcb",
            accident_id=accident.id, project_id=proj.id,
            triggered_by_admin_id=admin.id, to_phone="+5521988887777",
            from_phone="+15555550000", call_status="initiated",
            message_twiml="<Response/>",
            created_at=_NOW, updated_at=_NOW,
        )
        db.add(log)
        db.commit()
        accident_id = accident.id
        call_sid = log.call_sid

    client = TestClient(app, raise_server_exceptions=False)
    with patch("sistema.app.routers.twilio_callbacks.notify_admin_data_changed"):
        resp = client.post(
            CALLBACK_URL,
            data={"CallSid": call_sid, "CallStatus": "completed", "CallDuration": "33"},
        )
    assert resp.status_code == 200, resp.text

    with AppSessionLocal() as db:
        rows = db.execute(
            sa.select(AccidentCallNotification).where(AccidentCallNotification.accident_id == accident_id)
        ).scalars().all()
        # We expect exactly one persisted notification — the completed one.
        assert len(rows) == 1, rows
        row = rows[0]
        assert row.event_type == "completed"
        assert "foi finalizada" in row.message_pt
        assert "33 segundos" in row.message_pt


# ---------------------------------------------------------------------------
# GET endpoint
# ---------------------------------------------------------------------------


def _logged_in_admin_client() -> TestClient:
    with AppSessionLocal() as db:
        # Need a User with admin profile to log in via /api/admin/auth/login.
        user = db.execute(sa.select(User).where(User.chave == _ADMIN_CHAVE)).scalar_one_or_none()
        if user is None:
            user = User(
                chave=_ADMIN_CHAVE, nome="Adm Endpoint",
                projeto="PERS_PROJ", checkin=False, local="Office",
                last_active_at=_NOW, inactivity_days=0,
                senha=hash_password(_ADMIN_PASSWORD), perfil=19,
            )
            db.add(user)
        else:
            user.senha = hash_password(_ADMIN_PASSWORD)
            user.perfil = 19
        db.commit()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _ADMIN_CHAVE, "senha": _ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return client


def test_endpoint_returns_notifications_ordered_by_occurred_at():
    _close_all_accidents_app_db()
    with AppSessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == "PERS_EP_PROJ")).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name="PERS_EP_PROJ", country_code="BR", country_name="Brasil",
                timezone_name="America/Sao_Paulo", address="Av EP", zip_code="04040404",
            )
            db.add(proj)
            db.flush()
        admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == "PEEA")).scalar_one_or_none()
        if admin is None:
            admin = AdminUser(chave="PEEA", nome_completo="Adm EP",
                              created_at=_NOW, updated_at=_NOW)
            db.add(admin)
            db.flush()
        next_number = int(
            db.execute(sa.text("SELECT COALESCE(MAX(accident_number), 0) + 1 FROM accidents")).scalar_one()
        )
        accident = Accident(
            accident_number=next_number, project_id=proj.id,
            project_name_snapshot=proj.name, location_name_snapshot="Sala EP",
            location_is_registered=False, origin="admin",
            opened_by_admin_id=admin.id, opened_at=_NOW,
            description="ep", created_at=_NOW, updated_at=_NOW,
        )
        db.add(accident)
        db.flush()
        next_call_number = int(
            db.execute(sa.text("SELECT COALESCE(MAX(call_number), 0) + 1 FROM accident_call_logs")).scalar_one()
        )
        log = AccidentCallLog(
            call_number=next_call_number, accident_id=accident.id, project_id=proj.id,
            triggered_by_admin_id=admin.id, to_phone="+5521988887777", from_phone="+15555550000",
            call_status="queued", message_twiml="<Response/>",
            created_at=_NOW, updated_at=_NOW,
        )
        db.add(log)
        db.flush()
        # Persist three notifications in a non-monotonic insertion order.
        for delta, event in [(20, "completed"), (0, "requested"), (10, "initiated")]:
            metadata = _build_call_notification_metadata(
                log=log, accident=accident, project=proj,
                triggered_by_name="Adm EP", triggered_by_chave="PEEA",
                triggered_by_role="admin", status_event=event,
                occurred_at=_NOW + timedelta(seconds=delta),
            )
            record_call_notification(db, log=log, metadata=metadata, project_timezone_name=proj.timezone_name)
        db.commit()
        accident_id = accident.id

    client = _logged_in_admin_client()
    resp = client.get(f"/api/admin/accidents/{accident_id}/notifications")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 3
    # Ordered by occurred_at ascending.
    events_in_order = [r["event_type"] for r in rows]
    assert events_in_order == ["requested", "initiated", "completed"]
    for r in rows:
        assert isinstance(r["id"], int)
        assert isinstance(r["message_pt"], str) and r["message_pt"]


# ---------------------------------------------------------------------------
# Cascade
# ---------------------------------------------------------------------------


def test_deleting_accident_cascades_call_notifications(tmp_path: Path):
    """ORM-level cascade deletes notification rows when their accident is removed."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin, accident_number=300)
    log = _make_call_log(db, accident, proj, admin, call_number=300)
    db.commit()

    metadata = _build_call_notification_metadata(
        log=log, accident=accident, project=proj,
        triggered_by_name="Adm Pers", triggered_by_chave="ADP1",
        triggered_by_role="admin", status_event="requested",
        occurred_at=_NOW,
    )
    record_call_notification(db, log=log, metadata=metadata, project_timezone_name=proj.timezone_name)
    db.commit()

    # Sanity: row exists.
    assert db.execute(sa.select(sa.func.count(AccidentCallNotification.id))).scalar_one() == 1

    # Delete the accident via ORM (the path the admin DELETE endpoint takes).
    db.delete(accident)
    db.commit()

    # Notification row gone via cascade.
    remaining = db.execute(sa.select(sa.func.count(AccidentCallNotification.id))).scalar_one()
    assert remaining == 0, "AccidentCallNotification not cascaded when parent Accident was deleted"
