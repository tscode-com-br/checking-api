"""Tests for the project_id field on /api/web/check/accident/state (Phase 3 / prompt 3.1).

The front App relies on `project_id` (and `project_name`) to decide whether the
authenticated user is checked-in at the same project as the accident. This pins
that the field is present both on the root WebAccidentStateResponse (compat
scalar) and on each entry of active_accidents.
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
WEB_LOGIN_URL = "/api/web/auth/login"

_PROJ_NAME = "PI_PROJ"
_USER_CHAVE = "PIU1"
_PASSWORD = "PiTest!1"


def _ensure_project(db, name: str = _PROJ_NAME) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="PI Addr",
            zip_code="020202",
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
            local="PI Site",
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


def _ensure_admin(db) -> AdminUser:
    chave = "PIAD"
    admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if admin is None:
        now = datetime.now(tz=timezone.utc)
        admin = AdminUser(
            chave=chave,
            nome_completo="PI Admin",
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


def test_state_root_includes_project_id():
    """Root-level WebAccidentStateResponse.project_id matches the active accident's project."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_user(db, _USER_CHAVE, "PI User")
        _ensure_membership(db, user, proj)
        admin = _ensure_admin(db)
        proj_id = proj.id
        admin_id = admin.id

    with (
        SessionLocal() as db,
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        open_accident(
            db,
            origin="admin",
            project_id=proj_id,
            custom_location_name="PI Site",
            opened_by_admin_id=admin_id,
        )

    client = _login_client(_USER_CHAVE)
    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["project_id"] == proj_id, f"expected project_id={proj_id}, got {data!r}"
    assert data["project_name"] == _PROJ_NAME


def test_state_active_accidents_items_include_project_id():
    """Each active_accidents item carries its own project_id matching project_name."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_user(db, _USER_CHAVE, "PI User")
        _ensure_membership(db, user, proj)
        admin = _ensure_admin(db)
        proj_id = proj.id
        admin_id = admin.id

    with (
        SessionLocal() as db,
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        open_accident(
            db,
            origin="admin",
            project_id=proj_id,
            custom_location_name="PI Site",
            opened_by_admin_id=admin_id,
        )

    client = _login_client(_USER_CHAVE)
    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    items = resp.json()["active_accidents"]
    assert len(items) == 1
    item = items[0]
    assert item["project_id"] == proj_id
    assert item["project_name"] == _PROJ_NAME


def test_state_returns_no_project_id_when_no_active_accident():
    """When there's no active accident, project_id remains None."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_user(db, _USER_CHAVE, "PI User")
        _ensure_membership(db, user, proj)

    client = _login_client(_USER_CHAVE)
    resp = client.get(STATE_URL, params={"chave": _USER_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False
    assert data["project_id"] is None
    assert data["active_accidents"] == []
