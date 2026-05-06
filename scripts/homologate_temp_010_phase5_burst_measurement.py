from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, Request, async_playwright


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREVIEW_DB_PREFIX = "preview_phase5_burst_measurement"
REPORT_PATH = ROOT / "docs" / "temp_010_phase5_burst_measurement_report.json"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8768
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
ADMIN_CHAVE = "HR70"
ADMIN_SENHA = "eAcacdLe2"
PROJECT_NAME = "P5BURST"
BASE_LOCATION_LABEL = "Phase5 Burst Base"
BASE_COORDS = (1.265936, 103.621066)
LOCATION_THRESHOLD_METERS = 25

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", f"sqlite:///./{PREVIEW_DB_PREFIX}.db")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("EVENT_ARCHIVES_DIR", str(ROOT / "preview_event_archives"))
os.environ.setdefault("ADMIN_SESSION_SECRET", "phase5-preview-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", ADMIN_CHAVE)
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", ADMIN_SENHA)
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")

SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "open_qr_code",
        "title": "Abrir o QR Code",
        "description": "Abrir a pagina com chave, senha e configuracoes persistidas, com GPS ja concedido.",
        "user": {"chave": "QRA1", "senha": "abc123"},
        "seed_initial_checkin": True,
        "setup": {
            "persisted_chave": True,
            "persisted_password": True,
            "automatic_activities_enabled": True,
            "permission_state": "granted",
            "persisted_permission_granted": True,
            "expected_location": BASE_LOCATION_LABEL,
        },
        "counted_action": "page_open",
    },
    {
        "name": "authenticate",
        "title": "Autenticar",
        "description": "Digitar chave e senha do zero, com pausas maiores que o debounce da verificacao silenciosa.",
        "user": {"chave": "AU02", "senha": "abc123"},
        "seed_initial_checkin": True,
        "setup": {
            "persisted_chave": False,
            "persisted_password": False,
            "automatic_activities_enabled": True,
            "permission_state": "granted",
            "persisted_permission_granted": True,
            "expected_location": BASE_LOCATION_LABEL,
        },
        "counted_action": "authenticate_by_typing",
    },
    {
        "name": "return_from_locked_screen",
        "title": "Voltar da tela bloqueada",
        "description": "Abrir a pagina com a chave persistida, permanecer bloqueado e desbloquear explicitamente com Enter.",
        "user": {"chave": "LK03", "senha": "abc123"},
        "seed_initial_checkin": True,
        "setup": {
            "persisted_chave": True,
            "persisted_password": False,
            "automatic_activities_enabled": True,
            "permission_state": "granted",
            "persisted_permission_granted": True,
            "expected_location": BASE_LOCATION_LABEL,
        },
        "counted_action": "unlock_from_prompt",
    },
    {
        "name": "switch_tabs",
        "title": "Alternar abas",
        "description": "Retornar para a aba autenticada dentro da janela curta de reuso de lifecycle.",
        "user": {"chave": "TB04", "senha": "abc123"},
        "seed_initial_checkin": True,
        "setup": {
            "persisted_chave": True,
            "persisted_password": True,
            "automatic_activities_enabled": True,
            "permission_state": "granted",
            "persisted_permission_granted": True,
            "expected_location": BASE_LOCATION_LABEL,
        },
        "counted_action": "tab_return_cluster",
    },
    {
        "name": "grant_location",
        "title": "Conceder localizacao",
        "description": "Autenticar sem permissao de GPS, conceder permissao depois e disparar um lifecycle de retorno de UI.",
        "user": {"chave": "GP05", "senha": "abc123"},
        "seed_initial_checkin": True,
        "setup": {
            "persisted_chave": True,
            "persisted_password": True,
            "automatic_activities_enabled": True,
            "permission_state": "denied",
            "persisted_permission_granted": False,
            "expected_location": "Sem Permissão",
            "expected_location_after_grant": BASE_LOCATION_LABEL,
        },
        "counted_action": "grant_permission_then_lifecycle",
    },
    {
        "name": "submit_checkin_checkout",
        "title": "Registrar check-in/check-out",
        "description": "Submeter check-in e depois check-out manualmente, com GPS concedido e atividades automaticas desligadas.",
        "user": {"chave": "SB06", "senha": "abc123"},
        "seed_initial_checkin": False,
        "setup": {
            "persisted_chave": True,
            "persisted_password": True,
            "automatic_activities_enabled": False,
            "permission_state": "granted",
            "persisted_permission_granted": True,
            "expected_location": BASE_LOCATION_LABEL,
        },
        "counted_action": "submit_checkin_checkout",
    },
)

