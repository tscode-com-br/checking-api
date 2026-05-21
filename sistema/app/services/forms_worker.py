from collections.abc import Callable, Sequence
from pathlib import Path
from time import monotonic, sleep
from typing import Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ..core.config import settings


FIELD_SEARCH_TIMEOUT_SECONDS = 60
SUCCESS_SEARCH_TIMEOUT_SECONDS = 60
PRE_SUBMIT_SUCCESS_CHECK_MS = 500
STEP_CONFIRM_TIMEOUT_SECONDS = 10
FIELD_SEARCH_RETRY_INTERVAL_SECONDS = 1.0
FIELD_SEARCH_CANDIDATE_TIMEOUT_MS = 250
URL_LOAD_SETTLE_SECONDS = 3.0
STEP_DISCOVERY_SETTLE_SECONDS = 0.5
AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS = 2.0
AFTER_FILL_SETTLE_SECONDS = 1.0
AFTER_SELECTION_SETTLE_SECONDS = 1.0
PRE_SUBMIT_SETTLE_SECONDS = 1.0
POST_SUBMIT_SETTLE_SECONDS = 5.0
KNOWN_SELECTOR_PREFIXES = ("css=", "xpath=", "text=", "role=", "label=")


FormsStatusCallback = Callable[[str], None]


class FormsStepTimeoutError(Exception):
    def __init__(self, step_name: str, timeout_seconds: int) -> None:
        self.step_name = step_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Step '{step_name}' not found within {timeout_seconds} seconds")


class FormsStepValidationError(Exception):
    def __init__(self, step_name: str, details: str) -> None:
        self.step_name = step_name
        self.details = details
        super().__init__(f"Step '{step_name}' validation failed: {details}")


class FormsProjectAbortError(Exception):
    def __init__(self, project_candidates: Sequence[str]) -> None:
        self.project_candidates = [str(value).strip().upper() for value in project_candidates if str(value).strip()]
        candidate_label = ", ".join(self.project_candidates) or "-"
        super().__init__(f"Nenhum projeto suportado no Forms para esta submissao: {candidate_label}")


