"""E-mail templates for the accident/help-request notification flow."""
from datetime import datetime


def render_help_request_email(
    *,
    recipient_name: str,
    requester_name: str,
    requester_chave: str,
    project_name: str,
    location_name: str,
) -> tuple[str, str]:
    subject = "(CHECKING) PEDIDO DE SOCORRO"
    body = (
        f"Prezado {recipient_name},\n\n"
        f"O usuário {requester_name}, chave {requester_chave}, pede AJUDA IMEDIATA, "
        f"ao reportar um acidente ocorrido no projeto {project_name}, local {location_name}.\n\n"
        "Esta mensagem foi disparada após o pedido de ajuda ter sido CONFIRMADO.\n\n"
        "Atenciosamente,\n"
        "Checking App\n"
    )
    return subject, body


def render_emergency_notification_email(
    *,
    accident_number_label: str,
    project_name: str,
    location_name: str,
    reporter_name: str,
    call_number: int,
    event_time: datetime,
) -> tuple[str, str]:
    subject = f"[EMERGÊNCIA] Acidente {accident_number_label} — {project_name}"
    time_str = event_time.strftime("%d/%m/%Y %H:%M")
    body = (
        f"Alerta de emergência — Checking App\n\n"
        f"Acidente N.º: {accident_number_label}\n"
        f"Projeto: {project_name}\n"
        f"Local: {location_name}\n"
        f"Reportado por: {reporter_name}\n"
        f"Data/Hora: {time_str}\n"
        f"Ligação de emergência N.º: {str(call_number).zfill(6)}\n\n"
        "O serviço de emergência local foi acionado via ligação automática.\n\n"
        "Atenciosamente,\n"
        "Checking App\n"
    )
    return subject, body