def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_rectangle_coordinates(
    latitude: float,
    longitude: float,
    *,
    latitude_delta: float = 0.0002,
    longitude_delta: float = 0.0002,
) -> list[dict[str, float]]:
    return [
        {"latitude": latitude, "longitude": longitude},
        {"latitude": latitude + latitude_delta, "longitude": longitude},
        {"latitude": latitude + latitude_delta, "longitude": longitude + longitude_delta},
        {"latitude": latitude, "longitude": longitude + longitude_delta},
    ]


def build_point_inside(base_coords: tuple[float, float]) -> tuple[float, float]:
    return (base_coords[0] + 0.00005, base_coords[1] + 0.00005)


def build_fast_sequence(latitude: float, longitude: float) -> list[dict[str, object]]:
    return [
        {
            "delay_ms": 120,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 42},
        },
        {
            "delay_ms": 240,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 18},
        },
        {
            "delay_ms": 360,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 8},
        },
    ]


def build_submit_guard_sequence(latitude: float, longitude: float) -> list[dict[str, object]]:
    return [
        {
            "delay_ms": 500,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 42},
        },
        {
            "delay_ms": 1800,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 18},
        },
        {
            "delay_ms": 3200,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 8},
        },
    ]


def build_init_script(
    *,
    persisted_chave: str,
    persisted_password_map: dict[str, str],
    persisted_settings_map: dict[str, dict[str, object]],
    initial_permission_state: str,
    persisted_permission_granted: bool,
    initial_sequence: list[dict[str, object]],
) -> str:
    return f"""
(() => {{
  const persistedChave = {json.dumps(persisted_chave)};
  const persistedPasswordMap = {json.dumps(persisted_password_map)};
  const persistedSettingsMap = {json.dumps(persisted_settings_map)};
  let permissionState = {json.dumps(initial_permission_state)};
  let visibilityState = 'visible';
  let activeSequence = {json.dumps(initial_sequence)};
  const persistedPermissionGranted = {json.dumps(bool(persisted_permission_granted))};
  const chaveStorageKey = 'checking.web.user.chave';
  const passwordStorageKey = 'checking.web.user.password.by-chave';
  const settingsStorageKey = 'checking.web.user.settings.by-chave';
  const permissionStorageKey = 'checking.web.user.location.permission-granted';

  if (persistedChave) {{
    window.localStorage.setItem(chaveStorageKey, persistedChave);
  }} else {{
    window.localStorage.removeItem(chaveStorageKey);
  }}
  window.localStorage.setItem(passwordStorageKey, JSON.stringify(persistedPasswordMap));
  window.localStorage.setItem(settingsStorageKey, JSON.stringify(persistedSettingsMap));
  if (persistedPermissionGranted) {{
    window.localStorage.setItem(permissionStorageKey, '1');
  }} else {{
    window.localStorage.removeItem(permissionStorageKey);
  }}

  function createPosition(position) {{
    const payload = position || {{}};
    return {{
      coords: {{
        latitude: Number(payload.latitude),
        longitude: Number(payload.longitude),
        accuracy: Number(payload.accuracy),
      }},
      timestamp: Date.now(),
    }};
  }}

  function createErrorPayload(error) {{
    const payload = error || {{}};
    return {{
      code: Number.isFinite(payload.code) ? Number(payload.code) : 2,
      message: String(payload.message || 'Mocked geolocation error'),
    }};
  }}

  function queueSequence(sequence, onSuccess, onError) {{
    const timers = [];
    for (const entry of Array.isArray(sequence) ? sequence : []) {{
      const delayMs = Number.isFinite(entry && entry.delay_ms) ? Math.max(0, Number(entry.delay_ms)) : 0;
      const timerId = window.setTimeout(() => {{
        if (entry && entry.error) {{
          onError(createErrorPayload(entry.error));
          return;
        }}
        onSuccess(createPosition(entry && entry.position));
      }}, delayMs);
      timers.push(timerId);
    }}
    return timers;
  }}

  const geoState = {{
    nextWatchId: 1,
    activeTimers: new Map(),
  }};

  const geoMock = {{
    setSequence(sequence) {{
      activeSequence = Array.isArray(sequence) ? sequence : [];
    }},
    getSequence() {{
      return Array.isArray(activeSequence) ? activeSequence : [];
    }},
    setPermission(state) {{
      permissionState = String(state || '').trim() || 'prompt';
    }},
    getPermission() {{
      return permissionState;
    }},
    getCurrentPosition(onSuccess, onError) {{
      const sequence = this.getSequence();
      const firstEntry = sequence[0] || null;
      const delayMs = Number.isFinite(firstEntry && firstEntry.delay_ms) ? Math.max(0, Number(firstEntry.delay_ms)) : 0;
      window.setTimeout(() => {{
        if (permissionState === 'denied') {{
          onError(createErrorPayload({{ code: 1, message: 'Mocked permission denied' }}));
          return;
        }}
        if (firstEntry && firstEntry.error) {{
          onError(createErrorPayload(firstEntry.error));
          return;
        }}
        onSuccess(createPosition(firstEntry && firstEntry.position));
      }}, delayMs);
    }},
    watchPosition(onSuccess, onError) {{
      const watchId = geoState.nextWatchId++;
      if (permissionState === 'denied') {{
        const timerId = window.setTimeout(() => {{
          onError(createErrorPayload({{ code: 1, message: 'Mocked permission denied' }}));
        }}, 0);
        geoState.activeTimers.set(watchId, [timerId]);
        return watchId;
      }}
      const timers = queueSequence(this.getSequence(), onSuccess, onError);
      geoState.activeTimers.set(watchId, timers);
      return watchId;
    }},
    clearWatch(watchId) {{
      const timers = geoState.activeTimers.get(watchId) || [];
      for (const timerId of timers) {{
        window.clearTimeout(timerId);
      }}
      geoState.activeTimers.delete(watchId);
    }},
  }};

  const permissionsMock = {{
    async query() {{
      return {{ state: permissionState }};
    }},
  }};

  Object.defineProperty(navigator, 'geolocation', {{
    configurable: true,
    value: {{
      getCurrentPosition: geoMock.getCurrentPosition.bind(geoMock),
      watchPosition: geoMock.watchPosition.bind(geoMock),
      clearWatch: geoMock.clearWatch.bind(geoMock),
    }},
  }});

  Object.defineProperty(navigator, 'permissions', {{
    configurable: true,
    value: permissionsMock,
  }});

  Object.defineProperty(Document.prototype, 'visibilityState', {{
    configurable: true,
    get() {{
      return visibilityState;
    }},
  }});

  Object.defineProperty(Document.prototype, 'hidden', {{
    configurable: true,
    get() {{
      return visibilityState !== 'visible';
    }},
  }});

  window.__temp010GeoMock__ = geoMock;
  window.__temp010UiMock__ = {{
    setVisibilityState(nextValue) {{
      visibilityState = String(nextValue || 'visible');
    }},
    dispatchTabReturnCluster() {{
      visibilityState = 'hidden';
      document.dispatchEvent(new Event('visibilitychange'));
      visibilityState = 'visible';
      document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event('focus'));
      window.dispatchEvent(
        typeof PageTransitionEvent === 'function'
          ? new PageTransitionEvent('pageshow', {{ persisted: false }})
          : new Event('pageshow')
      );
    }},
  }};
}})();
"""


