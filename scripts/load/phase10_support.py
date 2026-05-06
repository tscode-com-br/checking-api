from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


_BASE36_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(value: int) -> str:
    if value < 0:
        raise ValueError("Base36 conversion only supports non-negative integers")
    if value == 0:
        return "0"

    digits: list[str] = []
    remaining = value
    while remaining:
        remaining, remainder = divmod(remaining, 36)
        digits.append(_BASE36_ALPHABET[remainder])
    return "".join(reversed(digits))


def _normalize_key(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 4 or not normalized.isalnum():
        raise ValueError("Each harness key must have exactly 4 uppercase alphanumeric characters")
    return normalized


def _normalize_project(value: str) -> str:
    normalized = " ".join(str(value or "").strip().upper().split())
    if len(normalized) < 2:
        raise ValueError("Project names must contain at least 2 characters")
    return normalized


@dataclass(frozen=True)
class Phase10Identity:
    chave: str
    senha: str
    projeto: str
    nome: str
    email: str
    register_missing: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "chave", _normalize_key(self.chave))
        object.__setattr__(self, "senha", str(self.senha))
        object.__setattr__(self, "projeto", _normalize_project(self.projeto))
        object.__setattr__(self, "nome", " ".join(str(self.nome or "").strip().split()) or f"Load {self.chave}")
        normalized_email = str(self.email or "").strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("Each harness identity must provide a valid email address")
        object.__setattr__(self, "email", normalized_email)


@dataclass(frozen=True)
class GeneratedIdentityConfig:
    prefix: str
    count: int
    start_index: int = 1
    password: str = "abc123"
    project: str = "P80"
    register_missing: bool = True
    name_prefix: str = "Phase10 Load"
    email_domain: str = "load.invalid"

    def __post_init__(self) -> None:
        normalized_prefix = str(self.prefix or "").strip().upper()
        if not normalized_prefix or len(normalized_prefix) > 3 or not normalized_prefix.isalnum():
            raise ValueError("generated_users.prefix must contain 1 to 3 alphanumeric characters")
        if self.count <= 0:
            raise ValueError("generated_users.count must be greater than zero")
        if self.start_index < 0:
            raise ValueError("generated_users.start_index must be zero or greater")
        if len(str(self.password)) < 3 or len(str(self.password)) > 10:
            raise ValueError("generated_users.password must contain 3 to 10 characters")
        normalized_project = _normalize_project(self.project)
        normalized_name_prefix = " ".join(str(self.name_prefix or "").strip().split()) or "Phase10 Load"
        normalized_email_domain = str(self.email_domain or "").strip().lower()
        if not normalized_email_domain or "." not in normalized_email_domain:
            raise ValueError("generated_users.email_domain must be a valid domain name")
        object.__setattr__(self, "prefix", normalized_prefix)
        object.__setattr__(self, "password", str(self.password))
        object.__setattr__(self, "project", normalized_project)
        object.__setattr__(self, "name_prefix", normalized_name_prefix)
        object.__setattr__(self, "email_domain", normalized_email_domain)

        suffix_width = 4 - len(normalized_prefix)
        max_suffix_value = (36 ** suffix_width) - 1
        if self.start_index + self.count - 1 > max_suffix_value:
            raise ValueError("generated_users range exceeds the available 4-character key space for the chosen prefix")


@dataclass(frozen=True)
class WaitTimeConfig:
    min_seconds: float = 0.2
    max_seconds: float = 0.7

    def __post_init__(self) -> None:
        if self.min_seconds < 0 or self.max_seconds < 0:
            raise ValueError("wait_time values must be zero or greater")
        if self.max_seconds < self.min_seconds:
            raise ValueError("wait_time.max_seconds must be greater than or equal to wait_time.min_seconds")


@dataclass(frozen=True)
class LocationConfig:
    latitude: float
    longitude: float
    accuracy_meters: float = 8.0
    fallback_local: str = "Escritório Principal"

    def __post_init__(self) -> None:
        if self.latitude < -90 or self.latitude > 90:
            raise ValueError("location.latitude must be between -90 and 90")
        if self.longitude < -180 or self.longitude > 180:
            raise ValueError("location.longitude must be between -180 and 180")
        if self.accuracy_meters < 0:
            raise ValueError("location.accuracy_meters must be zero or greater")
        normalized_local = " ".join(str(self.fallback_local or "").strip().split())
        if len(normalized_local) < 2:
            raise ValueError("location.fallback_local must contain at least 2 characters")
        object.__setattr__(self, "fallback_local", normalized_local)


