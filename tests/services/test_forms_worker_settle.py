from sistema.app.core.config import settings


def test_settle_defaults_are_capped_at_one_second():
    """Garante o contrato com o usuário: pausas reduzidas para máximo de 1 s."""
    assert settings.forms_settle_url_load_seconds <= 1.0
    assert settings.forms_settle_after_checkout_discovery_seconds <= 1.0
    assert settings.forms_settle_post_submit_seconds <= 1.0