def build_persisted_settings_map(chave: str, automatic_activities_enabled: bool) -> dict[str, dict[str, object]]:
    return {
        str(chave).strip().upper(): {
            "project": PROJECT_NAME,
            "automaticActivitiesEnabled": bool(automatic_activities_enabled),
        }
    }


def build_persisted_password_map(chave: str, senha: str, enabled: bool) -> dict[str, str]:
    if not enabled:
        return {}
    return {str(chave).strip().upper(): str(senha)}


async def wait_for_health(timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=2.0) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get("/api/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
    raise TimeoutError("Timed out waiting for the local preview server to become healthy")


async def login_admin_client() -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0)
    response = await client.post(
        "/api/admin/auth/login",
        json={"chave": ADMIN_CHAVE, "senha": ADMIN_SENHA},
    )
    response.raise_for_status()
    return client


async def create_location(
    client: httpx.AsyncClient,
    *,
    local: str,
    project: str,
    base_coords: tuple[float, float],
    tolerance_meters: int,
) -> None:
    response = await client.post(
        "/api/admin/locations",
        json={
            "local": local,
            "coordinates": build_rectangle_coordinates(*base_coords),
            "projects": [project],
            "tolerance_meters": tolerance_meters,
        },
    )
    response.raise_for_status()


async def create_project(client: httpx.AsyncClient, *, project_name: str) -> None:
    response = await client.post(
        "/api/admin/projects",
        json={
            "name": project_name,
            "country_code": "SG",
            "country_name": "Singapore",
            "timezone_name": "Asia/Singapore",
            "address": "",
            "zip_code": "",
        },
    )
    response.raise_for_status()


