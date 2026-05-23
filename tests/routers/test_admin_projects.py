"""Tests for Commit E — GET/POST/PUT /api/admin/projects with new toggle fields."""
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
from sistema.app.models import CheckEvent, Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

ADMIN_LOGIN_URL = "/api/admin/auth/login"
PROJECTS_URL = "/api/admin/projects"

_ADMIN_CHAVE = "EP01"
_ADMIN_SENHA = "AdminEProj1!"


def _ensure_admin_user(db: sa.orm.Session) -> User:
    user = db.execute(sa.select(User).where(User.chave == _ADMIN_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_ADMIN_CHAVE,
            nome="E Proj Admin",
            projeto="EPBS",
            checkin=False,
            local="Office",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_ADMIN_SENHA),
            perfil=19,
        )
        db.add(user)
    else:
        user.senha = hash_password(_ADMIN_SENHA)
        user.perfil = 19
    db.commit()
    db.refresh(user)
    return user


def _ensure_base_project(db: sa.orm.Session) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == "EPBS")).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name="EPBS",
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="1 Test Rd",
            zip_code="099999",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


@pytest.fixture(autouse=True)
def cleanup_test_projects():
    """Remove projetos de teste antes e depois de cada teste para evitar colisões."""
    _test_project_names = {"EPRJTEST", "EPRJCREATE", "EPRJEXPL"}
    def _delete():
        with SessionLocal() as db:
            for name in _test_project_names:
                proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
                if proj is not None:
                    db.delete(proj)
            db.commit()
    _delete()
    yield
    _delete()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def admin_session(client):
    with SessionLocal() as db:
        _ensure_admin_user(db)
        _ensure_base_project(db)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _ADMIN_CHAVE, "senha": _ADMIN_SENHA})
    assert resp.status_code == 200, resp.text
    return resp.cookies


@pytest.fixture()
def sample_project(client, admin_session):
    """Create a fresh project for each test and return its row dict."""
    resp = client.post(
        PROJECTS_URL,
        cookies=admin_session,
        json={"name": "EPRJTEST", "address": "Rua Teste 1", "zip_code": "01001000"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/admin/projects — campos novos presentes
# ---------------------------------------------------------------------------

def test_get_projects_includes_toggle_fields(client, admin_session):
    resp = client.get(PROJECTS_URL, cookies=admin_session)
    assert resp.status_code == 200
    projects = resp.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1
    for row in projects:
        assert "forms_enabled" in row
        assert "transport_enabled" in row
        assert "emergency_phone" in row
        assert isinstance(row["forms_enabled"], bool)
        assert isinstance(row["transport_enabled"], bool)
        assert isinstance(row["emergency_phone"], str)


# ---------------------------------------------------------------------------
# POST /api/admin/projects — defaults corretos
# ---------------------------------------------------------------------------

def test_create_project_default_toggles(client, admin_session):
    resp = client.post(
        PROJECTS_URL,
        cookies=admin_session,
        json={"name": "EPRJCREATE"},
    )
    assert resp.status_code == 200, resp.text
    row = resp.json()
    assert row["forms_enabled"] is True
    assert row["transport_enabled"] is True
    assert row["emergency_phone"] == ""


def test_create_project_explicit_toggles(client, admin_session):
    resp = client.post(
        PROJECTS_URL,
        cookies=admin_session,
        json={
            "name": "EPRJEXPL",
            "forms_enabled": False,
            "transport_enabled": False,
            "emergency_phone": "+65 9123 4567",
        },
    )
    assert resp.status_code == 200, resp.text
    row = resp.json()
    assert row["forms_enabled"] is False
    assert row["transport_enabled"] is False
    assert row["emergency_phone"] == "+65 9123 4567"


# ---------------------------------------------------------------------------
# PUT /api/admin/projects/{id} — partial update preserva outros campos
# ---------------------------------------------------------------------------

def test_put_project_partial_update_forms_enabled(client, admin_session, sample_project):
    original_address = sample_project["address"]
    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    assert resp.status_code == 200, resp.text
    row = resp.json()
    assert row["forms_enabled"] is False
    assert row["transport_enabled"] is True
    assert row["address"] == original_address


def test_put_project_partial_update_emergency_phone(client, admin_session, sample_project):
    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"emergency_phone": "  +65 6789 0000  "},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["emergency_phone"] == "+65 6789 0000"


def test_put_project_full_update_preserves_new_fields(client, admin_session, sample_project):
    """Full PUT (como o admin2 UI envia) não deve zerar os campos novos."""
    # Primeiro seta forms_enabled=False
    client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    # Depois faz um PUT completo sem mencionar forms_enabled
    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={
            "name": sample_project["name"],
            "address": "Nova Rua 2",
            "zip_code": "02002000",
        },
    )
    assert resp.status_code == 200, resp.text
    row = resp.json()
    assert row["address"] == "Nova Rua 2"
    # forms_enabled continua False — não foi tocado pelo segundo PUT
    assert row["forms_enabled"] is False


