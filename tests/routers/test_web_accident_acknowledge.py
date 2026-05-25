"""Tests for /api/web/check/accident/acknowledge and the per-user awareness_status returned by /accident/state.

These tests back the Phase 1 / item 1.1 fix in docs/temp002b.md: the
accidentAckDialog in the App (Checking Web) must show whenever an active
accident has awareness_status='waiting' for the logged-in user, and it must
disappear once the user has acknowledged. The two-user fixture proves that
ack is per-user and does not leak across users.
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
ACK_URL = "/api/web/check/accident/acknowledge"
WEB_LOGIN_URL = "/api/web/auth/login"

_PROJ_NAME = "ACK_PROJ"
_USER_A_CHAVE = "ACKA"
_USER_B_CHAVE = "ACKB"
_PASSWORD = "AckTest!1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJ_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="Ack Addr",
            zip_code="000111",
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
            local="Site Ack",
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
    """Return a persisted AdminUser usable as opened_by_admin_id."""
    chave = "AKAD"
    admin_user = db.execute(sa.select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if admin_user is None:
        now = datetime.now(tz=timezone.utc)
        admin_user = AdminUser(
            chave=chave,
            nome_completo="Ack Admin",
            password_hash=hash_password(_PASSWORD),
            created_at=now,
            updated_at=now,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    return admin_user


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


def _setup_two_users_and_open_accident() -> tuple[int, int, int]:
    """Set up project + 2 members + 1 active accident.

    Returns (proj_id, user_a_id, user_b_id).
    """
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user_a = _ensure_user(db, _USER_A_CHAVE, "Ack User A")
        user_b = _ensure_user(db, _USER_B_CHAVE, "Ack User B")
        _ensure_membership(db, user_a, proj)
        _ensure_membership(db, user_b, proj)
        admin_user = _ensure_admin_user(db)
        proj_id = proj.id
        user_a_id = user_a.id
        user_b_id = user_b.id
        admin_id = admin_user.id

    with (
        SessionLocal() as db,
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        open_accident(
            db,
            origin="admin",
            project_id=proj_id,
            custom_location_name="Ack Test Site",
            opened_by_admin_id=admin_id,
        )

    return proj_id, user_a_id, user_b_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_state_returns_waiting_for_member_before_acknowledge():
    """Member of the project sees is_active=true and awareness_status='waiting' before clicking Ciente."""
    _setup_two_users_and_open_accident()

    client_a = _login_client(_USER_A_CHAVE)
    resp = client_a.get(STATE_URL, params={"chave": _USER_A_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["accident_id"] is not None
    assert data["awareness_status"] == "waiting", f"expected 'waiting', got {data!r}"


def test_acknowledge_transitions_state_to_acknowledged_for_caller_only():
    """POST /accident/acknowledge updates only the caller's AccidentUserReport.awareness_status."""
    _setup_two_users_and_open_accident()

    client_a = _login_client(_USER_A_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        ack = client_a.post(ACK_URL, json={"chave": _USER_A_CHAVE})
    assert ack.status_code == 200, ack.text
    body = ack.json()
    assert body["ok"] is True
    assert isinstance(body.get("accident_id"), int) and body["accident_id"] > 0

    # User A: awareness_status now acknowledged
    resp_a = client_a.get(STATE_URL, params={"chave": _USER_A_CHAVE})
    assert resp_a.status_code == 200, resp_a.text
    data_a = resp_a.json()
    assert data_a["is_active"] is True
    assert data_a["awareness_status"] == "acknowledged"

    # User B: still waiting — ack is per-user, must not bleed across
    client_b = _login_client(_USER_B_CHAVE)
    resp_b = client_b.get(STATE_URL, params={"chave": _USER_B_CHAVE})
    assert resp_b.status_code == 200, resp_b.text
    data_b = resp_b.json()
    assert data_b["is_active"] is True
    assert data_b["awareness_status"] == "waiting"


def test_acknowledge_is_idempotent():
    """Repeated POST acknowledge keeps awareness_status='acknowledged' and returns 200 every time."""
    _setup_two_users_and_open_accident()

    client_a = _login_client(_USER_A_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        ack1 = client_a.post(ACK_URL, json={"chave": _USER_A_CHAVE})
        ack2 = client_a.post(ACK_URL, json={"chave": _USER_A_CHAVE})
    assert ack1.status_code == 200
    assert ack2.status_code == 200

    resp = client_a.get(STATE_URL, params={"chave": _USER_A_CHAVE})
    assert resp.status_code == 200
    assert resp.json()["awareness_status"] == "acknowledged"


def test_acknowledge_without_active_accident_returns_409():
    """If there is no active accident, acknowledge returns 409 (not 500)."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user_a = _ensure_user(db, _USER_A_CHAVE, "Ack User A")
        _ensure_membership(db, user_a, proj)

    client_a = _login_client(_USER_A_CHAVE)
    resp = client_a.post(ACK_URL, json={"chave": _USER_A_CHAVE})
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Multi-accident scenario: user is a member of 2 projects, admin opens an
# accident on each. The web state must expose both via `active_accidents`,
# and acknowledge must target one at a time via the `accident_id` payload.
# ---------------------------------------------------------------------------

_PROJ_X = "ACK_PROJ_X"
_PROJ_Y = "ACK_PROJ_Y"


def _ensure_named_project(db, name: str) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="Multi Addr",
            zip_code="000222",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _setup_user_with_two_active_accidents() -> tuple[int, int, int]:
    """Set up a user with membership in 2 projects and an active accident on each.

    Returns (user_a_id, accident_x_id, accident_y_id).
    """
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj_x = _ensure_named_project(db, _PROJ_X)
        proj_y = _ensure_named_project(db, _PROJ_Y)
        user_a = _ensure_user(db, _USER_A_CHAVE, "Multi Ack User")
        _ensure_membership(db, user_a, proj_x)
        _ensure_membership(db, user_a, proj_y)
        admin_user = _ensure_admin_user(db)
        proj_x_id = proj_x.id
        proj_y_id = proj_y.id
        user_a_id = user_a.id
        admin_id = admin_user.id

    accidents_created: list[int] = []
    with (
        SessionLocal() as db,
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        acc_x = open_accident(
            db,
            origin="admin",
            project_id=proj_x_id,
            custom_location_name="Multi Site X",
            opened_by_admin_id=admin_id,
        )
        acc_y = open_accident(
            db,
            origin="admin",
            project_id=proj_y_id,
            custom_location_name="Multi Site Y",
            opened_by_admin_id=admin_id,
        )
        accidents_created.extend([acc_x.id, acc_y.id])

    return user_a_id, accidents_created[0], accidents_created[1]


def test_state_returns_active_accidents_for_each_project():
    """User in 2 projects with 2 active accidents → active_accidents has 2 entries, each with awareness_status='waiting'."""
    _, acc_x_id, acc_y_id = _setup_user_with_two_active_accidents()

    client_a = _login_client(_USER_A_CHAVE)
    resp = client_a.get(STATE_URL, params={"chave": _USER_A_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert isinstance(data.get("active_accidents"), list), data
    items = data["active_accidents"]
    assert len(items) == 2, f"expected 2 active items, got {items!r}"
    ids = sorted(item["accident_id"] for item in items)
    assert ids == sorted([acc_x_id, acc_y_id])
    for item in items:
        assert item["awareness_status"] == "waiting"
        assert item["project_name"] in {_PROJ_X, _PROJ_Y}
    # Legacy scalar field still mirrors the first item for backwards compat
    assert data["accident_id"] == items[0]["accident_id"]
    assert data["awareness_status"] == "waiting"


def test_acknowledge_with_explicit_accident_id_targets_only_that_one():
    """POST acknowledge with accident_id=X only flips X. The other accident stays 'waiting'."""
    _, acc_x_id, acc_y_id = _setup_user_with_two_active_accidents()

    client_a = _login_client(_USER_A_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        ack = client_a.post(
            ACK_URL,
            json={"chave": _USER_A_CHAVE, "accident_id": acc_x_id},
        )
    assert ack.status_code == 200, ack.text
    assert ack.json()["accident_id"] == acc_x_id

    state = client_a.get(STATE_URL, params={"chave": _USER_A_CHAVE}).json()
    items_by_id = {item["accident_id"]: item for item in state["active_accidents"]}
    assert items_by_id[acc_x_id]["awareness_status"] == "acknowledged"
    assert items_by_id[acc_y_id]["awareness_status"] == "waiting"


def test_acknowledge_rejects_unknown_accident_id():
    """POST acknowledge with an accident_id that is not currently active → 404."""
    _setup_user_with_two_active_accidents()

    client_a = _login_client(_USER_A_CHAVE)
    resp = client_a.post(
        ACK_URL,
        json={"chave": _USER_A_CHAVE, "accident_id": 9_999_999},
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


def test_acknowledge_without_accident_id_uses_legacy_fallback():
    """Omitting accident_id keeps the legacy behaviour: ack the first matching active accident."""
    _, acc_x_id, acc_y_id = _setup_user_with_two_active_accidents()

    client_a = _login_client(_USER_A_CHAVE)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        ack = client_a.post(ACK_URL, json={"chave": _USER_A_CHAVE})
    assert ack.status_code == 200, ack.text
    # Whichever ordering list_active_accidents returns (sorted by accident_number),
    # the returned accident_id must be one of the two known active ids.
    assert ack.json()["accident_id"] in {acc_x_id, acc_y_id}
