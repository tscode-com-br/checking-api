from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import Settings, normalize_transport_ai_agent_mode, settings
from ..models import TransportAIRun
from ..schemas import (
    TransportAgentPlanningInput,
    TransportAgentProjectLlmRuntimeSnapshot,
    TransportAIPreflightCheckResult,
    TransportAIPreflightIssue,
)
from .location_settings import get_transport_pricing_settings
from .transport_ai_llm_settings import (
    TransportAILlmRuntimeSettings,
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsProjectNotFoundError,
    TransportAILlmSettingsValidationError,
    get_supported_transport_ai_llm_providers,
    resolve_transport_ai_llm_runtime_settings,
    validate_transport_ai_settings_encryption_availability,
)


_TRANSPORT_AI_ACTIVE_RUN_STATUSES = (
    "requested",
    "baseline_saved",
    "passengers_reset",
    "running",
)


def _build_transport_ai_preflight_issue(
    *,
    code: str,
    message: str,
    setting_name: str | None = None,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return TransportAIPreflightIssue(
        code=code,
        message=message,
        blocking=blocking,
        setting_name=setting_name,
    )


@dataclass(frozen=True, slots=True)
class TransportAIProjectLlmRuntimeContext:
    project_id: int
    project_name: str
    partition_keys: tuple[str, ...]
    runtime_settings: TransportAILlmRuntimeSettings


def _collect_transport_ai_planning_projects(
    planning_input: TransportAgentPlanningInput,
) -> list[tuple[int, str, tuple[str, ...]]]:
    project_rows_by_id: dict[int, tuple[str, list[str]]] = {}

    for partition in planning_input.partitions:
        project_name, partition_keys = project_rows_by_id.setdefault(
            int(partition.project_id),
            (partition.project_name, []),
        )
        if project_name != partition.project_name:
            project_name = partition.project_name
        partition_keys.append(partition.partition_key)
        project_rows_by_id[int(partition.project_id)] = (project_name, partition_keys)

    return [
        (
            project_id,
            project_rows_by_id[project_id][0],
            tuple(sorted(set(project_rows_by_id[project_id][1]))),
        )
        for project_id in sorted(project_rows_by_id)
    ]


def resolve_transport_ai_project_llm_runtime_contexts(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> list[TransportAIProjectLlmRuntimeContext]:
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext] = []

    for project_id, project_name, partition_keys in _collect_transport_ai_planning_projects(planning_input):
        runtime_settings = resolve_transport_ai_llm_runtime_settings(
            db,
            project_id=project_id,
            settings_obj=settings_obj,
        )
        resolved_contexts.append(
            TransportAIProjectLlmRuntimeContext(
                project_id=project_id,
                project_name=project_name,
                partition_keys=partition_keys,
                runtime_settings=runtime_settings,
            )
        )

    return resolved_contexts


def build_transport_ai_project_llm_runtime_snapshots(
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext],
) -> list[TransportAgentProjectLlmRuntimeSnapshot]:
    return [
        TransportAgentProjectLlmRuntimeSnapshot(
            project_id=context.project_id,
            project_name=context.project_name,
            partition_keys=list(context.partition_keys),
            provider=context.runtime_settings.provider,
            model_name=context.runtime_settings.model_name,
            reasoning_effort=context.runtime_settings.reasoning_effort,
        )
        for context in resolved_contexts
    ]