async def register_web_user(*, chave: str, senha: str, projeto: str) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as client:
        register_response = await client.post(
            "/api/web/auth/register-user",
            json={
                "chave": chave,
                "nome": f"Burst {chave}",
                "projeto": projeto,
                "email": "",
                "senha": senha,
                "confirmar_senha": senha,
            },
        )
        register_response.raise_for_status()


async def create_initial_checkin(*, chave: str, senha: str, projeto: str, local: str) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as client:
        login_response = await client.post(
            "/api/web/auth/login",
            json={"chave": chave, "senha": senha},
        )
        login_response.raise_for_status()

        submit_response = await client.post(
            "/api/web/check",
            json={
                "chave": chave,
                "projeto": projeto,
                "action": "checkin",
                "local": local,
                "informe": "normal",
                "event_time": datetime.now(timezone.utc).isoformat(),
                "client_event_id": f"seed-{chave.lower()}-{int(time.time() * 1000)}",
            },
        )
        submit_response.raise_for_status()


async def seed_preview_data() -> None:
    admin_client = await login_admin_client()
    try:
        await create_project(admin_client, project_name=PROJECT_NAME)

        settings_response = await admin_client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": LOCATION_THRESHOLD_METERS},
        )
        settings_response.raise_for_status()

        await create_location(
            admin_client,
            local=BASE_LOCATION_LABEL,
            project=PROJECT_NAME,
            base_coords=BASE_COORDS,
            tolerance_meters=90,
        )
    finally:
        await admin_client.aclose()

    for scenario in SCENARIOS:
        chave = str(scenario["user"]["chave"])
        senha = str(scenario["user"]["senha"])
        await register_web_user(chave=chave, senha=senha, projeto=PROJECT_NAME)
        if bool(scenario["seed_initial_checkin"]):
            await create_initial_checkin(
                chave=chave,
                senha=senha,
                projeto=PROJECT_NAME,
                local=BASE_LOCATION_LABEL,
            )


def read_git_app_source(revision: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:sistema/app/static/check/app.js"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to read app.js from git revision {revision}")
    return result.stdout


def read_current_app_source() -> str:
    return (ROOT / "sistema" / "app" / "static" / "check" / "app.js").read_text(encoding="utf-8")


def read_head_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to resolve HEAD commit")
    return result.stdout.strip()