class FormsWorker:
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir

    def load_xpath(self, name: str) -> str:
        return self.load_selectors(name)[0]

    def load_selectors(self, name: str) -> list[str]:
        path = self.assets_dir / "xpath" / name
        selectors = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not selectors:
            raise ValueError(f"Nenhum seletor configurado em {name}")
        return selectors

    def _normalize_selector(self, selector: str) -> str:
        normalized = selector.strip()
        if normalized.startswith(KNOWN_SELECTOR_PREFIXES):
            return normalized
        if normalized.startswith("/") or normalized.startswith("("):
            return f"xpath={normalized}"
        return normalized

    def _normalize_selector_candidates(self, selectors: Sequence[str] | str) -> list[str]:
        raw_selectors = [selectors] if isinstance(selectors, str) else list(selectors)
        normalized = [self._normalize_selector(selector) for selector in raw_selectors if str(selector).strip()]
        if not normalized:
            raise ValueError("Ao menos um seletor valido e obrigatorio")
        return normalized

    def _build_xpath_literal(self, value: str) -> str:
        if '"' not in value:
            return f'"{value}"'
        if "'" not in value:
            return f"'{value}'"
        parts = value.split('"')
        return "concat(" + ", '\"', ".join(f'"{part}"' for part in parts) + ")"

    def _build_project_xpath_map(self) -> dict[str, list[str]]:
        xpath_dir = self.assets_dir / "xpath"
        project_xpath_map: dict[str, list[str]] = {}
        for path in sorted(xpath_dir.glob("botao_projeto_*.txt")):
            project_name = path.stem.replace("botao_projeto_", "").strip().upper()
            if not project_name:
                continue
            project_xpath_map[project_name] = self.load_selectors(path.name)
        return project_xpath_map

    def _pause(self, page, seconds: float) -> None:
        if seconds <= 0:
            return
        wait_for_timeout = getattr(page, "wait_for_timeout", None)
        if callable(wait_for_timeout):
            wait_for_timeout(int(seconds * 1000))

    def _emit_status(self, status_callback: FormsStatusCallback | None, status: str) -> None:
        if status_callback is None:
            return
        status_callback(status)

    def _wait_for_step(self, page, selectors: Sequence[str] | str, step_name: str, timeout_seconds: int):
        normalized_selectors = self._normalize_selector_candidates(selectors)
        attempt_limit = max(int(timeout_seconds), 1)

        for _attempt in range(attempt_limit):
            for selector in normalized_selectors:
                try:
                    page.wait_for_selector(
                        selector,
                        state="visible",
                        timeout=FIELD_SEARCH_CANDIDATE_TIMEOUT_MS,
                    )
                    return page.locator(selector)
                except PlaywrightTimeoutError:
                    continue
            self._pause(page, FIELD_SEARCH_RETRY_INTERVAL_SECONDS)

        raise FormsStepTimeoutError(step_name=step_name, timeout_seconds=timeout_seconds)

    def _wait_for_step_confirmation(self, step_name: str, predicate, timeout_seconds: int, failure_details: str) -> None:
        deadline = monotonic() + timeout_seconds

        while monotonic() < deadline:
            if predicate():
                return
            sleep(1.0)

        raise FormsStepValidationError(step_name=step_name, details=failure_details)

    def _is_step_visible(self, page, selectors: Sequence[str] | str, timeout_ms: int = PRE_SUBMIT_SUCCESS_CHECK_MS) -> bool:
        for selector in self._normalize_selector_candidates(selectors):
            try:
                page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                return True
            except PlaywrightTimeoutError:
                continue
        return False

    def _normalize_detail_value(self, value: str) -> str:
        sanitized = value.replace("\n", " ").replace("\r", " ").strip()
        return " ".join(sanitized.split())

    def _fill_locator(self, locator, value: str, step_name: str) -> None:
        locator.fill(value)
        expected_value = value.strip()
        self._wait_for_step_confirmation(
            step_name=step_name,
            predicate=lambda: self._normalize_detail_value(locator.input_value()) == expected_value,
            timeout_seconds=STEP_CONFIRM_TIMEOUT_SECONDS,
            failure_details=f"expected_value={expected_value}",
        )

    def _click_locator(self, locator) -> None:
        locator.click()

    def _click_checked_locator(self, locator, step_name: str) -> None:
        locator.click()
        self._wait_for_step_confirmation(
            step_name=step_name,
            predicate=lambda: locator.is_checked(),
            timeout_seconds=STEP_CONFIRM_TIMEOUT_SECONDS,
            failure_details="expected_checked=true",
        )

    def _locate_step(self, page, selectors: Sequence[str] | str, step_name: str, *, settle_seconds: float = 0.0):
        locator = self._wait_for_step(page, selectors, step_name, FIELD_SEARCH_TIMEOUT_SECONDS)
        if settle_seconds > 0:
            self._pause(page, settle_seconds)
        return locator

    def _normalize_project_candidates(
        self,
        *,
        projeto: str | None,
        project_candidates: Sequence[str] | None,
    ) -> list[str]:
        normalized: list[str] = []
        for value in project_candidates or []:
            candidate = str(value or "").strip().upper()
            if candidate and candidate not in normalized:
                normalized.append(candidate)
        fallback_project = str(projeto or "").strip().upper()
        if fallback_project and fallback_project not in normalized:
            normalized.append(fallback_project)
        return normalized

    def _resolve_supported_project_name(
        self,
        *,
        projeto: str | None,
        project_candidates: Sequence[str] | None,
        project_xpath_map: dict[str, list[str]],
    ) -> str:
        normalized_candidates = self._normalize_project_candidates(
            projeto=projeto,
            project_candidates=project_candidates,
        )
        if not normalized_candidates:
            raise ValueError("Projeto invalido para check-in")
        unsupported_candidates = [candidate for candidate in normalized_candidates if candidate not in project_xpath_map]
        if unsupported_candidates:
            raise FormsProjectAbortError(normalized_candidates)
        return normalized_candidates[0]

    def _audit(self, audit_events: list[dict], status: str, message: str, details: str | None = None) -> None:
        audit_events.append(
            {
                "source": "forms",
                "action": "forms",
                "status": status,
                "message": message,
                "details": details,
            }
        )

    def _submit_once(
        self,
        action: Literal["checkin", "checkout"],
        chave: str,
        projeto: str | None,
        ontime: bool,
        *,
        project_candidates: Sequence[str] | None = None,
        status_callback: FormsStatusCallback | None = None,
    ) -> dict:
        audit_events: list[dict] = []
        completed_steps: list[str] = []
        digitar_chave = self.load_selectors("digitar_chave.txt")
        confirmar_chave = self.load_selectors("confirmar_chave.txt")
        botao_normal = self.load_selectors("botao_normal.txt")
        botao_retroativo = self.load_selectors("botao_retroativo.txt")
        botao_checkin = self.load_selectors("botao_checkin.txt")
        botao_checkout = self.load_selectors("botao_checkout.txt")
        botao_enviar = self.load_selectors("botao_enviar.txt")
        sucesso = self.load_selectors("sucesso.txt")

        projeto_xpath_map = self._build_project_xpath_map()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(settings.forms_url, timeout=settings.forms_timeout_seconds * 1000)
                self._audit(audit_events, "opened", "Microsoft Forms opened")
                self._emit_status(status_callback, "URL Carregada")
                self._pause(page, URL_LOAD_SETTLE_SECONDS)

                digitar_chave_locator = self._locate_step(
                    page,
                    digitar_chave,
                    "digitar_chave",
                    settle_seconds=STEP_DISCOVERY_SETTLE_SECONDS,
                )
                confirmar_chave_locator = self._locate_step(
                    page,
                    confirmar_chave,
                    "confirmar_chave",
                    settle_seconds=STEP_DISCOVERY_SETTLE_SECONDS,
                )
                botao_normal_locator = self._locate_step(
                    page,
                    botao_normal,
                    "botao_normal",
                    settle_seconds=STEP_DISCOVERY_SETTLE_SECONDS,
                )
                botao_retroativo_locator = self._locate_step(
                    page,
                    botao_retroativo,
                    "botao_retroativo",
                    settle_seconds=STEP_DISCOVERY_SETTLE_SECONDS,
                )
                botao_checkin_locator = self._locate_step(
                    page,
                    botao_checkin,
                    "botao_checkin",
                    settle_seconds=STEP_DISCOVERY_SETTLE_SECONDS,
                )
                botao_checkout_locator = self._locate_step(
                    page,
                    botao_checkout,
                    "botao_checkout",
                )
                self._pause(page, AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS)
                self._emit_status(status_callback, "Preenchendo...")

                self._fill_locator(digitar_chave_locator, chave, "digitar_chave")
                completed_steps.append("digitar_chave:filled+verified")
                self._pause(page, AFTER_FILL_SETTLE_SECONDS)
                self._fill_locator(confirmar_chave_locator, chave, "confirmar_chave")
                completed_steps.append("confirmar_chave:filled+verified")
                self._pause(page, AFTER_FILL_SETTLE_SECONDS)
                informe_locator = botao_normal_locator if ontime else botao_retroativo_locator
                informe_step_name = "botao_normal" if ontime else "botao_retroativo"
                self._click_checked_locator(informe_locator, informe_step_name)
                completed_steps.append(f"{informe_step_name}:clicked+verified")
                self._pause(page, AFTER_SELECTION_SETTLE_SECONDS)

                if action == "checkin":
                    self._click_checked_locator(botao_checkin_locator, "botao_checkin")
                    completed_steps.append("botao_checkin:clicked+verified")
                    self._pause(page, AFTER_SELECTION_SETTLE_SECONDS)
                    selected_project = self._resolve_supported_project_name(
                        projeto=projeto,
                        project_candidates=project_candidates,
                        project_xpath_map=projeto_xpath_map,
                    )
                    project_locator = self._locate_step(
                        page,
                        projeto_xpath_map[selected_project],
                        f"botao_projeto_{selected_project}",
                    )
                    self._click_checked_locator(project_locator, f"botao_projeto_{selected_project}")
                    completed_steps.append(f"botao_projeto_{selected_project}:clicked+verified")
                    self._emit_status(status_callback, "Preenchido")
                else:
                    self._click_checked_locator(botao_checkout_locator, "botao_checkout")
                    completed_steps.append("botao_checkout:clicked+verified")
                    self._emit_status(status_callback, "Preenchido")

                self._pause(page, PRE_SUBMIT_SETTLE_SECONDS)

                if self._is_step_visible(page, sucesso):
                    raise ValueError("XPath de sucesso ja estava visivel antes do envio")

                submit_started_at = monotonic()
                self._click_locator(self._locate_step(page, botao_enviar, "botao_enviar"))
                completed_steps.append("botao_enviar:clicked")
                self._pause(page, POST_SUBMIT_SETTLE_SECONDS)
                success_locator = self._wait_for_step(page, sucesso, "sucesso", SUCCESS_SEARCH_TIMEOUT_SECONDS)
                completed_steps.append("sucesso:visible")
                self._emit_status(status_callback, "Enviado")
                submit_elapsed_ms = int((monotonic() - submit_started_at) * 1000)
                success_text = self._normalize_detail_value(success_locator.inner_text())
                completed_details = (
                    f"steps={','.join(completed_steps)}; "
                    f"ontime={ontime}; "
                    "success_xpath_visible=true; "
                    f"submit_to_success_ms={submit_elapsed_ms}; "
                    f"success_text={success_text or '-'}"
                )
                self._audit(audit_events, "completed", "Microsoft Forms completed", completed_details)
            finally:
                browser.close()

        return {"success": True, "message": "Form submitted successfully", "audit_events": audit_events}

    def submit_with_retries(
        self,
        action: Literal["checkin", "checkout"],
        chave: str,
        projeto: str | None,
        ontime: bool = True,
        *,
        project_candidates: Sequence[str] | None = None,
        status_callback: FormsStatusCallback | None = None,
    ) -> dict:
        last_error = ""
        for attempt in range(1, settings.forms_max_retries + 1):
            try:
                result = self._submit_once(
                    action=action,
                    chave=chave,
                    projeto=projeto,
                    ontime=ontime,
                    project_candidates=project_candidates,
                    status_callback=status_callback,
                )
                result["retry_count"] = attempt - 1
                return result
            except FormsStepTimeoutError as exc:
                self._emit_status(status_callback, "Nao Encontrado")
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_step_timeout",
                    "failed_step": exc.step_name,
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms step timeout",
                            "details": f"step={exc.step_name}; timeout={exc.timeout_seconds}",
                        }
                    ],
                }
            except FormsProjectAbortError as exc:
                self._emit_status(status_callback, "Abortado")
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_project_unsupported",
                    "failed_step": "project_selection",
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms project selection aborted",
                            "details": f"projects={','.join(exc.project_candidates) or '-'}",
                        }
                    ],
                }
            except FormsStepValidationError as exc:
                self._emit_status(status_callback, "Abortado")
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_step_validation_failed",
                    "failed_step": exc.step_name,
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms step validation failed",
                            "details": f"step={exc.step_name}; {exc.details}",
                        }
                    ],
                }
            except ValueError as exc:
                self._emit_status(status_callback, "Abortado")
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_validation_error",
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms validation error",
                            "details": str(exc),
                        }
                    ],
                }
            except PlaywrightTimeoutError as exc:
                last_error = str(exc)

        return {
            "success": False,
            "message": f"Form submission failed: {last_error or 'unknown error'}",
            "retry_count": settings.forms_max_retries,
            "error_code": "forms_runtime_error",
            "audit_events": [
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "failed",
                    "message": "Forms runtime error",
                    "details": last_error or "unknown error",
                }
            ],
        }
