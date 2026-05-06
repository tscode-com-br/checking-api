from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from locust import HttpUser, between, task


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load.phase10_support import (  # noqa: E402
    IdentityPool,
    build_web_location_payload,
    build_web_login_payload,
    build_web_registration_payload,
    build_web_submit_payload,
    load_phase10_harness_config,
)


CONFIG_PATH = os.getenv("CHECKCHECK_PHASE10_CONFIG")
if not CONFIG_PATH:
    raise RuntimeError("CHECKCHECK_PHASE10_CONFIG must point to a JSON harness config file")

HARNESS_CONFIG = load_phase10_harness_config(CONFIG_PATH)
IDENTITY_POOL = IdentityPool(HARNESS_CONFIG.identities)
PROFILE = str(os.getenv("CHECKCHECK_PHASE10_PROFILE", "web-check")).strip().lower()


class Phase10BaseUser(HttpUser):
    abstract = True
    wait_time = between(HARNESS_CONFIG.wait_time.min_seconds, HARNESS_CONFIG.wait_time.max_seconds)


class Phase10WebCheckUser(Phase10BaseUser):
    abstract = PROFILE not in {"web-check", "integrated"}
    weight = 6 if PROFILE == "integrated" else 1

    def on_start(self) -> None:
        self.identity = IDENTITY_POOL.checkout()
        self.action_index = 0
        self.resolved_local = HARNESS_CONFIG.location.fallback_local
        self._ensure_authenticated()

    def _get_json(self, response, *, expected_status: int, error_message: str) -> dict[str, object]:
        if response.status_code != expected_status:
            raise RuntimeError(f"{error_message}: status={response.status_code} body={response.text[:400]}")
        return response.json()

    def _get_auth_status(self) -> dict[str, object]:
        response = self.client.get(
            HARNESS_CONFIG.web_check.auth_status_path,
            params={"chave": self.identity.chave},
            name="GET /api/web/auth/status",
        )
        return self._get_json(response, expected_status=200, error_message="web auth status failed")

    def _get_projects(self) -> None:
        response = self.client.get(
            HARNESS_CONFIG.web_check.projects_path,
            name="GET /api/web/projects",
        )
        if response.status_code != 200:
            raise RuntimeError(f"web project catalog failed: status={response.status_code} body={response.text[:400]}")

    def _open_check_shell(self) -> None:
        response = self.client.get(
            HARNESS_CONFIG.web_check.page_path,
            name="GET /checking/user",
        )
        if response.status_code != 200 or 'id="checkForm"' not in response.text:
            raise RuntimeError(f"web check shell failed: status={response.status_code}")

    def _register_if_needed(self) -> None:
        if not self.identity.register_missing:
            return

        response = self.client.post(
            HARNESS_CONFIG.web_check.auth_register_user_path,
            json=build_web_registration_payload(self.identity),
            name="POST /api/web/auth/register-user",
        )
        if response.status_code == 201:
            return
        if response.status_code == 409:
            return
        raise RuntimeError(f"web user registration failed: status={response.status_code} body={response.text[:400]}")

    def _login(self) -> None:
        response = self.client.post(
            HARNESS_CONFIG.web_check.auth_login_path,
            json=build_web_login_payload(self.identity),
            name="POST /api/web/auth/login",
        )
        self._get_json(response, expected_status=200, error_message="web auth login failed")

    def _ensure_authenticated(self) -> None:
        if HARNESS_CONFIG.web_check.include_page_open:
            self._open_check_shell()

        status_payload = self._get_auth_status()
        if bool(status_payload.get("authenticated")):
            return

        if HARNESS_CONFIG.web_check.include_project_catalog:
            self._get_projects()

        if not bool(status_payload.get("has_password")):
            self._register_if_needed()

        self._login()

    def _load_check_state(self) -> None:
        response = self.client.get(
            HARNESS_CONFIG.web_check.check_state_path,
            params={"chave": self.identity.chave},
            name="GET /api/web/check/state",
        )
        self._get_json(response, expected_status=200, error_message="web check state failed")

    def _load_check_locations(self) -> None:
        response = self.client.get(
            HARNESS_CONFIG.web_check.check_locations_path,
            name="GET /api/web/check/locations",
        )
        self._get_json(response, expected_status=200, error_message="web check locations failed")

    def _resolve_location(self) -> None:
        response = self.client.post(
            HARNESS_CONFIG.web_check.check_location_match_path,
            json=build_web_location_payload(HARNESS_CONFIG.location),
            name="POST /api/web/check/location",
        )
        payload = self._get_json(response, expected_status=200, error_message="web check location match failed")
        resolved_local = payload.get("resolved_local")
        if isinstance(resolved_local, str) and resolved_local.strip():
            self.resolved_local = resolved_local.strip()

    def _submit_check(self) -> None:
        action = HARNESS_CONFIG.web_check.action_cycle[self.action_index % len(HARNESS_CONFIG.web_check.action_cycle)]
        self.action_index += 1

        response = self.client.post(
            HARNESS_CONFIG.web_check.check_submit_path,
            json=build_web_submit_payload(
                self.identity,
                action=action,
                informe=HARNESS_CONFIG.web_check.informe,
                local=self.resolved_local,
            ),
            name="POST /api/web/check",
        )
        payload = self._get_json(response, expected_status=200, error_message="web check submit failed")
        if payload.get("ok") is not True:
            raise RuntimeError(f"web check submit returned ok=false: {json.dumps(payload)[:400]}")

    @task
    def web_check_journey(self) -> None:
        if HARNESS_CONFIG.web_check.include_page_open:
            self._open_check_shell()

        self._ensure_authenticated()

        if HARNESS_CONFIG.web_check.include_project_catalog:
            self._get_projects()

        self._load_check_state()

        if HARNESS_CONFIG.web_check.include_location_options:
            self._load_check_locations()

        if HARNESS_CONFIG.web_check.include_location_resolution:
            self._resolve_location()

        self._submit_check()
        self._load_check_state()