class ApiRequestTracker:
    def __init__(self, page: Page):
        self._pending: set[Request] = set()
        self._requests: list[dict[str, Any]] = []
        self._last_activity = time.monotonic()
        page.on("request", self._handle_request)
        page.on("requestfinished", self._handle_request_complete)
        page.on("requestfailed", self._handle_request_complete)

    @staticmethod
    def _normalize_request(request: Request) -> dict[str, Any] | None:
        parsed = urlparse(request.url)
        if parsed.path.startswith("/api/"):
            return {
                "method": request.method,
                "path": parsed.path,
                "url": request.url,
                "started_at": time.time(),
            }
        return None

    def _handle_request(self, request: Request) -> None:
        normalized = self._normalize_request(request)
        if normalized is None:
            return
        self._pending.add(request)
        self._requests.append(normalized)
        self._last_activity = time.monotonic()

    def _handle_request_complete(self, request: Request) -> None:
        if request in self._pending:
            self._pending.discard(request)
            self._last_activity = time.monotonic()

    async def wait_for_idle(self, *, timeout_seconds: float = 20.0, quiet_ms: int = 700) -> None:
        deadline = time.monotonic() + timeout_seconds
        quiet_seconds = quiet_ms / 1000.0
        while time.monotonic() < deadline:
            if not self._pending and (time.monotonic() - self._last_activity) >= quiet_seconds:
                return
            await asyncio.sleep(0.05)
        raise TimeoutError("Timed out waiting for the browser network to go idle")

    def clear(self) -> None:
        self._requests = []
        self._pending = set()
        self._last_activity = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        counter = Counter(f"{item['method']} {item['path']}" for item in self._requests)
        return {
            "total_requests": sum(counter.values()),
            "counts": dict(sorted(counter.items())),
            "sequence": [f"{item['method']} {item['path']}" for item in self._requests],
        }


async def wait_for_basic_page_ready(page: Page, *, timeout_ms: float = 15000) -> None:
    await page.wait_for_function(
        """() => {
          const projectSelect = document.querySelector('#projectSelect');
          const passwordInput = document.querySelector('#passwordInput');
          return Boolean(projectSelect && projectSelect.options.length > 0 && passwordInput);
        }""",
        timeout=timeout_ms,
    )


async def wait_for_locked_prompt(page: Page, *, expected_chave: str, timeout_ms: float = 15000) -> None:
    await page.wait_for_function(
        """(expectedChave) => {
          const chaveInput = document.querySelector('#chaveInput');
          const projectSelect = document.querySelector('#projectSelect');
          const primary = (document.querySelector('#notificationLinePrimary')?.textContent || '').trim();
          return Boolean(
            chaveInput
            && projectSelect
            && projectSelect.options.length > 0
            && chaveInput.value === expectedChave
            && primary.includes('Digite sua senha')
          );
        }""",
        arg=expected_chave,
        timeout=timeout_ms,
    )


async def wait_for_authenticated_ui_ready(
    page: Page,
    *,
    expected_location: str | None = None,
    automatic_enabled: bool | None = None,
    timeout_ms: float = 20000,
) -> None:
    await page.wait_for_function(
        """({ expectedLocation, automaticEnabled }) => {
          const projectSelect = document.querySelector('#projectSelect');
          const passwordInput = document.querySelector('#passwordInput');
          const submitButton = document.querySelector('#submitButton');
          const toggle = document.querySelector('#automaticActivitiesToggle');
          const refreshButton = document.querySelector('#refreshLocationButton');
          const locationValue = (document.querySelector('#locationValue')?.textContent || '').trim();
          return Boolean(
            projectSelect
            && projectSelect.options.length > 0
            && passwordInput
            && passwordInput.value.length >= 3
            && submitButton
            && refreshButton
            && refreshButton.getAttribute('aria-busy') === 'false'
                        && (expectedLocation == null || expectedLocation === '' || locationValue === expectedLocation)
            && toggle
                        && (automaticEnabled == null || toggle.checked === automaticEnabled)
          );
        }""",
        arg={"expectedLocation": expected_location, "automaticEnabled": automatic_enabled},
        timeout=timeout_ms,
    )


async def wait_for_status_contains(page: Page, expected_text: str, *, timeout_ms: float = 15000) -> None:
    await page.wait_for_function(
        """(expectedText) => {
          const primary = (document.querySelector('#notificationLinePrimary')?.textContent || '').trim();
          return primary.includes(expectedText);
        }""",
        arg=expected_text,
        timeout=timeout_ms,
    )