@dataclass(frozen=True)
class WebCheckScenarioConfig:
    page_path: str = "/checking/user"
    projects_path: str = "/api/web/projects"
    auth_status_path: str = "/api/web/auth/status"
    auth_register_user_path: str = "/api/web/auth/register-user"
    auth_login_path: str = "/api/web/auth/login"
    check_state_path: str = "/api/web/check/state"
    check_locations_path: str = "/api/web/check/locations"
    check_location_match_path: str = "/api/web/check/location"
    check_submit_path: str = "/api/web/check"
    include_page_open: bool = True
    include_project_catalog: bool = True
    include_location_resolution: bool = True
    include_location_options: bool = True
    action_cycle: tuple[str, ...] = ("checkin", "checkout")
    informe: str = "normal"

    def __post_init__(self) -> None:
        if not self.action_cycle:
            raise ValueError("web_check.action_cycle must contain at least one action")
        normalized_actions = tuple(str(action).strip().lower() for action in self.action_cycle)
        if any(action not in {"checkin", "checkout"} for action in normalized_actions):
            raise ValueError("web_check.action_cycle only supports checkin and checkout")
        normalized_informe = str(self.informe).strip().lower()
        if normalized_informe not in {"normal", "retroativo"}:
            raise ValueError("web_check.informe must be either normal or retroativo")
        object.__setattr__(self, "action_cycle", normalized_actions)
        object.__setattr__(self, "informe", normalized_informe)


@dataclass(frozen=True)
class OperatorCredentials:
    chave: str
    senha: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "chave", _normalize_key(self.chave))
        normalized_password = str(self.senha or "")
        if len(normalized_password) < 3:
            raise ValueError("Operator passwords must contain at least 3 characters")
        object.__setattr__(self, "senha", normalized_password)


@dataclass(frozen=True)
class AdminScenarioConfig:
    credentials: OperatorCredentials
    login_path: str = "/api/admin/auth/login"
    session_path: str = "/api/admin/auth/session"
    projects_path: str = "/api/admin/projects"
    forms_queue_diagnostics_path: str = "/api/admin/forms/queue/diagnostics"
    database_diagnostics_path: str = "/api/admin/diagnostics/database"


@dataclass(frozen=True)
class TransportScenarioConfig:
    credentials: OperatorCredentials
    verify_path: str = "/api/transport/auth/verify"
    session_path: str = "/api/transport/auth/session"
    dashboard_path: str = "/api/transport/dashboard"
    projects_path: str = "/api/transport/projects"
    route_kind: str = "home_to_work"

    def __post_init__(self) -> None:
        normalized_route_kind = str(self.route_kind or "").strip().lower()
        if normalized_route_kind not in {"home_to_work", "work_to_home"}:
            raise ValueError("transport.route_kind must be either home_to_work or work_to_home")
        object.__setattr__(self, "route_kind", normalized_route_kind)


@dataclass(frozen=True)
class FormsBacklogScenarioConfig:
    ready_path: str = "/api/health/ready"
    producer_action_cycle: tuple[str, ...] = ("checkin", "checkout")

    def __post_init__(self) -> None:
        normalized_actions = tuple(str(action).strip().lower() for action in self.producer_action_cycle)
        if not normalized_actions or any(action not in {"checkin", "checkout"} for action in normalized_actions):
            raise ValueError("forms_backlog.producer_action_cycle only supports checkin and checkout")
        object.__setattr__(self, "producer_action_cycle", normalized_actions)


@dataclass(frozen=True)
class Phase10HarnessConfig:
    wait_time: WaitTimeConfig
    location: LocationConfig
    web_check: WebCheckScenarioConfig
    identities: tuple[Phase10Identity, ...]
    admin: AdminScenarioConfig | None = None
    transport: TransportScenarioConfig | None = None
    forms_backlog: FormsBacklogScenarioConfig | None = None