class Phase10AdminUser(Phase10BaseUser):
    abstract = PROFILE not in {"admin", "integrated", "forms-backlog"}
    weight = 1

    def on_start(self) -> None:
        if HARNESS_CONFIG.admin is None:
            raise RuntimeError("The selected Phase 10 profile requires the admin section in the harness config")
        self._login_admin()

    def _admin_get_json(self, response, *, expected_status: int, error_message: str) -> dict[str, object] | list[object]:
        if response.status_code != expected_status:
            raise RuntimeError(f"{error_message}: status={response.status_code} body={response.text[:400]}")
        return response.json()

    def _login_admin(self) -> None:
        assert HARNESS_CONFIG.admin is not None
        response = self.client.post(
            HARNESS_CONFIG.admin.login_path,
            json={
                "chave": HARNESS_CONFIG.admin.credentials.chave,
                "senha": HARNESS_CONFIG.admin.credentials.senha,
            },
            name="POST /api/admin/auth/login",
        )
        self._admin_get_json(response, expected_status=200, error_message="admin login failed")

    @task
    def admin_monitoring_journey(self) -> None:
        assert HARNESS_CONFIG.admin is not None
        self._admin_get_json(
            self.client.get(HARNESS_CONFIG.admin.session_path, name="GET /api/admin/auth/session"),
            expected_status=200,
            error_message="admin session failed",
        )
        self._admin_get_json(
            self.client.get(HARNESS_CONFIG.admin.projects_path, name="GET /api/admin/projects"),
            expected_status=200,
            error_message="admin projects failed",
        )
        self._admin_get_json(
            self.client.get(
                HARNESS_CONFIG.admin.forms_queue_diagnostics_path,
                name="GET /api/admin/forms/queue/diagnostics",
            ),
            expected_status=200,
            error_message="admin forms queue diagnostics failed",
        )
        self._admin_get_json(
            self.client.get(
                HARNESS_CONFIG.admin.database_diagnostics_path,
                name="GET /api/admin/diagnostics/database",
            ),
            expected_status=200,
            error_message="admin database diagnostics failed",
        )


class Phase10TransportUser(Phase10BaseUser):
    abstract = PROFILE not in {"transport", "integrated"}
    weight = 1

    def on_start(self) -> None:
        if HARNESS_CONFIG.transport is None:
            raise RuntimeError("The selected Phase 10 profile requires the transport section in the harness config")
        self._login_transport()

    def _transport_get_json(self, response, *, expected_status: int, error_message: str) -> dict[str, object] | list[object]:
        if response.status_code != expected_status:
            raise RuntimeError(f"{error_message}: status={response.status_code} body={response.text[:400]}")
        return response.json()

    def _login_transport(self) -> None:
        assert HARNESS_CONFIG.transport is not None
        response = self.client.post(
            HARNESS_CONFIG.transport.verify_path,
            json={
                "chave": HARNESS_CONFIG.transport.credentials.chave,
                "senha": HARNESS_CONFIG.transport.credentials.senha,
            },
            name="POST /api/transport/auth/verify",
        )
        self._transport_get_json(response, expected_status=200, error_message="transport login failed")

    @task
    def transport_dashboard_journey(self) -> None:
        assert HARNESS_CONFIG.transport is not None
        self._transport_get_json(
            self.client.get(HARNESS_CONFIG.transport.session_path, name="GET /api/transport/auth/session"),
            expected_status=200,
            error_message="transport session failed",
        )
        self._transport_get_json(
            self.client.get(
                HARNESS_CONFIG.transport.dashboard_path,
                params={"route_kind": HARNESS_CONFIG.transport.route_kind},
                name="GET /api/transport/dashboard",
            ),
            expected_status=200,
            error_message="transport dashboard failed",
        )
        self._transport_get_json(
            self.client.get(HARNESS_CONFIG.transport.projects_path, name="GET /api/transport/projects"),
            expected_status=200,
            error_message="transport projects failed",
        )


class Phase10FormsBacklogProducerUser(Phase10WebCheckUser):
    abstract = PROFILE not in {"forms-backlog", "integrated"}
    weight = 4 if PROFILE == "forms-backlog" else 2

    def web_check_journey(self) -> None:  # pragma: no cover - inherited task disabled for backlog producer
        return None

    @task
    def forms_backlog_submit_journey(self) -> None:
        self._ensure_authenticated()
        self._submit_check()


class Phase10FormsBacklogMonitorUser(Phase10AdminUser):
    abstract = PROFILE not in {"forms-backlog", "integrated"}
    weight = 1

    def admin_monitoring_journey(self) -> None:  # pragma: no cover - inherited task disabled for backlog monitor
        return None

    @task
    def backlog_monitoring_journey(self) -> None:
        assert HARNESS_CONFIG.forms_backlog is not None
        response = self.client.get(
            HARNESS_CONFIG.forms_backlog.ready_path,
            name="GET /api/health/ready",
        )
        self._admin_get_json(response, expected_status=200, error_message="ready health failed")
        super().admin_monitoring_journey()