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
    is_transport_enabled_for_project,
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