def resolve_transport_ai_shared_llm_runtime_context(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> tuple[TransportAILlmRuntimeSettings, list[TransportAgentProjectLlmRuntimeSnapshot]]:
    resolved_contexts = resolve_transport_ai_project_llm_runtime_contexts(
        db,
        planning_input=planning_input,
        settings_obj=settings_obj,
    )
    if not resolved_contexts:
        raise TransportAILlmSettingsValidationError(
            "Transport AI planning input does not reference any eligible project partitions."
        )

    first_runtime_settings = resolved_contexts[0].runtime_settings
    conflicting_project_names = sorted(
        {
            context.project_name
            for context in resolved_contexts
            if context.runtime_settings != first_runtime_settings
        }
    )
    if conflicting_project_names:
        project_names = ", ".join(conflicting_project_names)
        raise TransportAILlmSettingsValidationError(
            "Transport AI agent mode currently requires the same project-specific LLM provider, model, "
            f"reasoning effort, and API key across all referenced projects in a single run. Conflicting projects: {project_names}."
        )

    return first_runtime_settings, build_transport_ai_project_llm_runtime_snapshots(resolved_contexts)


def _build_transport_ai_project_runtime_issue(
    *,
    code: str,
    message: str,
    setting_name: str,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name=setting_name,
    )


def _build_transport_ai_project_runtime_preflight_issues(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings,
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext] = []

    for project_id, project_name, partition_keys in _collect_transport_ai_planning_projects(planning_input):
        try:
            runtime_settings = resolve_transport_ai_llm_runtime_settings(
                db,
                project_id=project_id,
                settings_obj=settings_obj,
            )
        except TransportAILlmSettingsProjectNotFoundError:
            issues.append(
                _build_transport_ai_project_runtime_issue(
                    code="transport_ai_llm_project_missing",
                    message=(
                        f"Transport AI project '{project_name}' is no longer available for runtime resolution."
                    ),
                    setting_name="transport_ai_llm_settings",
                )
            )
            continue
        except TransportAILlmSettingsEncryptionError:
            issues.append(
                _build_transport_ai_project_runtime_issue(
                    code="transport_ai_llm_api_key_missing",
                    message=(
                        f"Transport AI API key for project '{project_name}' is missing or could not be decrypted."
                    ),
                    setting_name="transport_ai_llm_api_key",
                )
            )
            continue
        except TransportAILlmSettingsValidationError as exc:
            normalized_message = str(exc).strip()
            normalized_message_lower = normalized_message.lower()
            if "api key" in normalized_message_lower:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_api_key_missing",
                        message=(
                            f"Transport AI API key has not been configured for project '{project_name}' yet."
                        ),
                        setting_name="transport_ai_llm_api_key",
                    )
                )
            elif "provider" in normalized_message_lower and "supported" in normalized_message_lower:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_provider_invalid",
                        message=(
                            f"The configured Transport AI LLM provider for project '{project_name}' is not supported."
                        ),
                        setting_name="transport_ai_llm_provider",
                    )
                )
            else:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_settings_missing",
                        message=(
                            f"Transport AI LLM settings have not been configured for project '{project_name}' yet."
                        ),
                        setting_name="transport_ai_llm_settings",
                    )
                )
            continue

        resolved_contexts.append(
            TransportAIProjectLlmRuntimeContext(
                project_id=project_id,
                project_name=project_name,
                partition_keys=partition_keys,
                runtime_settings=runtime_settings,
            )
        )

    if issues:
        return issues

    if not resolved_contexts:
        return issues

    first_runtime_settings = resolved_contexts[0].runtime_settings
    conflicting_project_names = sorted(
        {
            context.project_name
            for context in resolved_contexts
            if context.runtime_settings != first_runtime_settings
        }
    )
    if conflicting_project_names:
        issues.append(
            _build_transport_ai_project_runtime_issue(
                code="transport_ai_llm_runtime_conflict",
                message=(
                    "Transport AI agent mode currently requires the same project-specific LLM provider, model, "
                    "reasoning effort, and API key across all referenced projects in a single run. "
                    f"Conflicting projects: {', '.join(conflicting_project_names)}."
                ),
                setting_name="transport_ai_llm_settings",
            )
        )

    return issues