def generate_identities(config: GeneratedIdentityConfig) -> list[Phase10Identity]:
    suffix_width = 4 - len(config.prefix)
    identities: list[Phase10Identity] = []
    for offset in range(config.count):
        numeric_index = config.start_index + offset
        suffix = _to_base36(numeric_index).rjust(suffix_width, "0")
        chave = _normalize_key(f"{config.prefix}{suffix}")
        identities.append(
            Phase10Identity(
                chave=chave,
                senha=config.password,
                projeto=config.project,
                nome=f"{config.name_prefix} {offset + 1}",
                email=f"{chave.lower()}@{config.email_domain}",
                register_missing=config.register_missing,
            )
        )
    return identities


def _load_explicit_identities(items: list[object]) -> list[Phase10Identity]:
    identities: list[Phase10Identity] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ValueError("identities entries must be JSON objects")
        identities.append(
            Phase10Identity(
                chave=str(raw_item.get("chave") or ""),
                senha=str(raw_item.get("senha") or ""),
                projeto=str(raw_item.get("projeto") or "P80"),
                nome=str(raw_item.get("nome") or f"Load {raw_item.get('chave') or ''}"),
                email=str(raw_item.get("email") or f"{str(raw_item.get('chave') or '').lower()}@load.invalid"),
                register_missing=bool(raw_item.get("register_missing", True)),
            )
        )
    return identities


def load_phase10_harness_config(config_path: str | Path) -> Phase10HarnessConfig:
    resolved_path = Path(config_path).resolve()
    raw_payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("Phase 10 harness config must be a JSON object")

    wait_time_payload = raw_payload.get("wait_time") or {}
    location_payload = raw_payload.get("location") or {}
    web_check_payload = raw_payload.get("web_check") or {}
    admin_payload = raw_payload.get("admin")
    transport_payload = raw_payload.get("transport")
    forms_backlog_payload = raw_payload.get("forms_backlog") or {}

    identities: list[Phase10Identity] = []
    if isinstance(raw_payload.get("identities"), list):
        identities.extend(_load_explicit_identities(raw_payload["identities"]))

    generated_payload = raw_payload.get("generated_users")
    if generated_payload is not None:
        if not isinstance(generated_payload, dict):
            raise ValueError("generated_users must be a JSON object")
        identities.extend(
            generate_identities(
                GeneratedIdentityConfig(
                    prefix=str(generated_payload.get("prefix") or "L"),
                    count=int(generated_payload.get("count") or 0),
                    start_index=int(generated_payload.get("start_index") or 1),
                    password=str(generated_payload.get("password") or "abc123"),
                    project=str(generated_payload.get("project") or "P80"),
                    register_missing=bool(generated_payload.get("register_missing", True)),
                    name_prefix=str(generated_payload.get("name_prefix") or "Phase10 Load"),
                    email_domain=str(generated_payload.get("email_domain") or "load.invalid"),
                )
            )
        )

    if not identities:
        raise ValueError("The Phase 10 harness config must define identities or generated_users")

    deduplicated: dict[str, Phase10Identity] = {}
    for identity in identities:
        deduplicated[identity.chave] = identity

    return Phase10HarnessConfig(
        wait_time=WaitTimeConfig(
            min_seconds=float(wait_time_payload.get("min_seconds", 0.2)),
            max_seconds=float(wait_time_payload.get("max_seconds", 0.7)),
        ),
        location=LocationConfig(
            latitude=float(location_payload.get("latitude")),
            longitude=float(location_payload.get("longitude")),
            accuracy_meters=float(location_payload.get("accuracy_meters", 8.0)),
            fallback_local=str(location_payload.get("fallback_local", "Escritório Principal")),
        ),
        web_check=WebCheckScenarioConfig(
            page_path=str(web_check_payload.get("page_path", "/checking/user")),
            projects_path=str(web_check_payload.get("projects_path", "/api/web/projects")),
            auth_status_path=str(web_check_payload.get("auth_status_path", "/api/web/auth/status")),
            auth_register_user_path=str(web_check_payload.get("auth_register_user_path", "/api/web/auth/register-user")),
            auth_login_path=str(web_check_payload.get("auth_login_path", "/api/web/auth/login")),
            check_state_path=str(web_check_payload.get("check_state_path", "/api/web/check/state")),
            check_locations_path=str(web_check_payload.get("check_locations_path", "/api/web/check/locations")),
            check_location_match_path=str(web_check_payload.get("check_location_match_path", "/api/web/check/location")),
            check_submit_path=str(web_check_payload.get("check_submit_path", "/api/web/check")),
            include_page_open=bool(web_check_payload.get("include_page_open", True)),
            include_project_catalog=bool(web_check_payload.get("include_project_catalog", True)),
            include_location_resolution=bool(web_check_payload.get("include_location_resolution", True)),
            include_location_options=bool(web_check_payload.get("include_location_options", True)),
            action_cycle=tuple(web_check_payload.get("action_cycle", ["checkin", "checkout"])),
            informe=str(web_check_payload.get("informe", "normal")),
        ),
        identities=tuple(deduplicated.values()),
        admin=(
            AdminScenarioConfig(
                credentials=OperatorCredentials(
                    chave=str(admin_payload.get("chave") or ""),
                    senha=str(admin_payload.get("senha") or ""),
                ),
                login_path=str(admin_payload.get("login_path", "/api/admin/auth/login")),
                session_path=str(admin_payload.get("session_path", "/api/admin/auth/session")),
                projects_path=str(admin_payload.get("projects_path", "/api/admin/projects")),
                forms_queue_diagnostics_path=str(admin_payload.get("forms_queue_diagnostics_path", "/api/admin/forms/queue/diagnostics")),
                database_diagnostics_path=str(admin_payload.get("database_diagnostics_path", "/api/admin/diagnostics/database")),
            )
            if isinstance(admin_payload, dict)
            else None
        ),
        transport=(
            TransportScenarioConfig(
                credentials=OperatorCredentials(
                    chave=str(transport_payload.get("chave") or ""),
                    senha=str(transport_payload.get("senha") or ""),
                ),
                verify_path=str(transport_payload.get("verify_path", "/api/transport/auth/verify")),
                session_path=str(transport_payload.get("session_path", "/api/transport/auth/session")),
                dashboard_path=str(transport_payload.get("dashboard_path", "/api/transport/dashboard")),
                projects_path=str(transport_payload.get("projects_path", "/api/transport/projects")),
                route_kind=str(transport_payload.get("route_kind", "home_to_work")),
            )
            if isinstance(transport_payload, dict)
            else None
        ),
        forms_backlog=FormsBacklogScenarioConfig(
            ready_path=str(forms_backlog_payload.get("ready_path", "/api/health/ready")),
            producer_action_cycle=tuple(forms_backlog_payload.get("producer_action_cycle", ["checkin", "checkout"])),
        ),
    )


