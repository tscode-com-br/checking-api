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
from sistema.app.models import Project, User, UserProjectMembership  # noqa: E402
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


# ---------------------------------------------------------------------------
# Modificação 1 — Regras #1–#4 sobre o botão Transporte no app (multi-projeto)
# ---------------------------------------------------------------------------

_WEB_EXTRA_PROJECT_ON = "WSPMULTON"
_WEB_EXTRA_PROJECT_OFF = "WSPMULTOFF"


def _ensure_project(db: sa.orm.Session, name: str, *, transport_enabled: bool) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="",
            zip_code="",
            forms_enabled=True,
            transport_enabled=transport_enabled,
            emergency_phone="",
        )
        db.add(proj)
    else:
        proj.transport_enabled = transport_enabled
    db.flush()
    db.refresh(proj)
    return proj


def _set_user_memberships(db: sa.orm.Session, user: User, project_ids: list[int]) -> None:
    db.execute(sa.delete(UserProjectMembership).where(UserProjectMembership.user_id == user.id))
    now = datetime.now(tz=timezone.utc)
    for project_id in project_ids:
        db.add(
            UserProjectMembership(
                user_id=user.id, project_id=project_id, created_at=now, updated_at=now
            )
        )


@pytest.fixture()
def web_user_with_multi_projects(client):
    """Cria 3 projetos (o principal + on + off) e vincula o usuário aos três.

    O fixture devolve uma função `apply(states)` que ajusta os 3 toggles e
    devolve os cookies de sessão. Os memberships são limpos no teardown.
    """
    with SessionLocal() as db:
        user, _ = _ensure_web_user_and_project(db)
        _ensure_project(db, _WEB_EXTRA_PROJECT_ON, transport_enabled=True)
        _ensure_project(db, _WEB_EXTRA_PROJECT_OFF, transport_enabled=False)
        db.commit()

    resp = client.post(LOGIN_URL, json={"chave": _WEB_CHAVE, "senha": _WEB_SENHA})
    assert resp.status_code == 200, resp.text
    cookies = resp.cookies

    def apply(states: dict[str, bool], project_names: list[str]) -> None:
        with SessionLocal() as db:
            project_ids: list[int] = []
            for project_name in project_names:
                proj = _ensure_project(
                    db, project_name, transport_enabled=states.get(project_name, True)
                )
                project_ids.append(proj.id)
            user = db.execute(sa.select(User).where(User.chave == _WEB_CHAVE)).scalar_one()
            _set_user_memberships(db, user, project_ids)
            db.commit()

    yield apply, cookies

    # Teardown: zera memberships e restaura defaults dos projetos auxiliares.
    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == _WEB_CHAVE)).scalar_one_or_none()
        if user is not None:
            db.execute(sa.delete(UserProjectMembership).where(UserProjectMembership.user_id == user.id))
        for name in (_WEB_EXTRA_PROJECT_ON, _WEB_EXTRA_PROJECT_OFF):
            proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
            if proj is not None:
                proj.transport_enabled = True
        db.commit()


def test_state_rule1_single_project_off_hides_button(client, web_user_with_multi_projects):
    """Regra #1: usuário em um único projeto com transporte OFF → False."""
    apply, cookies = web_user_with_multi_projects
    apply(
        {_WEB_PROJECT: False},
        project_names=[_WEB_PROJECT],
    )
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=cookies)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is False


def test_state_rule2_multi_project_all_off_hides_button(client, web_user_with_multi_projects):
    """Regra #2: multi-projeto, todos OFF → False."""
    apply, cookies = web_user_with_multi_projects
    apply(
        {_WEB_PROJECT: False, _WEB_EXTRA_PROJECT_OFF: False},
        project_names=[_WEB_PROJECT, _WEB_EXTRA_PROJECT_OFF],
    )
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=cookies)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is False


def test_state_rule3_multi_project_mixed_shows_button(client, web_user_with_multi_projects):
    """Regra #3: multi-projeto, mix ON/OFF → True (basta um ON)."""
    apply, cookies = web_user_with_multi_projects
    apply(
        {
            _WEB_PROJECT: False,
            _WEB_EXTRA_PROJECT_ON: True,
            _WEB_EXTRA_PROJECT_OFF: False,
        },
        project_names=[_WEB_PROJECT, _WEB_EXTRA_PROJECT_ON, _WEB_EXTRA_PROJECT_OFF],
    )
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=cookies)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is True


def test_state_rule4_multi_project_all_on_shows_button(client, web_user_with_multi_projects):
    """Regra #4: multi-projeto, todos ON → True."""
    apply, cookies = web_user_with_multi_projects
    apply(
        {_WEB_PROJECT: True, _WEB_EXTRA_PROJECT_ON: True},
        project_names=[_WEB_PROJECT, _WEB_EXTRA_PROJECT_ON],
    )
    resp = client.get(f"{STATE_URL}?chave={_WEB_CHAVE}", cookies=cookies)
    assert resp.status_code == 200, resp.text
    assert resp.json()["transport_enabled"] is True
