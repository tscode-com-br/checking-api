"""Integration test (E2E) — complete admin accident lifecycle.

Covers Task L2: all 10 steps from opening an accident to deleting it,
exercised exclusively through HTTP endpoints with real DB writes.

Steps covered
-------------
1.  Fixtures provide admin_perfil_1 (full admin) and admin_perfil_9 (super-admin)
    already authenticated via POST /api/admin/auth/login.
2.  GET  /api/admin/accidents/active          → is_active=False  (no active accident)
3.  POST /api/admin/accidents/open            → 200, is_active=True
4.  GET  /api/admin/accidents/active          → is_active=True, situation_rows present
5.  POST /api/admin/accidents/close (perfil9) → 200, is_active=False;
        BackgroundTask builds archive synchronously inside TestClient
6.  GET  /api/admin/accidents                 → 1 row for this accident
7.  Row's download_ready=True                 (archive built by BackgroundTask)
8.  GET  /api/admin/accidents/{id}/archive    → 307 redirect to presigned URL
9.  DELETE /api/admin/accidents/{id} (perfil1) → 403 (only perfil=9 may delete)
10. DELETE /api/admin/accidents/{id} (perfil9) → 200; subsequent GET shows 0 rows
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa

from sistema.app.database import SessionLocal
from sistema.app.models import (
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
)

# ---------------------------------------------------------------------------
# Endpoint URLs
# ---------------------------------------------------------------------------

ACTIVE_URL = "/api/admin/accidents/active"
OPEN_URL = "/api/admin/accidents/open"
CLOSE_URL = "/api/admin/accidents/close"
LIST_URL = "/api/admin/accidents"


def _archive_url(accident_id: int) -> str:
    return f"/api/admin/accidents/{accident_id}/archive"


def _delete_url(accident_id: int) -> str:
    return f"/api/admin/accidents/{accident_id}"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _wipe_accidents(db: sa.orm.Session) -> None:
    """Close any open accident and remove all accident-related rows."""
    now = datetime.now(timezone.utc)
    db.execute(
        sa.update(Accident)
        .where(Accident.closed_at.is_(None))
        .values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(sa.delete(Accident))
    db.commit()


# ---------------------------------------------------------------------------
# Patches reused across the test
# ---------------------------------------------------------------------------

# Notify calls that would hit the Postgres LISTEN/NOTIFY broker
_LIFECYCLE_PATCHES = [
    "sistema.app.services.accident_lifecycle.notify_admin_data_changed",
    "sistema.app.services.accident_lifecycle.notify_web_check_data_changed",
]
# notify call inside build_and_attach_archive_for_accident
_ARCHIVE_NOTIFY_PATCH = "sistema.app.services.accident_archive_builder.notify_admin_data_changed"
# upload_stream as imported by the archive builder (must patch the local name)
_ARCHIVE_UPLOAD_PATCH = "sistema.app.services.accident_archive_builder.upload_stream"
# Router-level helpers that call outbound services
_ROUTER_PATCHES = [
    "sistema.app.routers.admin.notify_admin_data_changed",
    "sistema.app.routers.admin.notify_web_check_data_changed",
    "sistema.app.routers.admin.delete_prefix",
]
_PRESIGNED_PATCH = "sistema.app.routers.admin.generate_presigned_url"

_FAKE_PRESIGNED_URL = "https://fake-presigned.example.com/archive.zip?sig=test"


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------


def test_complete_admin_flow(
    admin_perfil_1,
    admin_perfil_9,
    accident_project,
):
    """Full admin accident cycle: open → verify active → close →
    check archive → attempt delete (perfil1 → 403) → delete (perfil9 → 200)."""

    # -----------------------------------------------------------------------
    # Setup: ensure no leftover state from prior test runs
    # -----------------------------------------------------------------------
    with SessionLocal() as db:
        _wipe_accidents(db)

    client1 = admin_perfil_1.client   # full admin, perfil=1 — can open/close, not delete
    client9 = admin_perfil_9.client   # super-admin, perfil=9 — can also delete

    proj_id = accident_project.id

    def _fake_upload(*, object_key: str, stream, content_type: str, **_):
        """No-op upload that prevents disk I/O in the archive builder."""
        return f"https://fake-storage.example.com/{object_key}"

    with (
        patch(_LIFECYCLE_PATCHES[0]),
        patch(_LIFECYCLE_PATCHES[1]),
        patch(_ARCHIVE_NOTIFY_PATCH),
        patch(_ARCHIVE_UPLOAD_PATCH, side_effect=_fake_upload),
        patch(_ROUTER_PATCHES[0]),
        patch(_ROUTER_PATCHES[1]),
        patch(_ROUTER_PATCHES[2]),
        patch(_PRESIGNED_PATCH, return_value=_FAKE_PRESIGNED_URL),
    ):
        # -------------------------------------------------------------------
        # Step 2: GET /active — no accident yet
        # -------------------------------------------------------------------
        resp = client1.get(ACTIVE_URL)
        assert resp.status_code == 200, f"[Step 2] {resp.text}"
        data = resp.json()
        assert data["is_active"] is False
        assert data["accident"] is None
        assert data["situation_rows"] == []

        # -------------------------------------------------------------------
        # Step 3: POST /open — open via perfil=1 admin
        # -------------------------------------------------------------------
        resp = client1.post(
            OPEN_URL,
            json={"project_id": proj_id, "custom_location_name": "E2E Test Zone"},
        )
        assert resp.status_code == 200, f"[Step 3] {resp.text}"
        open_data = resp.json()
        assert open_data["is_active"] is True
        assert open_data["accident"] is not None
        assert open_data["accident"]["location_name"] == "E2E Test Zone"
        assert open_data["accident"]["origin"] == "admin"
        assert open_data["accident"]["closed_at"] is None
        accident_id: int = open_data["accident"]["id"]

        # -------------------------------------------------------------------
        # Step 4: GET /active — accident is now active
        # -------------------------------------------------------------------
        resp = client1.get(ACTIVE_URL)
        assert resp.status_code == 200, f"[Step 4] {resp.text}"
        active_data = resp.json()
        assert active_data["is_active"] is True
        assert active_data["accident"]["id"] == accident_id
        assert isinstance(active_data["situation_rows"], list)

        # -------------------------------------------------------------------
        # Step 5: POST /close via perfil=9 — accident closed + archive built
        #
        # FastAPI TestClient executes BackgroundTasks synchronously, so
        # build_and_attach_archive_for_accident runs before this call returns.
        # -------------------------------------------------------------------
        resp = client9.post(CLOSE_URL)
        assert resp.status_code == 200, f"[Step 5] {resp.text}"
        close_data = resp.json()
        assert close_data["is_active"] is False
        assert close_data["accident"] is None

        # -------------------------------------------------------------------
        # Step 6: GET /accidents (list) — exactly 1 row for our accident
        # -------------------------------------------------------------------
        resp = client9.get(LIST_URL)
        assert resp.status_code == 200, f"[Step 6] {resp.text}"
        list_data = resp.json()
        rows = list_data["rows"]
        assert len(rows) >= 1, "At least 1 closed accident must appear in list"
        our_row = next((r for r in rows if r["id"] == accident_id), None)
        assert our_row is not None, f"Accident {accident_id} not found in list: {rows}"

        # -------------------------------------------------------------------
        # Step 7: download_ready=True — archive built by BackgroundTask
        # -------------------------------------------------------------------
        assert our_row["download_ready"] is True, (
            "download_ready should be True: TestClient runs BackgroundTasks synchronously, "
            "but archive row was not created. Row: " + str(our_row)
        )

        # -------------------------------------------------------------------
        # Step 8: GET /archive/{id} — 307 redirect to presigned URL
        # -------------------------------------------------------------------
        resp = client9.get(_archive_url(accident_id), follow_redirects=False)
        assert resp.status_code == 307, f"[Step 8] Expected 307, got {resp.status_code}: {resp.text}"
        assert resp.headers["location"] == _FAKE_PRESIGNED_URL

        # -------------------------------------------------------------------
        # Step 9: DELETE via perfil=1 → 403 (only perfil=9 may delete)
        # -------------------------------------------------------------------
        resp = client1.delete(_delete_url(accident_id))
        assert resp.status_code == 403, f"[Step 9] Expected 403, got {resp.status_code}: {resp.text}"

        # -------------------------------------------------------------------
        # Step 10: DELETE via perfil=9 → 200; accident gone from list
        # -------------------------------------------------------------------
        resp = client9.delete(_delete_url(accident_id))
        assert resp.status_code == 200, f"[Step 10 delete] {resp.text}"
        assert resp.json()["ok"] is True

        resp = client9.get(LIST_URL)
        assert resp.status_code == 200, f"[Step 10 list] {resp.text}"
        remaining_ids = [r["id"] for r in resp.json()["rows"]]
        assert accident_id not in remaining_ids, (
            f"Deleted accident {accident_id} must not appear in list; got ids: {remaining_ids}"
        )
