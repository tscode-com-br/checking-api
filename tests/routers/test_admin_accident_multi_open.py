"""Tests for Phase 4 / prompt 4.1 — admin can open accidents simultaneously.

These tests pin the backend contract that supports the front "Confirmar" button
reset fix: opening a second accident in another project while one is already
active, and reopening an accident in the same project after closing the previous
one, must both succeed with HTTP 200 (no 409). The 409 only fires when the
target project still has an active accident — the partial unique index is
per-project, not global.
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
    Project,
    User,
)
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

OPEN_URL = "/api/admin/accidents/open"
ACTIVE_URL = "/api/admin/accidents/active"
ADMIN_LOGIN_URL = "/api/admin/auth/login"

_ADMIN_CHAVE = "MULT"
_ADMIN_SENHA = "MultiAdmin!1"
_PROJ_A = "MULTI_A"
_PROJ_B = "MULTI_B"


def _ensure_admin_user(db) -> User:
    user = db.execute(sa.select(User).where(User.chave == _ADMIN_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_ADMIN_CHAVE,
            nome="Multi Admin",
            projeto=_PROJ_A,
            checkin=False,
            local="Office",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_ADMIN_SENHA),
            perfil=19,  # admin panel access
        )
        db.add(user)
    else:
        user.senha = hash_password(_ADMIN_SENHA)
        user.perfil = 19
    db.commit()
    db.refresh(user)
    return user


def _ensure_project(db, name: str) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="Addr",
            zip_code="111000",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _close_all_accidents(db) -> None:
    now = datetime.now(tz=timezone.utc)
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(
        sa.update(Accident).where(Accident.closed_at.is_(None)).values(closed_at=now, updated_at=now)
    )
    db.commit()


def _logged_in_client() -> TestClient:
    with SessionLocal() as db:
        _ensure_project(db, _PROJ_A)
        _ensure_project(db, _PROJ_B)
        _ensure_admin_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _ADMIN_CHAVE, "senha": _ADMIN_SENHA})
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    return client


def _open_via_api(client: TestClient, project_id: int, location_name: str = "Site") -> int:
    """POST /accidents/open and return the accident_id. Brokers patched out."""
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={"project_id": project_id, "custom_location_name": location_name},
        )
    assert resp.status_code == 200, f"open failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["is_active"] is True
    # Backwards-compat: response carries the just-created accident at the root.
    return data["accident"]["id"]


def _close_via_api(client: TestClient, accident_id: int) -> None:
    """POST /accidents/{id}/close. Brokers and archive build patched out."""
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.build_and_attach_archive_for_accident"),
    ):
        resp = client.post(f"/api/admin/accidents/{accident_id}/close")
    assert resp.status_code == 200, f"close failed: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reopen_in_same_project_after_close_returns_200():
    """Admin closes accident in project A, then opens another in project A → 200, both rows exist."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj_a = _ensure_project(db, _PROJ_A)
        proj_a_id = proj_a.id

    client = _logged_in_client()

    first_id = _open_via_api(client, proj_a_id, location_name="First site")
    _close_via_api(client, first_id)
    second_id = _open_via_api(client, proj_a_id, location_name="Second site")

    assert second_id != first_id

    # Verify both rows exist in the database (one closed, one active).
    with SessionLocal() as db:
        rows = db.execute(
            sa.select(Accident).where(Accident.project_id == proj_a_id).order_by(Accident.id)
        ).scalars().all()
        assert len(rows) >= 2
        first = next(r for r in rows if r.id == first_id)
        second = next(r for r in rows if r.id == second_id)
        assert first.closed_at is not None
        assert second.closed_at is None


def test_open_simultaneous_accidents_on_two_projects():
    """Admin opens accident in project A, then in project B without closing A → both active."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj_a = _ensure_project(db, _PROJ_A)
        proj_b = _ensure_project(db, _PROJ_B)
        proj_a_id = proj_a.id
        proj_b_id = proj_b.id

    client = _logged_in_client()

    a_id = _open_via_api(client, proj_a_id, location_name="A site")
    b_id = _open_via_api(client, proj_b_id, location_name="B site")

    # GET /accidents/active must report 2 active accidents under active_accidents.
    resp = client.get(ACTIVE_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    active_ids = sorted(item["accident"]["id"] for item in data["active_accidents"])
    assert active_ids == sorted([a_id, b_id])


def test_open_in_same_project_with_active_returns_409():
    """Sanity check: opening a second accident in the SAME project while one is active still returns 409.

    The per-project partial unique index is the safety net the front button-reset
    fix relies on — opening anywhere else is allowed, opening in the same project
    is not.
    """
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj_a = _ensure_project(db, _PROJ_A)
        proj_a_id = proj_a.id

    client = _logged_in_client()
    _open_via_api(client, proj_a_id, location_name="A site")

    # Second attempt in the same project must hit 409.
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={"project_id": proj_a_id, "custom_location_name": "duplicate site"},
        )
    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
