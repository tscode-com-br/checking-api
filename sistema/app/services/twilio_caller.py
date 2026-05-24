from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import Accident, AccidentCallLog, AdminUser, Project, User
from .accident_numbering import format_accident_number
from .admin_updates import notify_admin_data_changed
from .email_sender import send_emergency_notification_email
from .time_utils import now_sgt

_logger = logging.getLogger(__name__)

_ENGLISH_COUNTRIES = {"US", "GB", "AU", "NZ", "CA", "IE", "IN", "SG", "PH", "MY"}

_DEFAULT_MESSAGE_PT = (
    "Alerta de acidente. Petrobras Checking System. Alerta de acidente. "
    "Um acidente foi reportado pelo funcionário Petrobras <nome> às <hora local> do dia <data>. "
    "O local reportado do acidente é <local> referente ao projeto <projeto>. "
    "O usuário solicita auxílio imediato no local. "
    "Caso haja dúvidas, ligue para o número <administrador>. "
    "Repetindo o número: <administrador>. Repetindo o número: <administrador>. "
    "Este alerta será enviado para o e-mail <E-Mail do Serviço Local de Emergência>."
)

_DEFAULT_MESSAGE_EN = (
    "Accident alert. Petrobras Checking System. Accident alert. "
    "An accident was reported by Petrobras employee <nome> at <hora local> on <data>. "
    "The reported location is <local> for project <projeto>. "
    "The user requests immediate assistance at the location. "
    "For inquiries, call <administrador>. "
    "Repeating: <administrador>. Repeating: <administrador>. "
    "An alert will be sent to <E-Mail do Serviço Local de Emergência>."
)


class TwilioNotConfiguredError(Exception):
    pass


class EmergencyCallAlreadyFiredError(Exception):
    pass


class EmergencyCallFailedError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_voice(country_code: str) -> tuple[str, str]:
    """Return (language, voice) for Twilio <Say> based on project country_code."""
    cc = (country_code or "").strip().upper()
    if cc == "BR":
        return "pt-BR", "Polly.Vitoria"
    return "en-US", "Polly.Joanna"


def _build_twiml(text: str, language: str, voice: str) -> str:
    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say language="{language}" voice="{voice}">{safe}</Say>'
        "</Response>"
    )


def _format_event_time(event_time: datetime, timezone_name: str) -> tuple[str, str]:
    """Return (hora_local HH:MM, data DD/MM/YYYY) in the project timezone."""
    try:
        tz = ZoneInfo(timezone_name or "UTC")
    except Exception:
        tz = timezone.utc
    local_dt = event_time.astimezone(tz)
    return local_dt.strftime("%H:%M"), local_dt.strftime("%d/%m/%Y")


