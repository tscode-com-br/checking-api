from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Accident, AccidentCallLog, AdminUser, Project, User
from ..services.admin_updates import notify_admin_data_changed
from ..services.time_utils import now_sgt
from ..services.twilio_caller import (
    _build_call_notification_metadata,
    _resolve_triggered_by,
    record_call_notification,
)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])

_logger = logging.getLogger(__name__)


# Map Twilio CallStatus values to the canonical status_event consumed by the
# admin front (admin2/app.js _buildNotificationLine).
#
# Twilio sends:    initiated / ringing / in-progress / completed / failed /
#                  busy / no-answer / canceled
# Item 3.2.5 wants:
#   - "está sendo completada" → initiated / ringing
#   - "foi atendida"           → in-progress
#   - "foi finalizada pelo sistema, duração X" → completed
#   - error variations          → failed / busy / no-answer / canceled
_STATUS_EVENT_MAP = {
    "initiated": "initiated",
    "ringing": "initiated",  # same UI line per item 3.2.5
    "in-progress": "answered",
    "completed": "completed",
    "failed": "failed",
    "busy": "busy",
    "no-answer": "no_answer",
    "canceled": "canceled",
}


def _resolve_status_event(twilio_status: str) -> str:
    return _STATUS_EVENT_MAP.get(twilio_status, twilio_status or "unknown")


@router.post("/status-callback")
async def twilio_status_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Webhook called by Twilio when a call status changes."""
    try:
        form = await request.form()
        call_sid = str(form.get("CallSid", ""))
        call_status = str(form.get("CallStatus", ""))
        duration_raw = form.get("CallDuration") or form.get("Duration")
        duration_seconds = int(duration_raw) if duration_raw else None
    except Exception:
        _logger.warning("Failed to parse Twilio callback form data", exc_info=True)
        return Response(status_code=200)

    if not call_sid:
        return Response(status_code=200)

    log = db.execute(
        select(AccidentCallLog).where(AccidentCallLog.call_sid == call_sid)
    ).scalar_one_or_none()

    if log is None:
        _logger.warning("Twilio callback for unknown call_sid=%s", call_sid)
        return Response(status_code=200)

    log.call_status = call_status
    if duration_seconds is not None:
        log.duration_seconds = duration_seconds
    # Twilio does not expose who hung up directly. We mark "system" by default
    # because the TwiML <Say> wrapper makes the system the active speaker.
    if call_status == "completed" and log.ended_by is None:
        log.ended_by = "system"
    log.updated_at = now_sgt()
    db.commit()

    # Build the rich SSE metadata consumed by the admin notification feed.
    accident = db.get(Accident, log.accident_id) if log.accident_id else None
    project = db.get(Project, log.project_id) if log.project_id else None
    triggered_by_admin = (
        db.get(AdminUser, log.triggered_by_admin_id) if log.triggered_by_admin_id else None
    )
    triggered_by_user = (
        db.get(User, log.triggered_by_user_id) if log.triggered_by_user_id else None
    )
    triggered_by_name, triggered_by_chave, triggered_by_role = _resolve_triggered_by(
        triggered_by_user=triggered_by_user,
        triggered_by_admin_user=triggered_by_admin,
        reporter_name_fallback="(desconhecido)",
    )

    if accident is not None and project is not None:
        metadata = _build_call_notification_metadata(
            log=log,
            accident=accident,
            project=project,
            triggered_by_name=triggered_by_name,
            triggered_by_chave=triggered_by_chave,
            triggered_by_role=triggered_by_role,
            status_event=_resolve_status_event(call_status),
            occurred_at=log.updated_at,
            duration_seconds=log.duration_seconds,
            ended_by=log.ended_by,
        )
        # Persist so the admin can refresh and still see the line (item 3.2.3).
        try:
            record_call_notification(
                db, log=log, metadata=metadata,
                project_timezone_name=project.timezone_name,
            )
            db.commit()
        except Exception:
            _logger.warning("Failed to persist call notification from callback", exc_info=True)
            db.rollback()
    else:
        # Accident/project deleted between call and callback. Send a minimal
        # metadata so the front still sees the status change. Persistence is
        # skipped because the parent accident is gone (cascade would prune any
        # row we wrote anyway).
        metadata = {
            "call_number": log.call_number,
            "call_number_label": str(log.call_number).zfill(6),
            "accident_id": log.accident_id,
            "call_status": call_status,
            "status_event": _resolve_status_event(call_status),
            "occurred_at": log.updated_at.isoformat() if log.updated_at else None,
            "duration_seconds": log.duration_seconds,
            "ended_by": log.ended_by,
        }

    notify_admin_data_changed("emergency_call_status_update", metadata=metadata)

    return Response(status_code=200)