def get_transport_ai_operational_readiness_issues(
    *,
    settings_obj: Settings = settings,
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []

    if not str(settings_obj.transport_ai_operational_approval_evidence or "").strip():
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_operational_approval_missing",
                message=(
                    "Transport AI requires explicit operational approval evidence covering resource approval "
                    "and dedicated load validation before new runs can start."
                ),
                setting_name="transport_ai_operational_approval_evidence",
            )
        )

    if settings_obj.transport_ai_max_concurrent_runs <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_concurrent_runs_invalid",
                message="The maximum concurrent Transport AI runs must be greater than zero.",
                setting_name="transport_ai_max_concurrent_runs",
            )
        )

    if settings_obj.transport_ai_max_runtime_seconds <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_runtime_seconds_invalid",
                message="The maximum Transport AI runtime must be greater than zero seconds.",
                setting_name="transport_ai_max_runtime_seconds",
            )
        )

    return issues


def count_transport_ai_active_runs(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(TransportAIRun.id)).where(TransportAIRun.status.in_(_TRANSPORT_AI_ACTIVE_RUN_STATUSES))
        ).scalar_one()
        or 0
    )


def build_transport_ai_concurrency_limit_issue(
    *,
    active_run_count: int,
    settings_obj: Settings = settings,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code="transport_ai_concurrency_limit_reached",
        message=(
            f"Transport AI already has {active_run_count} active run(s), which meets the configured "
            f"limit of {settings_obj.transport_ai_max_concurrent_runs}."
        ),
        setting_name="transport_ai_max_concurrent_runs",
    )


def validate_transport_ai_runtime_configuration(
    db: Session,
    *,
    settings_obj: Settings = settings,
    planning_input: TransportAgentPlanningInput | None = None,
) -> TransportAIPreflightCheckResult:
    issues: list[TransportAIPreflightIssue] = []

    if not bool(settings_obj.transport_ai_enabled):
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_disabled",
                message="Transport AI is disabled in the server configuration.",
                setting_name="transport_ai_enabled",
            )
        )
        return TransportAIPreflightCheckResult(ok=False, issues=issues)

    agent_mode = normalize_transport_ai_agent_mode(settings_obj.transport_ai_agent_mode)
    if agent_mode is None:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_agent_mode_invalid",
                message="Transport AI agent mode must be 'agent' or 'deterministic'.",
                setting_name="transport_ai_agent_mode",
            )
        )
    elif agent_mode == "agent":
        settings_encryption_available = True
        try:
            validate_transport_ai_settings_encryption_availability(settings_obj=settings_obj)
        except TransportAILlmSettingsEncryptionError:
            settings_encryption_available = False
            issues.append(
                _build_transport_ai_preflight_issue(
                    code="transport_ai_settings_encryption_unavailable",
                    message="Transport AI settings encryption key is missing or invalid in the server configuration.",
                    setting_name="transport_ai_settings_encryption_key",
                )
            )

        if planning_input is not None and settings_encryption_available:
            issues.extend(
                _build_transport_ai_project_runtime_preflight_issues(
                    db,
                    planning_input=planning_input,
                    settings_obj=settings_obj,
                )
            )

    if not str(settings_obj.mapbox_access_token or "").strip():
        issues.append(
            _build_transport_ai_preflight_issue(
                code="mapbox_access_token_missing",
                message="The Mapbox access token is not configured.",
                setting_name="mapbox_access_token",
            )
        )

    pricing_settings = get_transport_pricing_settings(db)
    configured_prices = (
        pricing_settings["default_car_price"],
        pricing_settings["default_minivan_price"],
        pricing_settings["default_van_price"],
        pricing_settings["default_bus_price"],
    )
    if all(price is None for price in configured_prices):
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_pricing_missing",
                message="At least one transport vehicle price must be configured before running Transport AI.",
                setting_name="transport_pricing",
            )
        )

    issues.extend(get_transport_ai_operational_readiness_issues(settings_obj=settings_obj))

    if settings_obj.transport_ai_max_passengers_per_run <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_passengers_per_run_invalid",
                message="The maximum passengers per Transport AI run must be greater than zero.",
                setting_name="transport_ai_max_passengers_per_run",
            )
        )

    return TransportAIPreflightCheckResult(
        ok=not any(issue.blocking for issue in issues),
        issues=issues,
    )