def _substitute_placeholders(
    template: str,
    *,
    reporter_name: str,
    hora_local: str,
    data: str,
    reporter_local: str,
    project_name: str,
    mobile_admin: str,
    email_local_emergency: str,
) -> str:
    replacements = {
        "<nome>": reporter_name or "(não identificado)",
        "<hora local>": hora_local,
        "<data>": data,
        "<local>": reporter_local or "(não informado)",
        "<projeto>": project_name,
        "<administrador>": mobile_admin or "(não cadastrado)",
        "<E-Mail do Serviço Local de Emergência>": email_local_emergency or "(não cadastrado)",
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def _next_call_number(db: Session) -> int:
    """Concurrency-safe: lock the max row before computing next."""
    result = db.execute(
        select(func.coalesce(func.max(AccidentCallLog.call_number), 0) + 1).with_for_update()
    ).scalar()
    return int(result)


def make_emergency_call(
    db: Session,
    *,
    accident: Accident,
    project: Project,
    triggered_by_user: User | None = None,
    triggered_by_admin_user: AdminUser | None = None,
    reporter_name: str,
    reporter_local: str,
    event_time: datetime,
) -> AccidentCallLog:
    # Validate Twilio config for this project
    account_sid = project.twilio_account_sid or settings.twilio_account_sid or ""
    auth_token = project.twilio_auth_token or settings.twilio_auth_token or ""
    from_phone = project.twilio_phone_number or settings.twilio_phone_number or ""
    to_phone = project.emergency_phone or ""

    if not all([account_sid, auth_token, from_phone, to_phone]):
        raise TwilioNotConfiguredError(
            "Twilio não está totalmente configurado para este projeto. "
            "Verifique Account SID, Auth Token, número Twilio e Telefone de Emergência Local."
        )

    # Each user can only trigger one call per accident
    if triggered_by_user is not None:
        existing_call = db.execute(
            select(AccidentCallLog).where(
                AccidentCallLog.accident_id == accident.id,
                AccidentCallLog.triggered_by_user_id.is_not(None),
            )
        ).scalar_one_or_none()
        if existing_call is not None:
            raise EmergencyCallAlreadyFiredError(
                "Uma chamada de emergência já foi realizada por outro usuário neste acidente."
            )

    hora_local, data = _format_event_time(event_time, project.timezone_name)
    language, voice = _resolve_voice(project.country_code)

    message_template = project.emergency_call_message or (
        _DEFAULT_MESSAGE_PT if project.country_code == "BR" else _DEFAULT_MESSAGE_EN
    )
    message_text = _substitute_placeholders(
        message_template,
        reporter_name=reporter_name,
        hora_local=hora_local,
        data=data,
        reporter_local=reporter_local,
        project_name=accident.project_name_snapshot,
        mobile_admin=project.mobile_admin,
        email_local_emergency=project.email_local_emergency,
    )
    twiml_xml = _build_twiml(message_text, language, voice)

    call_number = _next_call_number(db)
    now = now_sgt()
    log = AccidentCallLog(
        call_number=call_number,
        call_sid=None,
        accident_id=accident.id,
        project_id=project.id,
        triggered_by_user_id=triggered_by_user.id if triggered_by_user else None,
        triggered_by_admin_id=triggered_by_admin_user.id if triggered_by_admin_user else None,
        to_phone=to_phone,
        from_phone=from_phone,
        call_status="queued",
        message_twiml=twiml_xml,
        created_at=now,
        updated_at=now,
    )
    db.add(log)
    db.commit()

    try:
        from twilio.rest import Client  # lazy import — not installed in dev by default

        client = Client(account_sid, auth_token)
        call_kwargs: dict = dict(
            to=to_phone,
            from_=from_phone,
            twiml=twiml_xml,
        )
        if settings.public_base_url:
            call_kwargs["status_callback"] = (
                f"{settings.public_base_url}/api/twilio/status-callback"
            )
            call_kwargs["status_callback_method"] = "POST"
            call_kwargs["status_callback_event"] = [
                "initiated", "ringing", "in-progress", "completed"
            ]

        call = client.calls.create(**call_kwargs)
        log.call_sid = call.sid
        log.call_status = "initiated"
    except ImportError:
        _logger.warning("Twilio SDK not installed — call queued but not sent")
        log.call_status = "failed"
        log.error_message = "Twilio SDK not installed (twilio>=9.0.0 required)"
        db.commit()
        raise EmergencyCallFailedError("Twilio SDK não instalado no servidor.")
    except Exception as exc:
        log.call_status = "failed"
        log.error_message = str(exc)[:1000]
        db.commit()
        _logger.error("Twilio call failed", exc_info=True)
        raise EmergencyCallFailedError(str(exc)) from exc

    log.updated_at = now_sgt()
    db.commit()

    send_emergency_notification_email(
        accident_number_label=format_accident_number(accident.accident_number),
        project=project,
        location_name=reporter_local or accident.location_name_snapshot or "",
        reporter_name=reporter_name,
        call_number=call_number,
        event_time=event_time,
    )

    notify_admin_data_changed(
        "emergency_call_initiated",
        metadata={
            "call_number": call_number,
            "accident_id": accident.id,
            "project_id": project.id,
        },
    )

    return log