async def wait_for_lifecycle_effect(
    page: Page,
    tracker: ApiRequestTracker,
    *,
    timeout_seconds: float = 15.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if tracker.snapshot()["total_requests"] > 0:
            return
        ui = await read_ui_snapshot(page)
        if "atualizada com sucesso" in str(ui["statusPrimary"]).lower():
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Timed out waiting for the lifecycle trigger to produce a visible effect")


async def read_ui_snapshot(page: Page) -> dict[str, Any]:
    return await page.evaluate(
        """() => ({
          locationValue: (document.querySelector('#locationValue')?.textContent || '').trim(),
          statusPrimary: (document.querySelector('#notificationLinePrimary')?.textContent || '').trim(),
          statusSecondary: (document.querySelector('#notificationLineSecondary')?.textContent || '').trim(),
          automaticChecked: Boolean(document.querySelector('#automaticActivitiesToggle')?.checked),
          selectedAction: document.querySelector('input[name="action"]:checked')?.value || null,
        })"""
    )


async def set_browser_sequence(page: Page, sequence: list[dict[str, object]]) -> None:
    await page.evaluate(
        """(nextSequence) => {
          window.__temp010GeoMock__.setSequence(nextSequence);
        }""",
        sequence,
    )


async def set_browser_permission(page: Page, permission_state: str) -> None:
    await page.evaluate(
        """(nextState) => {
          window.__temp010GeoMock__.setPermission(nextState);
        }""",
        permission_state,
    )


async def dispatch_tab_return_cluster(page: Page) -> None:
    await page.evaluate(
        """() => {
          window.__temp010UiMock__.dispatchTabReturnCluster();
        }"""
    )


async def create_scenario_page(browser, scenario: dict[str, Any], app_source: str):
    setup = scenario["setup"]
    user = scenario["user"]
    startup_point = build_point_inside(BASE_COORDS)
    context = await browser.new_context(base_url=BASE_URL, viewport={"width": 430, "height": 932})

    await context.route(
        "**/app.js",
        lambda route: route.fulfill(status=200, body=app_source, content_type="application/javascript"),
    )
    await context.add_init_script(
        build_init_script(
            persisted_chave=str(user["chave"]) if bool(setup["persisted_chave"]) else "",
            persisted_password_map=build_persisted_password_map(
                str(user["chave"]),
                str(user["senha"]),
                bool(setup["persisted_password"]),
            ),
            persisted_settings_map=build_persisted_settings_map(
                str(user["chave"]),
                bool(setup["automatic_activities_enabled"]),
            ),
            initial_permission_state=str(setup["permission_state"]),
            persisted_permission_granted=bool(setup["persisted_permission_granted"]),
            initial_sequence=build_fast_sequence(*startup_point),
        )
    )
    page = await context.new_page()
    tracker = ApiRequestTracker(page)
    return context, page, tracker


async def run_open_qr_code_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location"]),
            automatic_enabled=bool(scenario["setup"]["automatic_activities_enabled"]),
        )
        await tracker.wait_for_idle(timeout_seconds=20.0)
        return {
            "ui": await read_ui_snapshot(page),
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


async def run_authenticate_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    user = scenario["user"]
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_basic_page_ready(page)
        await tracker.wait_for_idle(timeout_seconds=10.0)
        tracker.clear()

        await page.locator("#chaveInput").fill(str(user["chave"]))
        await wait_for_locked_prompt(page, expected_chave=str(user["chave"]))
        await page.locator("#passwordInput").click()
        await page.locator("#passwordInput").type(str(user["senha"]), delay=380)
        await page.locator("#passwordInput").press("Enter")

        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location"]),
            automatic_enabled=bool(scenario["setup"]["automatic_activities_enabled"]),
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=25.0)
        return {
            "ui": await read_ui_snapshot(page),
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


async def run_unlock_from_prompt_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    user = scenario["user"]
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_locked_prompt(page, expected_chave=str(user["chave"]))
        await tracker.wait_for_idle(timeout_seconds=10.0)
        tracker.clear()

        await page.locator("#passwordInput").fill(str(user["senha"]))
        await page.locator("#passwordInput").press("Enter")

        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location"]),
            automatic_enabled=bool(scenario["setup"]["automatic_activities_enabled"]),
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=25.0)
        return {
            "ui": await read_ui_snapshot(page),
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


async def run_tab_switch_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location"]),
            automatic_enabled=bool(scenario["setup"]["automatic_activities_enabled"]),
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=20.0)
        await asyncio.sleep(1.3)
        tracker.clear()

        await dispatch_tab_return_cluster(page)
        await wait_for_lifecycle_effect(page, tracker, timeout_seconds=15.0)
        await tracker.wait_for_idle(timeout_seconds=15.0)

        return {
            "ui": await read_ui_snapshot(page),
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


async def run_grant_location_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_authenticated_ui_ready(
            page,
            expected_location=None,
            automatic_enabled=None,
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=20.0)
        await asyncio.sleep(1.3)
        tracker.clear()

        await set_browser_permission(page, "granted")
        await set_browser_sequence(page, build_fast_sequence(*build_point_inside(BASE_COORDS)))
        await dispatch_tab_return_cluster(page)
        await wait_for_lifecycle_effect(page, tracker, timeout_seconds=15.0)

        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location_after_grant"]),
            automatic_enabled=None,
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=20.0)
        return {
            "ui": await read_ui_snapshot(page),
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


async def run_submit_checkin_checkout_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    context, page, tracker = await create_scenario_page(browser, scenario, app_source)
    try:
        await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
        await wait_for_authenticated_ui_ready(
            page,
            expected_location=str(scenario["setup"]["expected_location"]),
            automatic_enabled=bool(scenario["setup"]["automatic_activities_enabled"]),
            timeout_ms=25000,
        )
        await tracker.wait_for_idle(timeout_seconds=20.0)
        tracker.clear()

        await set_browser_sequence(page, build_submit_guard_sequence(*build_point_inside(BASE_COORDS)))
        await page.locator("#submitButton").click()
        await asyncio.sleep(8.0)
        first_submit_ui = await read_ui_snapshot(page)
        assert_condition(
            "Check-In conclu" in str(first_submit_ui["statusPrimary"]),
            f"Unexpected status after the first submit: {first_submit_ui}",
        )

        await page.locator('input[name="action"][value="checkout"]').check()
        await page.locator("#submitButton").click()
        await asyncio.sleep(8.0)
        second_submit_ui = await read_ui_snapshot(page)
        assert_condition(
            "Check-Out conclu" in str(second_submit_ui["statusPrimary"]),
            f"Unexpected status after the second submit: {second_submit_ui}",
        )

        await tracker.wait_for_idle(timeout_seconds=25.0)
        return {
            "ui": second_submit_ui,
            "requests": tracker.snapshot(),
        }
    finally:
        await context.close()


SCENARIO_RUNNERS = {
    "page_open": run_open_qr_code_scenario,
    "authenticate_by_typing": run_authenticate_scenario,
    "unlock_from_prompt": run_unlock_from_prompt_scenario,
    "tab_return_cluster": run_tab_switch_scenario,
    "grant_permission_then_lifecycle": run_grant_location_scenario,
    "submit_checkin_checkout": run_submit_checkin_checkout_scenario,
}


async def run_scenario(browser, scenario: dict[str, Any], app_source: str) -> dict[str, Any]:
    runner = SCENARIO_RUNNERS[str(scenario["counted_action"])]
    result = await runner(browser, scenario, app_source)
    return {
        "scenario": scenario["name"],
        "title": scenario["title"],
        "description": scenario["description"],
        "user_chave": scenario["user"]["chave"],
        **result,
    }


async def run_variant_measurement(
    *,
    variant_name: str,
    app_source: str,
    scenario_filter: set[str] | None,
) -> dict[str, Any]:
    preview_db_path = ROOT / f"{PREVIEW_DB_PREFIX}_{variant_name}.db"
    if preview_db_path.exists():
        preview_db_path.unlink()

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite:///./{preview_db_path.name}",
            "FORMS_QUEUE_ENABLED": "false",
            "EVENT_ARCHIVES_DIR": str(ROOT / "preview_event_archives"),
            "ADMIN_SESSION_SECRET": "phase5-preview-secret",
            "BOOTSTRAP_ADMIN_KEY": ADMIN_CHAVE,
            "BOOTSTRAP_ADMIN_PASSWORD": ADMIN_SENHA,
            "BOOTSTRAP_ADMIN_NAME": "Tamer Salmem",
        }
    )

    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sistema.app.main:app",
            "--host",
            SERVER_HOST,
            "--port",
            str(SERVER_PORT),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        await wait_for_health()
        await seed_preview_data()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                scenario_results = []
                for scenario in SCENARIOS:
                    if scenario_filter and str(scenario["name"]) not in scenario_filter:
                        continue
                    scenario_results.append(await run_scenario(browser, scenario, app_source))
            finally:
                await browser.close()

        return {
            "variant": variant_name,
            "base_url": BASE_URL,
            "preview_db": str(preview_db_path),
            "results": scenario_results,
        }
    except PlaywrightError as error:
        message = str(error)
        if "Executable doesn't exist" in message:
            raise RuntimeError(
                "Playwright Chromium is not installed in this environment. Run `python -m playwright install chromium`."
            ) from error
        raise
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait(timeout=10)


