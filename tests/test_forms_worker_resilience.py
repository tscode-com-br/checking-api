from types import SimpleNamespace

from sistema.app.services import forms_worker as forms_worker_module
from sistema.app.services.forms_worker import FormsWorker


def _write_xpath_files(tmp_path, *, digitar_selector: str | None = None) -> None:
    xpath_dir = tmp_path / "xpath"
    xpath_dir.mkdir(parents=True)
    contents = {
        "digitar_chave.txt": digitar_selector or "//digitar_chave",
        "confirmar_chave.txt": "//confirmar_chave",
        "botao_normal.txt": "//botao_normal",
        "botao_retroativo.txt": "//botao_retroativo",
        "botao_checkin.txt": "//botao_checkin",
        "botao_checkout.txt": "//botao_checkout",
        "botao_enviar.txt": "//botao_enviar",
        "sucesso.txt": "//sucesso",
        "botao_projeto_P80.txt": "//botao_projeto_P80",
        "botao_projeto_P82.txt": "//botao_projeto_P82",
        "botao_projeto_P83.txt": "//botao_projeto_P83",
    }
    for name, content in contents.items():
        (xpath_dir / name).write_text(content, encoding="utf-8")


def test_forms_worker_tries_selector_fallbacks(tmp_path, monkeypatch):
    _write_xpath_files(tmp_path, digitar_selector="css=.missing\n//digitar_chave")

    send_selector = "xpath=//botao_enviar"
    success_selector = "xpath=//sucesso"

    class FakeLocator:
        def __init__(self, page, selector: str):
            self.page = page
            self.selector = selector

        def fill(self, value: str) -> None:
            self.page.filled[self.selector] = value

        def click(self) -> None:
            self.page.clicked.append(self.selector)
            self.page.checked.add(self.selector)
            if self.selector == send_selector:
                self.page.success_visible = True

        def input_value(self) -> str:
            return self.page.filled.get(self.selector, "")

        def is_checked(self) -> bool:
            return self.selector in self.page.checked

        def inner_text(self) -> str:
            if self.selector == success_selector:
                return "Sua resposta foi enviada."
            return ""

    class FakePage:
        def __init__(self):
            self.success_visible = False
            self.filled = {}
            self.clicked = []
            self.checked = set()
            self.visible_selectors = {
                "xpath=//digitar_chave",
                "xpath=//confirmar_chave",
                "xpath=//botao_normal",
                "xpath=//botao_retroativo",
                "xpath=//botao_checkin",
                "xpath=//botao_checkout",
                send_selector,
            }

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            if selector == success_selector and self.success_visible:
                return True
            if selector in self.visible_selectors:
                return True
            raise forms_worker_module.PlaywrightTimeoutError("timeout")

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

    class FakeBrowser:
        def __init__(self, page: FakePage):
            self.page = page

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakePlaywright:
        def __init__(self, page: FakePage):
            self.chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser(page))

    class FakePlaywrightContext:
        def __init__(self, page: FakePage):
            self.page = page

        def __enter__(self):
            return FakePlaywright(self.page)

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_page = FakePage()
    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext(fake_page))

    worker = FormsWorker(assets_dir=tmp_path)
    result = worker.submit_with_retries(action="checkout", chave="HR70", projeto="P80")

    assert result["success"] is True
    assert fake_page.filled["xpath=//digitar_chave"] == "HR70"


