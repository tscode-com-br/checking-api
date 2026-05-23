"""Tests for Commit F — gate forms_enabled in submit_forms_event."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import FormsSubmission, Project, User
from sistema.app.routers.web_check import WEB_CHECK_CHANNEL
from sistema.app.schemas import MobileSyncStateResponse
from sistema.app.services.forms_submit import submit_forms_event
from sistema.app.services.user_sync import ensure_web_user

_NOW = datetime(2026, 5, 20, 8, 0, 0, tzinfo=timezone.utc)
_PROJECT_NAME = "P-GATES"


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_gates.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    return factory()


def _make_project(db: Session, *, forms_enabled: bool = True) -> Project:
    proj = Project(
        name=_PROJECT_NAME,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Gates Way",
        zip_code="000011",
        forms_enabled=forms_enabled,
        transport_enabled=True,
        emergency_phone="",
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def _stub_sync_state(chave: str) -> MobileSyncStateResponse:
    return MobileSyncStateResponse(found=True, chave=chave)


def test_submit_forms_event_skips_when_project_forms_disabled(tmp_path: Path):
    """When forms_enabled=False, submit_forms_event must skip the queue with
    reason=forms_disabled_for_project and return ok=True, queued_forms=False."""
    db = _make_session(tmp_path)
    _make_project(db, forms_enabled=False)

    with patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event",
        return_value=None,
    ):
        response = submit_forms_event(
            db,
            chave="GT01",
            projeto=_PROJECT_NAME,
            action="checkin",
            informe="normal",
            local="Escritório",
            event_time=_NOW,
            client_event_id="req-gate-disabled-1",
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
        )

    assert response.ok is True
    assert response.queued_forms is False

    submission = db.execute(
        sa.select(FormsSubmission).where(
            FormsSubmission.request_id == "req-gate-disabled-1"
        )
    ).scalar_one()
    assert submission.status == "skipped"
    assert submission.last_error == "forms_disabled_for_project"


def test_submit_forms_event_enqueues_when_project_forms_enabled(tmp_path: Path):
    """When forms_enabled=True (default), submit_forms_event enqueues normally.
    A fresh user with no prior activity is eligible for checkin queuing."""
    db = _make_session(tmp_path)
    _make_project(db, forms_enabled=True)

    with patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event",
        return_value=None,
    ), patch(
        "sistema.app.services.forms_submit.enqueue_forms_submission",
        wraps=lambda db_, **kwargs: _stub_enqueue(db_, **kwargs),
    ) as mock_enqueue:
        response = submit_forms_event(
            db,
            chave="GT02",
            projeto=_PROJECT_NAME,
            action="checkin",
            informe="normal",
            local="Escritório",
            event_time=_NOW,
            client_event_id="req-gate-enabled-1",
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
        )

    assert response.ok is True
    # Forms enabled — enqueue must have been called
    mock_enqueue.assert_called_once()
    # The submission should be present with pending status
    submission = db.execute(
        sa.select(FormsSubmission).where(
            FormsSubmission.request_id == "req-gate-enabled-1"
        )
    ).scalar_one()
    assert submission.status == "pending"
    assert submission.last_error != "forms_disabled_for_project"


def _stub_enqueue(db: Session, **kwargs) -> FormsSubmission:
    """Thin stub that creates a pending FormsSubmission without hitting
    the real queue worker."""
    from datetime import datetime as dt
    from sistema.app.models import FormsSubmission as FS
    from sistema.app.services.time_utils import now_sgt

    now = now_sgt()
    submission = FS(
        request_id=kwargs["request_id"],
        rfid=kwargs.get("rfid"),
        action=kwargs["action"],
        chave=kwargs["chave"],
        projeto=kwargs["projeto"],
        device_id=kwargs.get("device_id"),
        local=kwargs.get("local"),
        event_time=kwargs.get("event_time"),
        request_path=kwargs.get("request_path"),
        display_status="pending",
        ontime=kwargs.get("ontime", True),
        status="pending",
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    db.add(submission)
    db.flush()
    return submission
