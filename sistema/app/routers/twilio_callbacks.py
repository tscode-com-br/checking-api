from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AccidentCallLog
from ..services.admin_updates import notify_admin_data_changed
from ..services.time_utils import now_sgt

router = APIRouter(prefix="/api/twilio", tags=["twilio"])

_logger = logging.getLogger(__name__)


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
    log.updated_at = now_sgt()
    db.commit()

    notify_admin_data_changed(
        "emergency_call_status_update",
        metadata={
            "call_number": log.call_number,
            "accident_id": log.accident_id,
            "call_status": call_status,
        },
    )

    return Response(status_code=200)
