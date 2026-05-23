"""Tests for Commit E — is_forms_enabled_for_project / is_transport_enabled_for_project."""
from __future__ import annotations

import os

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

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

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.models import Project  # noqa: E402
from sistema.app.services.project_catalog import (  # noqa: E402
    is_forms_enabled_for_project,
    is_transport_enabled_for_any_project,
    is_transport_enabled_for_project,
    list_transport_enabled_project_names,
)

Base.metadata.create_all(bind=engine)

_PROJECT_NAME = "FLAGTEST"


def _upsert_project(db: Session, *, forms_enabled: bool, transport_enabled: bool) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJECT_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJECT_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="",
            zip_code="",
            forms_enabled=forms_enabled,
            transport_enabled=transport_enabled,
        )
        db.add(proj)
    else:
        proj.forms_enabled = forms_enabled
        proj.transport_enabled = transport_enabled
    db.commit()
    db.refresh(proj)
    return proj


@pytest.fixture(autouse=True)
def reset_flag_project():
    with SessionLocal() as db:
        _upsert_project(db, forms_enabled=True, transport_enabled=True)
    yield


# ---------------------------------------------------------------------------
# is_forms_enabled_for_project
# ---------------------------------------------------------------------------

def test_forms_enabled_true_by_default():
    with SessionLocal() as db:
        assert is_forms_enabled_for_project(db, projeto=_PROJECT_NAME) is True


def test_forms_enabled_false_when_disabled():
    with SessionLocal() as db:
        _upsert_project(db, forms_enabled=False, transport_enabled=True)
    with SessionLocal() as db:
        assert is_forms_enabled_for_project(db, projeto=_PROJECT_NAME) is False


def test_forms_enabled_true_for_unknown_project():
    with SessionLocal() as db:
        assert is_forms_enabled_for_project(db, projeto="UNKNOWNZZ99") is True


def test_forms_enabled_true_for_none_project():
    with SessionLocal() as db:
        assert is_forms_enabled_for_project(db, projeto=None) is True


def test_forms_enabled_true_for_empty_project():
    with SessionLocal() as db:
        assert is_forms_enabled_for_project(db, projeto="   ") is True


# ---------------------------------------------------------------------------
# is_transport_enabled_for_project
# ---------------------------------------------------------------------------

def test_transport_enabled_true_by_default():
    with SessionLocal() as db:
        assert is_transport_enabled_for_project(db, projeto=_PROJECT_NAME) is True


def test_transport_enabled_false_when_disabled():
    with SessionLocal() as db:
        _upsert_project(db, forms_enabled=True, transport_enabled=False)
    with SessionLocal() as db:
        assert is_transport_enabled_for_project(db, projeto=_PROJECT_NAME) is False


def test_transport_enabled_true_for_unknown_project():
    with SessionLocal() as db:
        assert is_transport_enabled_for_project(db, projeto="UNKNOWNZZ99") is True


def test_transport_enabled_true_for_none_project():
    with SessionLocal() as db:
        assert is_transport_enabled_for_project(db, projeto=None) is True


# ---------------------------------------------------------------------------
# Modificação 1 — is_transport_enabled_for_any_project (regra OR multi-projeto)
# ---------------------------------------------------------------------------

_MULTI_A = "MULTIFLAGA"
_MULTI_B = "MULTIFLAGB"
_MULTI_C = "MULTIFLAGC"


def _upsert_named_project(db: Session, name: str, *, transport_enabled: bool) -> Project:
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
        )
        db.add(proj)
    else:
        proj.transport_enabled = transport_enabled
    db.commit()
    db.refresh(proj)
    return proj


@pytest.fixture(autouse=True)
def reset_multi_projects():
    """Mantém os 3 projetos multi com transport_enabled=True antes de cada teste."""
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=True)
        _upsert_named_project(db, _MULTI_B, transport_enabled=True)
        _upsert_named_project(db, _MULTI_C, transport_enabled=True)
    yield
    with SessionLocal() as db:
        for name in (_MULTI_A, _MULTI_B, _MULTI_C):
            proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
            if proj is not None:
                proj.transport_enabled = True
        db.commit()


def test_transport_any_returns_true_for_empty_list():
    # Regra de default: sem projeto cadastrado → não bloqueia o botão.
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(db, projetos=[]) is True


def test_transport_any_returns_true_for_single_project_on():
    # Regra #1 (projeto único, ligado).
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=True)
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(db, projetos=[_MULTI_A]) is True


def test_transport_any_returns_false_for_single_project_off():
    # Regra #1 (projeto único, desligado).
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=False)
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(db, projetos=[_MULTI_A]) is False


def test_transport_any_returns_false_when_all_projects_off():
    # Regra #2 (multi-projeto, todos desligados).
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=False)
        _upsert_named_project(db, _MULTI_B, transport_enabled=False)
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(db, projetos=[_MULTI_A, _MULTI_B]) is False


def test_transport_any_returns_true_when_at_least_one_on():
    # Regra #3 (multi-projeto, mix ON/OFF).
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=False)
        _upsert_named_project(db, _MULTI_B, transport_enabled=True)
        _upsert_named_project(db, _MULTI_C, transport_enabled=False)
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(
            db, projetos=[_MULTI_A, _MULTI_B, _MULTI_C]
        ) is True


def test_transport_any_returns_true_when_all_projects_on():
    # Regra #4 (multi-projeto, todos ligados).
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=True)
        _upsert_named_project(db, _MULTI_B, transport_enabled=True)
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(db, projetos=[_MULTI_A, _MULTI_B]) is True


def test_transport_any_returns_true_for_unknown_project():
    # Projetos desconhecidos seguem o default ON.
    with SessionLocal() as db:
        assert is_transport_enabled_for_any_project(
            db, projetos=["UNKNOWNZZ99"]
        ) is True


def test_transport_any_ignores_none_and_empty_values():
    # Deve normalizar valores nulos/vazios sem erro.
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=False)
    with SessionLocal() as db:
        # Único projeto válido na lista é OFF → False.
        assert is_transport_enabled_for_any_project(
            db, projetos=[None, "", "   ", _MULTI_A]
        ) is False


# ---------------------------------------------------------------------------
# Modificação 1 — list_transport_enabled_project_names
# ---------------------------------------------------------------------------


def test_list_transport_enabled_filters_off_projects():
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=True)
        _upsert_named_project(db, _MULTI_B, transport_enabled=False)
        _upsert_named_project(db, _MULTI_C, transport_enabled=True)
    with SessionLocal() as db:
        result = list_transport_enabled_project_names(
            db, projetos=[_MULTI_A, _MULTI_B, _MULTI_C]
        )
    assert result == {_MULTI_A, _MULTI_C}


def test_list_transport_enabled_includes_unknown_projects():
    # Projetos desconhecidos seguem o default ON e entram no conjunto.
    with SessionLocal() as db:
        _upsert_named_project(db, _MULTI_A, transport_enabled=True)
    with SessionLocal() as db:
        result = list_transport_enabled_project_names(
            db, projetos=[_MULTI_A, "UNKNOWNZZ99"]
        )
    assert result == {_MULTI_A, "UNKNOWNZZ99"}


def test_list_transport_enabled_empty_for_empty_input():
    with SessionLocal() as db:
        assert list_transport_enabled_project_names(db, projetos=[]) == set()