def build_comparison(before_report: dict[str, Any], after_report: dict[str, Any]) -> dict[str, Any]:
    before_by_name = {item["scenario"]: item for item in before_report["results"]}
    after_by_name = {item["scenario"]: item for item in after_report["results"]}
    comparison_rows = []
    global_relief = Counter()

    for scenario in SCENARIOS:
        scenario_name = str(scenario["name"])
        if scenario_name not in before_by_name or scenario_name not in after_by_name:
            continue

        before_item = before_by_name[scenario_name]
        after_item = after_by_name[scenario_name]
        before_counts = Counter(before_item["requests"]["counts"])
        after_counts = Counter(after_item["requests"]["counts"])
        positive_delta = before_counts - after_counts
        negative_delta = after_counts - before_counts
        global_relief.update(positive_delta)

        comparison_rows.append(
            {
                "scenario": scenario_name,
                "title": before_item["title"],
                "user_chave": before_item["user_chave"],
                "before_total_requests": before_item["requests"]["total_requests"],
                "after_total_requests": after_item["requests"]["total_requests"],
                "total_requests_relief": before_item["requests"]["total_requests"] - after_item["requests"]["total_requests"],
                "before_counts": dict(sorted(before_counts.items())),
                "after_counts": dict(sorted(after_counts.items())),
                "relieved_endpoints": dict(sorted(positive_delta.items())),
                "increased_endpoints": dict(sorted(negative_delta.items())),
            }
        )

    return {
        "scenario_comparisons": comparison_rows,
        "most_relieved_endpoints": [
            {"endpoint": endpoint, "request_relief": count}
            for endpoint, count in global_relief.most_common()
        ],
    }


