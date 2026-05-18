"""E-mail templates for the accident/help-request notification flow."""


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