# ---------------------------------------------------------------------------
# Commit F — Auditoria e SSE
# ---------------------------------------------------------------------------

def test_put_project_logs_audit_event_on_forms_disable(client, admin_session, sample_project):
    """Transição forms ON → OFF deve gravar CheckEvent com action='proj_forms_off'."""
    # Limpar eventos de auditoria pré-existentes para este projeto
    with SessionLocal() as db:
        db.execute(
            sa.delete(CheckEvent).where(
                CheckEvent.action == "proj_forms_off",
                CheckEvent.project == sample_project["name"],
            )
        )
        db.commit()

    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        audit = db.execute(
            sa.select(CheckEvent).where(
                CheckEvent.action == "proj_forms_off",
                CheckEvent.project == sample_project["name"],
            )
        ).scalar_one_or_none()
    assert audit is not None
    assert audit.project == sample_project["name"]


def test_put_project_no_audit_when_forms_already_off(client, admin_session, sample_project):
    """Transição forms OFF → OFF não deve gerar nova entrada de auditoria."""
    # Desligar primeiro
    client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    # Contar audits após primeira transição
    with SessionLocal() as db:
        count_after_first = db.execute(
            sa.select(sa.func.count()).select_from(CheckEvent).where(
                CheckEvent.action == "proj_forms_off",
                CheckEvent.project == sample_project["name"],
            )
        ).scalar()

    # Segunda chamada OFF → OFF
    client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    with SessionLocal() as db:
        count_after_second = db.execute(
            sa.select(sa.func.count()).select_from(CheckEvent).where(
                CheckEvent.action == "proj_forms_off",
                CheckEvent.project == sample_project["name"],
            )
        ).scalar()

    # Não deve ter aumentado
    assert count_after_second == count_after_first


def test_put_project_notifies_web_check_when_transport_changes(client, admin_session, sample_project, monkeypatch):
    """Quando transport_enabled muda, notify_web_check_data_changed deve ser chamado."""
    notifications: list[str] = []
    monkeypatch.setattr(
        "sistema.app.routers.admin.notify_web_check_data_changed",
        lambda reason="refresh", **kwargs: notifications.append(reason),
    )

    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"transport_enabled": False},
    )
    assert resp.status_code == 200, resp.text
    assert "project_transport_flag" in notifications


def test_put_project_no_sse_when_transport_unchanged(client, admin_session, sample_project, monkeypatch):
    """Quando transport_enabled não muda, notify_web_check_data_changed NÃO deve ser chamado."""
    notifications: list[str] = []
    monkeypatch.setattr(
        "sistema.app.routers.admin.notify_web_check_data_changed",
        lambda reason="refresh", **kwargs: notifications.append(reason),
    )

    resp = client.put(
        f"{PROJECTS_URL}/{sample_project['id']}",
        cookies=admin_session,
        json={"emergency_phone": "+65 1234 5678"},  # só muda telefone
    )
    assert resp.status_code == 200, resp.text
    assert "project_transport_flag" not in notifications
