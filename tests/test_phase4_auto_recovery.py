from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path


def _load_auto_recovery_module():
    module_path = Path(__file__).resolve().parents[1] / "deploy" / "maintenance" / "checkcheck_auto_recovery.py"
    spec = importlib.util.spec_from_file_location("checkcheck_auto_recovery", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


auto_recovery = _load_auto_recovery_module()


def _healthy_service(name: str, *, configured: bool = True):
    return auto_recovery.ServiceObservation(
        service_name=name,
        configured=configured,
        container_id=f"{name}-id" if configured else None,
        container_name=name if configured else None,
        state_status="running" if configured else "missing",
        health_status="healthy" if configured else "missing",
        restart_count=0,
        oom_killed=False,
        running=configured,
    )


def _unhealthy_service(name: str):
    return auto_recovery.ServiceObservation(
        service_name=name,
        configured=True,
        container_id=f"{name}-id",
        container_name=name,
        state_status="running",
        health_status="unhealthy",
        restart_count=0,
        oom_killed=False,
        running=True,
    )


def _probe(*, ok: bool, status_code: int | None = 200):
    return auto_recovery.ProbeResult(
        url="http://127.0.0.1:8000/api/health/ready",
        ok=ok,
        status_code=status_code,
        raw_body="{}",
        json_body={},
        error=None,
    )


def _observation(*, api, db, forms_worker, api_ready_ok: bool):
    return auto_recovery.RuntimeObservation(
        api=api,
        db=db,
        forms_worker=forms_worker,
        api_ready=_probe(ok=api_ready_ok, status_code=200 if api_ready_ok else 503),
        api_summary=_probe(ok=api_ready_ok, status_code=200 if api_ready_ok else 503),
        observed_at="2026-05-05T12:00:00Z",
    )


def test_restart_forms_worker_after_sustained_worker_unhealthy_with_api_ready():
    config = auto_recovery.RecoveryConfig(worker_unhealthy_threshold=3)
    state = auto_recovery.RecoveryState(
        forms_worker=auto_recovery.ServiceRecoveryState(consecutive_unhealthy=3),
    )
    observation = _observation(
        api=_healthy_service("app"),
        db=_healthy_service("db"),
        forms_worker=_unhealthy_service("forms-worker"),
        api_ready_ok=True,
    )

    decision = auto_recovery.decide_auto_recovery(observation, state, config)

    assert decision.action == "restart_forms_worker"
    assert decision.target_service == "forms-worker"
    assert "API readiness stayed healthy" in decision.reason


def test_restart_api_only_when_database_is_healthy_and_worker_is_not_unhealthy():
    config = auto_recovery.RecoveryConfig(api_unhealthy_threshold=3)
    state = auto_recovery.RecoveryState(
        api=auto_recovery.ServiceRecoveryState(consecutive_unhealthy=3),
    )
    observation = _observation(
        api=_unhealthy_service("app"),
        db=_healthy_service("db"),
        forms_worker=_healthy_service("forms-worker"),
        api_ready_ok=False,
    )

    decision = auto_recovery.decide_auto_recovery(observation, state, config)

    assert decision.action == "restart_api"
    assert decision.target_service == "app"
    assert "database stayed healthy" in decision.reason


def test_collect_evidence_instead_of_restart_when_database_is_unhealthy():
    config = auto_recovery.RecoveryConfig(api_unhealthy_threshold=3)
    state = auto_recovery.RecoveryState(
        api=auto_recovery.ServiceRecoveryState(consecutive_unhealthy=3),
    )
    observation = _observation(
        api=_unhealthy_service("app"),
        db=_unhealthy_service("db"),
        forms_worker=_healthy_service("forms-worker"),
        api_ready_ok=False,
    )

    decision = auto_recovery.decide_auto_recovery(observation, state, config)

    assert decision.action == "collect_evidence"
    assert "database unhealthy" in decision.reason


def test_collect_evidence_when_forms_worker_restart_budget_is_exhausted():
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    config = auto_recovery.RecoveryConfig(
        worker_unhealthy_threshold=3,
        worker_max_restarts_per_window=2,
        worker_restart_window_seconds=3600,
    )
    state = auto_recovery.RecoveryState(
        forms_worker=auto_recovery.ServiceRecoveryState(
            consecutive_unhealthy=3,
            restart_timestamps=[
                auto_recovery.isoformat_utc(now),
                auto_recovery.isoformat_utc(now),
            ],
        )
    )
    observation = _observation(
        api=_healthy_service("app"),
        db=_healthy_service("db"),
        forms_worker=_unhealthy_service("forms-worker"),
        api_ready_ok=True,
    )

    auto_recovery.apply_observation_to_state(state, observation, config, now=now)
    decision = auto_recovery.decide_auto_recovery(observation, state, config)

    assert decision.action == "collect_evidence"
    assert "forms worker exhausted" in decision.reason


def test_collect_evidence_when_api_and_worker_fail_together():
    config = auto_recovery.RecoveryConfig(api_unhealthy_threshold=3, worker_unhealthy_threshold=3)
    state = auto_recovery.RecoveryState(
        api=auto_recovery.ServiceRecoveryState(consecutive_unhealthy=3),
        forms_worker=auto_recovery.ServiceRecoveryState(consecutive_unhealthy=3),
    )
    observation = _observation(
        api=_unhealthy_service("app"),
        db=_healthy_service("db"),
        forms_worker=_unhealthy_service("forms-worker"),
        api_ready_ok=False,
    )

    decision = auto_recovery.decide_auto_recovery(observation, state, config)

    assert decision.action == "collect_evidence"
    assert "unhealthy together" in decision.reason