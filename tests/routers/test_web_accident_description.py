"""Tests for Phase 5 / prompt 5.1 — Descrição Detalhada step in the App wizard.

These tests pin the backend contract the App wizard relies on: when the user
walks through the new "Descrição Detalhada" step (textarea, maxlength=500) and
confirms, the POST /api/web/check/accident/open call must persist the
description into Accident.description verbatim (including UTF-8 accents,
emojis and the upper limit boundary). They also lock in the 500-character
validation enforced by Pydantic at the schema level.
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
    UserProjectMembership,
)
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

OPEN_URL = "/api/web/check/accident/open"
STATE_URL = "/api/web/check/accident/state"
WEB_LOGIN_URL = "/api/web/auth/login"

_PROJ_NAME = "DESC_PROJ"
_USER_CHAVE = "DSC1"
_PASSWORD = "DescTest!1"


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJ_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="Desc Addr",
            zip_code="030303",
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
            nome="Desc User",
            projeto=_PROJ_NAME,
            checkin=True,
            local="Desc Site",
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


def _close_all_accidents(db) -> None:
    now = datetime.now(tz=timezone.utc)
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(
        sa.update(Accident).where(Accident.closed_at.is_(None)).values(closed_at=now, updated_at=now)
    )
    db.commit()


def _login_client() -> TestClient:
    with SessionLocal() as db:
        proj = _ensure_project(db)
        user = _ensure_user(db)
        _ensure_membership(db, user, proj)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": _USER_CHAVE, "senha": _PASSWORD})
    assert resp.status_code == 200, f"Web login failed: {resp.status_code} {resp.text}"
    return client


def _open_with_description(client: TestClient, description: str, project_id: int) -> int:
    """POST /accident/open with the given description; returns accident_id."""
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={
                "chave": _USER_CHAVE,
                "project_id": project_id,
                "location_id": None,
                "custom_location_name": "Desc Site",
                "zone": "safety",
                "status": "ok",
                "description": description,
            },
        )
    assert resp.status_code == 200, f"open failed: {resp.status_code} {resp.text}"
    state = client.get(STATE_URL, params={"chave": _USER_CHAVE}).json()
    return state["accident_id"]


def test_open_persists_description_with_accents_and_emoji():
    """A description with áéíóú and 🚨 must round-trip verbatim through the DB."""
    description = "Descrição com acentuação áéíóú, ç e emoji 🚨 — relatório completo."

    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _login_client()
    accident_id = _open_with_description(client, description, proj_id)

    # Verify directly in the DB so we are not just round-tripping the same code path.
    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        assert accident is not None
        assert accident.description == description, (
            f"description was not persisted verbatim. Stored: {accident.description!r}"
        )

    # And via the state endpoint — the value that powers the front "Descrição" badge.
    state = client.get(STATE_URL, params={"chave": _USER_CHAVE}).json()
    assert state["description"] == description


def test_open_persists_empty_description_as_empty_string():
    """Item 4.6 allows the user to skip the textarea — the resulting Accident.description must be ''."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _login_client()
    accident_id = _open_with_description(client, "", proj_id)

    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        assert accident is not None
        # open_accident calls description.strip() — empty in, empty out.
        assert accident.description == "", (
            f"expected empty description, got {accident.description!r}"
        )


def test_open_accepts_description_at_500_char_upper_bound():
    """The schema's max_length=500 must accept exactly 500 chars (boundary check)."""
    description = "a" * 500
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _login_client()
    accident_id = _open_with_description(client, description, proj_id)

    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        assert accident is not None
        assert accident.description == description
        assert len(accident.description) == 500


def test_open_rejects_description_above_500_chars():
    """A description longer than the schema limit must be rejected with 422."""
    description = "x" * 501

    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _login_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={
                "chave": _USER_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "Desc Site",
                "zone": "safety",
                "status": "ok",
                "description": description,
            },
        )
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"


def test_state_active_accidents_item_carries_description():
    """The new active_accidents list (phase 1.2) also carries description per entry."""
    description = "Conteúdo de teste — fase 5."
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _login_client()
    _open_with_description(client, description, proj_id)

    state = client.get(STATE_URL, params={"chave": _USER_CHAVE}).json()
    items = state["active_accidents"]
    assert len(items) == 1
    assert items[0]["description"] == description