def test_forms_worker_reports_not_found_when_project_selector_never_appears(tmp_path, monkeypatch):
    _write_xpath_files(tmp_path)

    status_updates: list[str] = []

    class FakeLocator:
        def __init__(self, page, selector: str):
            self.page = page
            self.selector = selector

        def fill(self, value: str) -> None:
            self.page.filled[self.selector] = value

        def click(self) -> None:
            self.page.clicked.append(self.selector)
            self.page.checked.add(self.selector)

        def input_value(self) -> str:
            return self.page.filled.get(self.selector, "")

        def is_checked(self) -> bool:
            return self.selector in self.page.checked

        def inner_text(self) -> str:
            return ""

    class FakePage:
        def __init__(self):
            self.filled = {}
            self.clicked = []
            self.checked = set()
            self.visible_selectors = {
                "xpath=//digitar_chave",
                "xpath=//confirmar_chave",
                "xpath=//botao_normal",
                "xpath=//botao_retroativo",
                "xpath=//botao_checkin",
                "xpath=//botao_checkout",
                "xpath=//botao_enviar",
            }

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            if selector in self.visible_selectors:
                return True
            raise forms_worker_module.PlaywrightTimeoutError("timeout")

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

    class FakeBrowser:
        def __init__(self, page: FakePage):
            self.page = page

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakePlaywright:
        def __init__(self, page: FakePage):
            self.chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser(page))

    class FakePlaywrightContext:
        def __init__(self, page: FakePage):
            self.page = page

        def __enter__(self):
            return FakePlaywright(self.page)

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_page = FakePage()
    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext(fake_page))

    worker = FormsWorker(assets_dir=tmp_path)
    result = worker.submit_with_retries(
        action="checkin",
        chave="HR70",
        projeto="P80",
        status_callback=status_updates.append,
    )

    assert result["success"] is False
    assert result["error_code"] == "forms_step_timeout"
    assert result["failed_step"] == "botao_projeto_P80"
    assert status_updates == ["URL Carregada", "Preenchendo...", "Nao Encontrado"]


def test_settle_values_come_from_settings(tmp_path, monkeypatch):
    """Verifica que os pauses obedecem aos settings, não a constantes hardcoded."""
    from sistema.app.core.config import settings

    monkeypatch.setattr(settings, "forms_settle_url_load_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_after_checkout_discovery_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_post_submit_seconds", 0.5)

    _write_xpath_files(tmp_path)

    waits: list[int] = []
    send_selector = "xpath=//botao_enviar"
    success_selector = "xpath=//sucesso"

    class FakeLocator:
        def __init__(self, page, selector: str):
            self.page = page
            self.selector = selector

        def fill(self, value: str) -> None:
            self.page.filled[self.selector] = value

        def click(self) -> None:
            self.page.clicked.append(self.selector)
            self.page.checked.add(self.selector)
            if self.selector == send_selector:
                self.page.success_visible = True

        def input_value(self) -> str:
            return self.page.filled.get(self.selector, "")

        def is_checked(self) -> bool:
            return self.selector in self.page.checked

        def inner_text(self) -> str:
            if self.selector == success_selector:
                return "Sua resposta foi enviada."
            return ""

    class CapturingFakePage:
        def __init__(self):
            self.success_visible = False
            self.filled = {}
            self.clicked = []
            self.checked = set()
            self.visible_selectors = {
                "xpath=//digitar_chave",
                "xpath=//confirmar_chave",
                "xpath=//botao_normal",
                "xpath=//botao_retroativo",
                "xpath=//botao_checkin",
                "xpath=//botao_checkout",
                send_selector,
            }

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_timeout(self, ms: int) -> None:
            waits.append(ms)

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            if selector == success_selector and self.success_visible:
                return True
            if selector in self.visible_selectors:
                return True
            raise forms_worker_module.PlaywrightTimeoutError("timeout")

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

    class FakeBrowser:
        def __init__(self, page):
            self.page = page

        def new_page(self):
            return self.page

        def close(self) -> None:
            return None

    class FakePlaywright:
        def __init__(self, page):
            self.chromium = __import__("types").SimpleNamespace(launch=lambda headless=True: FakeBrowser(page))

    class FakePlaywrightContext:
        def __init__(self, page):
            self.page = page

        def __enter__(self):
            return FakePlaywright(self.page)

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_page = CapturingFakePage()
    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext(fake_page))

    worker = forms_worker_module.FormsWorker(assets_dir=tmp_path)
    worker.submit_with_retries(action="checkout", chave="HR70", projeto="P80")

    # 0.5 s => 500 ms deve aparecer; os valores antigos (3000, 2000, 5000) não devem aparecer
    assert 500 in waits
    assert 3000 not in waits
    assert 2000 not in waits
    assert 5000 not in waits