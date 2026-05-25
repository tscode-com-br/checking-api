"""Tests for the post-report "Situação atual enviada." state (Phase 2 / prompt 2.1).

When an admin opens an accident, `open_accident` seeds an AccidentUserReport for
every project member with zone='waiting', status='waiting' and reported_at=None.
The front App treats a user as "has reported" only when reported_at is not None
— otherwise the inquiry card must stay in the initial Zona de Segurança / Zona
de Acidente state.

These tests pin that contract from the backend side so the front can rely on
`current_user_report.reported_at` as the single source of truth.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

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
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    Project,
    User,
    UserProjectMembership,
)
from sistema.app.services.accident_lifecycle import open_accident  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

STATE_URL = "/api/web/check/accident/state"
REPORT_URL = "/api/web/check/accident/report"
WEB_LOGIN_URL = "/api/web/auth/login"

_PROJ_NAME = "PR_PROJ"
_USER_CHAVE = "PRU1"
_PASSWORD = "PrTest!1"


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJ_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="PR Addr",
            zip_code="010101",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _ensure_user(db, chave: str, name: str) -> User:
    user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=chave,
            nome=name,
            projeto=_PROJ_NAME,
            checkin=True,
            local="PR Site",
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


def _ensure_membership(db, user: User, project: Project) -> None:
    existing = db.execute(
        sa.select(UserProjectMembership).where(
            UserProjectMembership.user_id == user.id,
            UserProjectMembership.project_id == project.id,
        )
    ).scalar_one_or_none()
    if existing is None:
        now = datetime.now(tz=timezone.utc)
        db.add(UserProjectMembership(
            user_id=user.id, project_id=project.id, created_at=now, updated_at=now,
        ))
        db.commit()


def _ensure_admin_user(db) -> AdminUser:
    chave = "PRAD"
    admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if admin is None:
        now = datetime.now(tz=timezone.utc)
        admin = AdminUser(
            chave=chave,
            nome_completo="PR Admin",
            password_hash=hash_password(_PASSWORD),
            created_at=now,
            updated_at=now,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


def _close_all_accidents(db) -> None:
    now = datetime.now(tz=timezone.utc)
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(
        sa.update(Accident).where(Accident.closed_at.is_(None)).values(closed_at=now, updated_at=now)
    )
    db.commit()


def _login_client(chave: str) -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": chave, "senha": _PASSWORD})
    assert resp.status_code == 200, f"Login failed for {chave}: {resp.status_code} {resp.text}"
    return client


def _setup_admin_opened_accident() -> int:
    """Set up a project, one user member, and an accident opened by ADMIN.

    Returns the user_id. Critical: origin=admin → the seeded AccidentUserReport
    for the user has reported_at=None (they have not interacted yet).
    """
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_user(db, _USER_CHAVE, "PR User")
        _ensure_membership(db, user, proj)
        admin = _ensure_admin_user(db)
        proj_id = proj.id
        admin_id = admin.id
        user_id = user.id

    with (
        SessionLocal() as db,
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        open_accident(
            db,
            origin="admin",
            project_id=proj_id,
            custom_location_name="PR Site",
            opened_by_admin_id=admin_id,
        )

    return user_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_state_reports_reported_at_null_when_user_has_not_reported_yet():
    """After admin opens an accident, the seeded report for a member has reported_at=None.

    The web state must surface current_user_report with reported_at=None so the
    front can keep the inquiry card in its initial state (Zona de Segurança /
    Zona de Acidente buttons) — NOT in the "Situação atual enviada." state.
    """
    _setup_admin_opened_accident()

    client = _login_client(_USER_CHAVE)
    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    cur = data.get("current_user_report")
    assert cur is not None, "current_user_report should be present for seeded members"
    # The seed leaves zone/status as 'waiting' which the response maps to None.
    assert cur["zone"] is None, f"expected zone=None pre-report, got {cur!r}"
    assert cur["status"] is None
    # reported_at is the discriminator the front uses for "has reported" state.
    assert cur["reported_at"] is None, (
        "reported_at must be None until the user submits a report; "
        "the front uses this to decide whether to show 'Situação atual enviada.'"
    )


def test_state_reports_reported_at_after_user_submits():
    """After POST /accident/report, current_user_report.reported_at is non-null."""
    _setup_admin_opened_accident()

    client = _login_client(_USER_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        r = client.post(REPORT_URL, json={"chave": _USER_CHAVE, "zone": "safety", "status": "ok"})
    assert r.status_code == 200, r.text

    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    cur = resp.json()["current_user_report"]
    assert cur is not None
    assert cur["zone"] == "safety"
    assert cur["status"] == "ok"
    assert cur["reported_at"] is not None, "reported_at must be populated after the user submits"


def test_state_persists_after_help_report_across_subsequent_state_fetches():
    """Once the user reported, every subsequent GET /accident/state keeps reported_at.

    This pins the behaviour the front relies on: a refresh after the report
    must show the post-report state (the user does NOT need to localStorage
    anything; the backend is the source of truth).
    """
    _setup_admin_opened_accident()

    client = _login_client(_USER_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.queue_help_request_emails"),
    ):
        r = client.post(
            REPORT_URL,
            json={"chave": _USER_CHAVE, "zone": "accident", "status": "help"},
        )
    assert r.status_code == 200, r.text

    # Simulate three subsequent state fetches (e.g. SSE-triggered + polling +
    # page reload). Each must keep current_user_report.reported_at populated.
    for _ in range(3):
        resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
        assert resp.status_code == 200, resp.text
        cur = resp.json()["current_user_report"]
        assert cur is not None
        assert cur["zone"] == "accident"
        assert cur["status"] == "help"
        assert cur["reported_at"] is not None


def test_state_active_accidents_carry_reported_at_per_entry():
    """In the new multi-accident payload, each active_accidents item carries its own current_user_report.reported_at."""
    _setup_admin_opened_accident()

    client = _login_client(_USER_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        r = client.post(REPORT_URL, json={"chave": _USER_CHAVE, "zone": "safety", "status": "ok"})
    assert r.status_code == 200, r.text

    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    items = resp.json()["active_accidents"]
    assert len(items) == 1
    item = items[0]
    assert item["current_user_report"] is not None
    assert item["current_user_report"]["zone"] == "safety"
    assert item["current_user_report"]["reported_at"] is not None
