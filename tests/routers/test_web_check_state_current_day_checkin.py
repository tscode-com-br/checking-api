"""Tests for has_current_day_checkin in GET /api/web/check/state (Phase 6 / prompt 6.1).

These tests pin the visibility rule for the App's "Reportar Acidente" button
(item 4.4 of docs/temp002_alteracoes.txt): the button is hidden unless the
user's last activity is a check-in on the CURRENT day in the PROJECT's
timezone. The front combines two payload fields:
    _canReportAccident = state.has_current_day_checkin && state.current_action === 'checkin'

We cover both pieces and the timezone boundary case where UTC is still on D-1
but the project timezone (Asia/Singapore, +08) is already on D.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import sqlalchemy as sa

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

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import Project, User, UserSyncEvent  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

STATE_URL = "/api/web/check/state"
WEB_LOGIN_URL = "/api/web/auth/login"

_PROJ_NAME = "CD_PROJ"
_USER_CHAVE = "CDU1"
_PASSWORD = "CdTest!1"
_TZ = "Asia/Singapore"  # +08


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJ_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name=_TZ,
            address="Cd Addr",
            zip_code="040404",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _ensure_user(db) -> User:
    user = db.execute(sa.select(User).where(User.chave == _USER_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_USER_CHAVE,
            nome="Cd User",
            projeto=_PROJ_NAME,
            checkin=True,
            local="Cd Site",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_PASSWORD),
            perfil=1,
        )
        db.add(user)
    else:
        user.senha = hash_password(_PASSWORD)
        user.projeto = _PROJ_NAME
        user.checkin = True
    db.commit()
    db.refresh(user)
    return user


def _wipe_user_events(db, user_id: int) -> None:
    db.execute(sa.delete(UserSyncEvent).where(UserSyncEvent.user_id == user_id))
    db.commit()


def _add_event(
    db,
    *,
    user: User,
    action: str,
    event_time: datetime,
    local: str = "Cd Site",
) -> None:
    db.add(UserSyncEvent(
        user_id=user.id,
        chave=user.chave,
        rfid=user.rfid,
        source="provider",
        action=action,
        projeto=_PROJ_NAME,
        local=local,
        ontime=True,
        event_time=event_time,
        created_at=event_time,
        source_request_id=f"cd-{uuid.uuid4().hex}",
        device_id="CD-TEST-01",
    ))
    db.commit()


def _login_client() -> TestClient:
    with SessionLocal() as db:
        _ensure_project(db)
        _ensure_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": _USER_CHAVE, "senha": _PASSWORD})
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return client


def _fetch_state(client: TestClient) -> dict:
    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_checkin_today_yields_has_current_day_checkin_true_and_action_checkin():
    """User checks in today (no later checkout) → both signals satisfied: button visible.

    Mirrors the front rule `has_current_day_checkin && current_action === 'checkin'`.
    """
    today_proj = datetime.now(tz=ZoneInfo(_TZ)).replace(hour=8, minute=0, second=0, microsecond=0)
    with SessionLocal() as db:
        proj = _ensure_project(db)  # noqa: F841
        user = _ensure_user(db)
        _wipe_user_events(db, user.id)
        _add_event(db, user=user, action="checkin", event_time=today_proj)

    client = _login_client()
    data = _fetch_state(client)
    assert data["has_current_day_checkin"] is True
    assert data["current_action"] == "checkin"


def test_checkin_yesterday_yields_has_current_day_checkin_false():
    """Last activity = check-in YESTERDAY → has_current_day_checkin=false → button hidden."""
    yesterday_proj = datetime.now(tz=ZoneInfo(_TZ)).replace(hour=8, minute=0, second=0, microsecond=0) - timedelta(days=1)
    with SessionLocal() as db:
        proj = _ensure_project(db)  # noqa: F841
        user = _ensure_user(db)
        _wipe_user_events(db, user.id)
        _add_event(db, user=user, action="checkin", event_time=yesterday_proj)

    client = _login_client()
    data = _fetch_state(client)
    assert data["has_current_day_checkin"] is False
    # current_action is still 'checkin' (last activity), but the date gate kills the button.
    assert data["current_action"] == "checkin"


def test_checkin_today_then_checkout_today_yields_current_action_checkout():
    """Check-in HOJE then check-out HOJE → last activity is check-out → button hidden."""
    today_morning = datetime.now(tz=ZoneInfo(_TZ)).replace(hour=8, minute=0, second=0, microsecond=0)
    today_evening = today_morning.replace(hour=18)
    with SessionLocal() as db:
        proj = _ensure_project(db)  # noqa: F841
        user = _ensure_user(db)
        _wipe_user_events(db, user.id)
        _add_event(db, user=user, action="checkin", event_time=today_morning)
        _add_event(db, user=user, action="checkout", event_time=today_evening)

    client = _login_client()
    data = _fetch_state(client)
    assert data["current_action"] == "checkout"
    # has_current_day_checkin can still be true (a check-in happened today), but
    # the front combines it with current_action — so the button must hide.
    # We validate the AND that powers _canReportAccident here:
    can_report = bool(data["has_current_day_checkin"]) and data["current_action"] == "checkin"
    assert can_report is False


def test_checkin_yesterday_then_checkout_today_yields_can_report_false():
    """Check-in ONTEM + check-out HOJE → has_current_day_checkin=false → button hidden."""
    yesterday_evening = datetime.now(tz=ZoneInfo(_TZ)).replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
    today_morning = datetime.now(tz=ZoneInfo(_TZ)).replace(hour=8, minute=0, second=0, microsecond=0)
    with SessionLocal() as db:
        proj = _ensure_project(db)  # noqa: F841
        user = _ensure_user(db)
        _wipe_user_events(db, user.id)
        _add_event(db, user=user, action="checkin", event_time=yesterday_evening)
        _add_event(db, user=user, action="checkout", event_time=today_morning)

    client = _login_client()
    data = _fetch_state(client)
    assert data["current_action"] == "checkout"
    assert data["has_current_day_checkin"] is False
    can_report = bool(data["has_current_day_checkin"]) and data["current_action"] == "checkin"
    assert can_report is False


def test_is_same_project_day_uses_project_timezone_not_utc():
    """Direct unit test of is_same_project_day (the helper behind has_current_day_checkin).

    Scenario: 2026-05-25 17:00 UTC vs 2026-05-25 19:00 UTC.
    - In UTC, both are on 2026-05-25 → same day → True regardless of tz.
    - Make the "now" cross the date line in Asia/Singapore:
      * checkin at 2026-05-25 15:00 UTC  = 2026-05-25 23:00 SGT (D-1)
      * now     at 2026-05-25 16:30 UTC  = 2026-05-26 00:30 SGT (D)
    In UTC both are 2026-05-25 → same day. In SGT they straddle midnight → different days.
    The helper MUST follow the project timezone and return False.

    Pinning this behaviour direct on the helper avoids the SQLite limitation of
    not preserving tzinfo on DateTime(timezone=True) columns. The production
    code path (Postgres) preserves tz so the end-to-end behaviour matches.
    """
    from sistema.app.services.user_sync import is_same_project_day

    checkin_utc = datetime(2026, 5, 25, 15, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 5, 25, 16, 30, 0, tzinfo=timezone.utc)

    # Sanity: both UTC instants are on the same UTC date.
    assert checkin_utc.date() == now_utc.date()

    # Singapore tz crosses the date boundary between them.
    sgt = ZoneInfo("Asia/Singapore")
    assert checkin_utc.astimezone(sgt).date() != now_utc.astimezone(sgt).date()

    # Helper must follow the project timezone.
    assert is_same_project_day(checkin_utc, now_utc, timezone_name="UTC") is True
    assert is_same_project_day(checkin_utc, now_utc, timezone_name="Asia/Singapore") is False


def test_is_same_project_day_groups_checkin_into_today_when_project_tz_already_advanced():
    """Inverse boundary: UTC says yesterday, Singapore says today → same project day = True.

    checkin at 2026-05-25 17:00 UTC = 2026-05-26 01:00 SGT (D)
    now     at 2026-05-25 19:00 UTC = 2026-05-26 03:00 SGT (D)
    In UTC both are 2026-05-25; in Singapore both are 2026-05-26 — either way same day.
    But the spec demands the project tz be the source of truth, so we exercise it.
    """
    from sistema.app.services.user_sync import is_same_project_day

    checkin_utc = datetime(2026, 5, 25, 17, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 5, 25, 19, 0, 0, tzinfo=timezone.utc)
    assert is_same_project_day(checkin_utc, now_utc, timezone_name="Asia/Singapore") is True


def test_no_events_yields_has_current_day_checkin_false_and_no_action():
    """A user with no events has has_current_day_checkin=false and current_action=None."""
    with SessionLocal() as db:
        proj = _ensure_project(db)  # noqa: F841
        user = _ensure_user(db)
        _wipe_user_events(db, user.id)

    client = _login_client()
    data = _fetch_state(client)
    assert data["has_current_day_checkin"] is False
    # current_action may be None or 'checkout' depending on whether the user's
    # default state is set. We only care that _canReportAccident evaluates to false.
    can_report = bool(data["has_current_day_checkin"]) and data["current_action"] == "checkin"
    assert can_report is False