async def run_measurement(*, scenario_filter: set[str] | None, variant_filter: set[str] | None) -> dict[str, Any]:
    head_commit = read_head_commit()
    variants = {
        "before_head": read_git_app_source("HEAD"),
        "after_worktree": read_current_app_source(),
    }

    selected_variants = [
        (name, source)
        for name, source in variants.items()
        if not variant_filter or name in variant_filter
    ]
    if not selected_variants:
        raise RuntimeError("No variants selected for measurement")

    reports = []
    for variant_name, app_source in selected_variants:
        reports.append(
            await run_variant_measurement(
                variant_name=variant_name,
                app_source=app_source,
                scenario_filter=scenario_filter,
            )
        )

    report: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "head_commit": head_commit,
        "base_url": BASE_URL,
        "preview_db_prefix": PREVIEW_DB_PREFIX,
        "location_threshold_meters": LOCATION_THRESHOLD_METERS,
        "variants": reports,
    }

    reports_by_name = {item["variant"]: item for item in reports}
    if "before_head" in reports_by_name and "after_worktree" in reports_by_name:
        report["comparison"] = build_comparison(reports_by_name["before_head"], reports_by_name["after_worktree"])

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Run only the named scenario. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        dest="variants",
        choices=["before_head", "after_worktree"],
        help="Run only the named app.js variant. Can be supplied multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(
        run_measurement(
            scenario_filter=set(args.scenarios or []),
            variant_filter=set(args.variants or []),
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()