class IdentityPool:
    def __init__(self, identities: tuple[Phase10Identity, ...]) -> None:
        if not identities:
            raise ValueError("IdentityPool requires at least one identity")
        self._identities = identities
        self._lock = threading.Lock()
        self._cursor = 0

    def checkout(self) -> Phase10Identity:
        with self._lock:
            identity = self._identities[self._cursor % len(self._identities)]
            self._cursor += 1
            return identity


def build_web_registration_payload(identity: Phase10Identity) -> dict[str, str]:
    return {
        "chave": identity.chave,
        "nome": identity.nome,
        "projeto": identity.projeto,
        "email": identity.email,
        "senha": identity.senha,
        "confirmar_senha": identity.senha,
    }


def build_web_login_payload(identity: Phase10Identity) -> dict[str, str]:
    return {
        "chave": identity.chave,
        "senha": identity.senha,
    }


def build_web_location_payload(location: LocationConfig) -> dict[str, float]:
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy_meters": location.accuracy_meters,
    }


def build_web_submit_payload(
    identity: Phase10Identity,
    *,
    action: str,
    informe: str,
    local: str,
) -> dict[str, str]:
    return {
        "chave": identity.chave,
        "projeto": identity.projeto,
        "action": action,
        "local": local,
        "informe": informe,
        "event_time": datetime.now(timezone.utc).isoformat(),
        "client_event_id": f"phase10-{identity.chave.lower()}-{uuid.uuid4().hex[:20]}",
    }