"""Tests for Phase 9 / prompt 9.1 — emergency video upload URL flow.

Pins:
1. POST /api/web/check/accident/video persists AccidentVideoUpload.public_url
   non-empty in dev (local fallback).
2. build_situation_rows regenerates public_url at read-time so a private
   DO Spaces object still yields a presigned URL the admin can play.
3. The archive ZIP contains the video under Registros/<chave 4-chars>/<filename>.
"""
from __future__ import annotations

import os
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

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
from sistema.app.services.accident_situation_table import build_situation_rows  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

WEB_LOGIN_URL = "/api/web/auth/login"
VIDEO_URL = "/api/web/check/accident/video"
OPEN_URL = "/api/web/check/accident/open"

_PROJ_NAME = "VID_PROJ"
_USER_CHAVE = "VIDU"
_PASSWORD = "VidTest!1"


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJ_NAME)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="BR",
            country_name="Brasil",
            timezone_name="America/Sao_Paulo",
            address="Av V",
            zip_code="05050505",
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
            nome="Vid User",
            projeto=_PROJ_NAME,
            checkin=True,
            local="Vid Site",
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
    chave = "VIDA"
    admin = db.execute(sa.select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if admin is None:
        now = datetime.now(tz=timezone.utc)
        admin = AdminUser(chave=chave, nome_completo="Vid Admin",
                          password_hash=hash_password(_PASSWORD),
                          created_at=now, updated_at=now)
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


def _login_client() -> TestClient:
    with SessionLocal() as db:
        proj = _ensure_project(db)
        user = _ensure_user(db)
        _ensure_membership(db, user, proj)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": _USER_CHAVE, "senha": _PASSWORD})
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return client


def _open_accident_for_user() -> int:
    """Open an accident via /api/web/check/accident/open (origin=web) and return id."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_user(db)
        _ensure_membership(db, user, proj)
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
                "custom_location_name": "Vid Site",
                "zone": "safety",
                "status": "ok",
                "description": "vídeo test",
            },
        )
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        active = db.execute(
            sa.select(Accident).where(Accident.closed_at.is_(None))
        ).scalar_one()
        return active.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_upload_persists_non_empty_public_url_in_dev():
    """POST /api/web/check/accident/video → AccidentVideoUpload.public_url ≠ ''. """
    accident_id = _open_accident_for_user()

    client = _login_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            VIDEO_URL,
            files={
                "chave": (None, _USER_CHAVE, "text/plain"),
                "idempotency_key": (None, "vid-upload-public-url-1", "text/plain"),
                "video": ("clip.mp4", b"fake-video-bytes", "video/mp4"),
            },
        )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["public_url"], f"public_url is empty: {payload!r}"
    # In dev fallback the URL points to /api/admin/accidents/local-asset/<key>.
    assert payload["public_url"].startswith("/api/admin/accidents/local-asset/"), payload["public_url"]

    with SessionLocal() as db:
        row = db.execute(
            sa.select(AccidentVideoUpload).where(AccidentVideoUpload.accident_id == accident_id)
        ).scalar_one()
        assert row.public_url
        assert row.object_key
        assert _USER_CHAVE in row.object_key


def test_build_situation_rows_regenerates_video_url_from_object_key():
    """The video URL surfaced to the admin is regenerated at read-time.

    Even when AccidentVideoUpload.public_url was stored with a stale value,
    the situation table must regenerate from object_key via
    object_storage.generate_presigned_url. This is what makes the admin's
    "Registros" cell open the video in prod (where ACL=private).
    """
    accident_id = _open_accident_for_user()

    # Upload a clip.
    client = _login_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        client.post(
            VIDEO_URL,
            files={
                "chave": (None, _USER_CHAVE, "text/plain"),
                "idempotency_key": (None, "vid-regen-url-1", "text/plain"),
                "video": ("clip.mp4", b"fake-video-bytes", "video/mp4"),
            },
        )

    # Tamper with the stored public_url to simulate a stale value and confirm
    # build_situation_rows ignores it in favor of generate_presigned_url.
    with SessionLocal() as db:
        row = db.execute(
            sa.select(AccidentVideoUpload).where(AccidentVideoUpload.accident_id == accident_id)
        ).scalar_one()
        row.public_url = "https://stale.example.com/wrong"
        db.commit()

    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        rows = build_situation_rows(db, accident=accident)

    videos = [v for r in rows for v in r.videos]
    assert videos, "expected at least one video link in situation rows"
    surfaced_url = videos[0].public_url
    assert surfaced_url != "https://stale.example.com/wrong", (
        "situation table returned the stale persisted URL instead of regenerating"
    )
    # In dev (local), the regenerated URL points at the local-asset endpoint.
    assert surfaced_url.startswith("/api/admin/accidents/local-asset/"), surfaced_url


def test_build_situation_rows_falls_back_to_persisted_url_when_object_key_missing():
    """Safety net: if object_key is empty, we still surface the persisted public_url."""
    accident_id = _open_accident_for_user()

    client = _login_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        client.post(
            VIDEO_URL,
            files={
                "chave": (None, _USER_CHAVE, "text/plain"),
                "idempotency_key": (None, "vid-fallback-url-1", "text/plain"),
                "video": ("clip.mp4", b"fake-video-bytes", "video/mp4"),
            },
        )

    with SessionLocal() as db:
        row = db.execute(
            sa.select(AccidentVideoUpload).where(AccidentVideoUpload.accident_id == accident_id)
        ).scalar_one()
        row.object_key = ""
        row.public_url = "https://kept-as-fallback.example.com/clip.mp4"
        db.commit()

    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        rows = build_situation_rows(db, accident=accident)

    videos = [v for r in rows for v in r.videos]
    assert videos
    assert videos[0].public_url == "https://kept-as-fallback.example.com/clip.mp4"


# ---------------------------------------------------------------------------
# Archive ZIP/XLSX structure (item 5.2 final bullet)
# ---------------------------------------------------------------------------


def _make_isolated_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'arch.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


def test_archive_zip_places_videos_under_registros_chave_folder(tmp_path: Path):
    """ZIP must contain Registros/<chave 4-chars>/<filename> for every uploaded video."""
    import json as _json
    from sistema.app.services.accident_archive_builder import build_and_attach_archive_for_accident

    db = _make_isolated_session(tmp_path)
    now = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)

    proj = Project(
        name="VID_ARCH", country_code="BR", country_name="Brasil",
        timezone_name="America/Sao_Paulo", address="Av A", zip_code="06060606",
    )
    db.add(proj); db.flush()
    admin = AdminUser(chave="VARC", nome_completo="Adm Arch",
                      created_at=now, updated_at=now)
    db.add(admin); db.flush()
    accident = Accident(
        accident_number=900, project_id=proj.id, project_name_snapshot=proj.name,
        location_name_snapshot="Sala A", location_is_registered=False,
        origin="admin", opened_by_admin_id=admin.id, opened_at=now,
        description="archive test", created_at=now, updated_at=now,
    )
    db.add(accident); db.flush()
    user = User(
        chave="ARCV", nome="User Arch", projeto="VID_ARCH",
        checkin=False, local="Sala A", last_active_at=now,
        inactivity_days=0,
    )
    db.add(user); db.flush()
    report = AccidentUserReport(
        accident_id=accident.id, user_id=user.id,
        user_chave_snapshot=user.chave, user_name_snapshot=user.nome,
        user_phone_snapshot=None,
        user_projects_snapshot=_json.dumps(["VID_ARCH"]),
        user_local_snapshot="Sala A", zone="safety", status="ok",
        reported_at=now, created_at=now, updated_at=now,
    )
    db.add(report); db.flush()
    video = AccidentVideoUpload(
        idempotency_key="archive-zip-video-1", accident_id=accident.id,
        user_id=user.id, object_key="accidents/0900/ARCV/clip.mp4",
        public_url="local://x", content_type="video/mp4", size_bytes=18,
        captured_at=now, created_at=now,
    )
    db.add(video); db.flush()
    db.commit()

    # Stage the raw bytes the builder will pull from local storage.
    local_root = tmp_path / "accidents_local_storage"
    target = local_root / video.object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"fake-video-bytes")

    with (
        patch("sistema.app.services.accident_archive_builder.SessionLocal", return_value=db),
        patch(
            "sistema.app.services.object_storage.settings",
            MagicMock(
                event_archives_dir=str(tmp_path),
                do_spaces_bucket=None,
                do_spaces_access_key=None,
                do_spaces_secret_key=None,
                tz_name="UTC",
            ),
        ),
        patch("sistema.app.services.accident_archive_builder._use_remote", return_value=False),
        patch(
            "sistema.app.services.accident_archive_builder._local_root",
            return_value=local_root,
        ),
        patch("sistema.app.services.accident_archive_builder.notify_admin_data_changed"),
    ):
        build_and_attach_archive_for_accident(accident.id)

    zip_path = local_root / "accidents" / "0900" / "archive" / "0900.zip"
    assert zip_path.exists(), f"archive ZIP not generated at {zip_path}"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

    # Exactly one Registros/<chave>/<filename> entry, chave is 4-char USER chave.
    registros = [n for n in names if n.startswith("Registros/")]
    assert len(registros) == 1, f"expected exactly 1 Registros/ entry, got {names!r}"
    path = registros[0]
    parts = path.split("/")
    assert parts[0] == "Registros"
    assert parts[1] == "ARCV", f"expected ARCV subfolder, got {parts[1]!r}"
    assert len(parts[1]) == 4, "user chave subfolder must be 4 chars"
    assert path.endswith(".mp4"), path
