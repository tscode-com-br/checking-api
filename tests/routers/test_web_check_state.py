"""Tests for Commit F — transport_enabled in GET /api/web/check/state."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

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
from sistema.app.models import Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

STATE_URL = "/api/web/check/state"
LOGIN_URL = "/api/web/auth/login"

_WEB_CHAVE = "WS01"
_WEB_SENHA = "WebState1!"
_WEB_PROJECT = "WSPTEST"


def _ensure_web_user_and_project(db: sa.orm.Session) -> tuple[User, Project]:
    proj = db.execute(sa.select(Project).where(Project.name == _WEB_PROJECT)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_WEB_PROJECT,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="1 State Test Rd",
            zip_code="099000",
            forms_enabled=True,
            transport_enabled=True,
            emergency_phone="",
        )
        db.add(proj)
        db.flush()

    user = db.execute(sa.select(User).where(User.chave == _WEB_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            rfid=None,
            chave=_WEB_CHAVE,
            nome="Web State User",
            projeto=_WEB_PROJECT,
            checkin=False,
            local="Escritório",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_WEB_SENHA),
        )
        db.add(user)
    else:
        user.senha = hash_password(_WEB_SENHA)
        user.projeto = _WEB_PROJECT
    db.commit()
    db.refresh(proj)
    db.refresh(user)
    return user, proj


@pytest.fixture(autouse=True)
def reset_project_transport_enabled():
    """Restore transport_enabled=True before each test."""
    with SessionLocal() as db:
        _ensure_web_user_and_project(db)
        proj = db.execute(sa.select(Project).where(Project.name == _WEB_PROJECT)).scalar_one_or_none()
        if proj is not None:
            proj.transport_enabled = True
            proj.forms_enabled = True
        db.commit()
    yield
    with SessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == _WEB_PROJECT)).scalar_one_or_none()
        if proj is not None:
            proj.transport_enabled = True
            proj.forms_enabled = True
        db.commit()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def web_user_session(client):
    with SessionLocal() as db:
        _ensure_web_user_and_project(db)
    resp = client.post(LOGIN_URL, json={"chave": _WEB_CHAVE, "senha": _WEB_SENHA})
    assert resp.status_code == 200, resp.text
    return resp.cookies


# ---------------------------------------------------------------------------
# transport_enabled field in /api/web/check/state
# ---------------------------------------------------------------------------

def test_web_check_state_includes_transport_enabled_field(client, web_user_session):
    """GET /api/web/check/state deve incluir o campo transport_enabled."""
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=web_user_session)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "transport_enabled" in data
    assert isinstance(data["transport_enabled"], bool)


def test_web_check_state_transport_enabled_true_by_default(client, web_user_session):
    """transport_enabled deve ser True para projetos com valor padrão."""
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=web_user_session)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is True


def test_web_check_state_reflects_disabled_transport(client, web_user_session):
    """transport_enabled deve refletir o valor atual do projeto."""
    with SessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == _WEB_PROJECT)).scalar_one()
        proj.transport_enabled = False
        db.commit()

    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=web_user_session)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is False
