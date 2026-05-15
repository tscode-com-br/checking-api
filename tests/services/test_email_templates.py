"""Tests for email_templates.render_help_request_email."""
from sistema.app.services.email_templates import render_help_request_email


def _render():
    return render_help_request_email(
        recipient_name="Admin Silva",
        requester_name="João Costa",
        requester_chave="JC001",
        project_name="Projeto Alpha",
        location_name="Bloco B",
    )


def test_subject_matches_spec():
    subject, _ = _render()
    assert subject == "(CHECKING) PEDIDO DE SOCORRO"


def test_body_includes_recipient_name():
    _, body = _render()
    assert "Prezado Admin Silva," in body


def test_body_includes_project_and_location():
    _, body = _render()
    assert "projeto Projeto Alpha" in body
    assert "local Bloco B" in body
    assert "chave JC001" in body
    assert "João Costa" in body


def test_body_confirms_help():
    _, body = _render()
    assert "AJUDA IMEDIATA" in body
    assert "CONFIRMADO" in body
    assert "Checking App" in body
