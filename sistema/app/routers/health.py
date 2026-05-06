from pathlib import Path

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from ..core.config import normalize_transport_ai_agent_mode, settings
from ..database import SessionLocal
from ..schemas import HealthComponentResponse, HealthLivenessResponse, HealthResponse
from ..services.forms_queue import get_forms_worker_health_failure_reason, get_forms_worker_observed_snapshot
from ..services.transport_ai_llm_settings import (
    TransportAILlmSettingsEncryptionError,
    validate_transport_ai_settings_encryption_availability,
)
from ..services.transport_ai_runtime import get_transport_ai_operational_readiness_issues

router = APIRouter(prefix="/api", tags=["health"])
_HEALTH_DETAIL_MAX_LENGTH = 200
_STATIC_SITE_REQUIREMENTS = (
    ("admin", "serve_admin_site_in_api", "admin"),
    ("user", "serve_user_site_in_api", "check"),
    ("transport", "serve_transport_site_in_api", "transport"),
)


def _truncate_health_detail(detail: str) -> str:
    normalized = " ".join(str(detail).strip().split())
    return normalized[:_HEALTH_DETAIL_MAX_LENGTH]


def _build_database_component() -> HealthComponentResponse:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar_one()
        return HealthComponentResponse(status="ok", detail="database reachable")
    except Exception as exc:
        return HealthComponentResponse(
            status="failed",
            detail=_truncate_health_detail(f"database unavailable: {exc}"),
        )


def _build_static_sites_component() -> HealthComponentResponse:
    static_dir = Path(__file__).resolve().parents[1] / "static"
    enabled_sites: list[str] = []
    missing_sites: list[str] = []

    for site_name, flag_name, directory_name in _STATIC_SITE_REQUIREMENTS:
        if not bool(getattr(settings, flag_name, True)):
            continue
        enabled_sites.append(site_name)
        if not (static_dir / directory_name).exists():
            missing_sites.append(site_name)

    if missing_sites:
        return HealthComponentResponse(
            status="failed",
            detail=f"missing static sites: {', '.join(missing_sites)}",
        )
    if not enabled_sites:
        return HealthComponentResponse(status="disabled", detail="all API static sites disabled by configuration")
    return HealthComponentResponse(
        status="ok",
        detail=f"static sites ready: {', '.join(enabled_sites)}",
    )


def _build_forms_worker_component() -> HealthComponentResponse:
    try:
        snapshot = get_forms_worker_observed_snapshot()
        failure_reason = get_forms_worker_health_failure_reason(snapshot)
    except Exception as exc:
        return HealthComponentResponse(
            status="unknown",
            detail=_truncate_health_detail(f"forms worker health unavailable: {exc}"),
        )

    if not bool(snapshot.get("enabled")):
        return HealthComponentResponse(status="disabled", detail="forms worker disabled")
    if failure_reason is not None:
        return HealthComponentResponse(status="degraded", detail=_truncate_health_detail(failure_reason))
    return HealthComponentResponse(status="ok", detail="forms worker healthy")


def _build_transport_ai_settings_encryption_component() -> HealthComponentResponse:
    if not bool(settings.transport_ai_enabled):
        return HealthComponentResponse(status="disabled", detail="transport ai disabled")

    agent_mode = normalize_transport_ai_agent_mode(settings.transport_ai_agent_mode)
    if agent_mode is None:
        return HealthComponentResponse(
            status="failed",
            detail=_truncate_health_detail(
                f"unsupported transport ai agent mode: {settings.transport_ai_agent_mode}"
            ),
        )
    if agent_mode != "agent":
        return HealthComponentResponse(
            status="disabled",
            detail=f"transport ai settings encryption not required in {agent_mode} mode",
        )

    try:
        validate_transport_ai_settings_encryption_availability()
    except TransportAILlmSettingsEncryptionError as exc:
        return HealthComponentResponse(
            status="failed",
            detail=_truncate_health_detail(str(exc)),
        )

    return HealthComponentResponse(status="ok", detail="transport ai settings encryption ready")


def _build_transport_ai_operational_readiness_component() -> HealthComponentResponse:
    if not bool(settings.transport_ai_enabled):
        return HealthComponentResponse(status="disabled", detail="transport ai disabled")

    issues = get_transport_ai_operational_readiness_issues(settings_obj=settings)
    if issues:
        issue_codes = ", ".join(issue.code for issue in issues)
        return HealthComponentResponse(
            status="failed",
            detail=_truncate_health_detail(f"transport ai operational readiness blocked: {issue_codes}"),
        )

    return HealthComponentResponse(status="ok", detail="transport ai operational readiness approved")


def _build_health_components(*, include_forms_worker: bool) -> dict[str, HealthComponentResponse]:
    components = {
        "database": _build_database_component(),
        "static_sites": _build_static_sites_component(),
        "transport_ai_operational_readiness": _build_transport_ai_operational_readiness_component(),
        "transport_ai_settings_encryption": _build_transport_ai_settings_encryption_component(),
    }
    if include_forms_worker:
        components["forms_worker"] = _build_forms_worker_component()
    return components


def _is_ready(components: dict[str, HealthComponentResponse]) -> bool:
    return (
        components["database"].status == "ok"
        and components["static_sites"].status in {"ok", "disabled"}
        and components["transport_ai_operational_readiness"].status in {"ok", "disabled"}
        and components["transport_ai_settings_encryption"].status in {"ok", "disabled"}
    )


def _build_health_response(*, include_forms_worker: bool) -> HealthResponse:
    components = _build_health_components(include_forms_worker=include_forms_worker)
    ready = _is_ready(components)

    overall_status = "unready"
    if ready:
        overall_status = "degraded" if any(
            component.status in {"degraded", "unknown"}
            for component_name, component in components.items()
            if component_name not in {"database", "static_sites"}
        ) else "ok"

    return HealthResponse(
        status="ok" if ready else "unready",
        app=settings.app_name,
        ready=ready,
        overall_status=overall_status,
        components=components,
    )


@router.get("/health/live", response_model=HealthLivenessResponse)
def health_live() -> HealthLivenessResponse:
    return HealthLivenessResponse(status="ok", app=settings.app_name)


@router.get("/health/ready", response_model=HealthResponse)
def health_ready(response: Response) -> HealthResponse:
    payload = _build_health_response(include_forms_worker=False)
    if not payload.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    payload = _build_health_response(include_forms_worker=True)
    if not payload.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
