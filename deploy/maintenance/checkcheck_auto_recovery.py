#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal


DecisionAction = Literal["noop", "restart_api", "restart_forms_worker", "collect_evidence"]


@dataclass
class ServiceObservation:
    service_name: str
    configured: bool
    container_id: str | None = None
    container_name: str | None = None
    state_status: str = "missing"
    health_status: str = "missing"
    restart_count: int = 0
    oom_killed: bool = False
    running: bool = False


@dataclass
class ProbeResult:
    url: str | None
    ok: bool
    status_code: int | None = None
    raw_body: str | None = None
    json_body: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class RuntimeObservation:
    api: ServiceObservation
    db: ServiceObservation
    forms_worker: ServiceObservation
    api_ready: ProbeResult
    api_summary: ProbeResult
    observed_at: str


@dataclass
class ServiceRecoveryState:
    consecutive_unhealthy: int = 0
    restart_timestamps: list[str] = field(default_factory=list)
    last_action: str | None = None
    last_reason: str | None = None


@dataclass
class RecoveryState:
    api: ServiceRecoveryState = field(default_factory=ServiceRecoveryState)
    forms_worker: ServiceRecoveryState = field(default_factory=ServiceRecoveryState)
    last_decision: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    api_unhealthy_threshold: int = 3
    worker_unhealthy_threshold: int = 3
    api_restart_window_seconds: int = 5400
    worker_restart_window_seconds: int = 3600
    api_max_restarts_per_window: int = 1
    worker_max_restarts_per_window: int = 2
    max_container_restart_count_before_manual: int = 2
    health_probe_timeout_seconds: float = 5.0
    logs_tail_lines: int = 200


@dataclass
class RecoveryDecision:
    action: DecisionAction
    reason: str
    target_service: str | None = None


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def service_hard_unhealthy(service: ServiceObservation) -> bool:
    if not service.configured:
        return False
    if service.oom_killed:
        return True
    if service.health_status == "starting":
        return False
    if service.health_status == "unhealthy":
        return True
    if service.state_status in {"missing", "dead", "exited", "restarting"}:
        return True
    return not service.running


def api_unhealthy(observation: RuntimeObservation) -> bool:
    api = observation.api
    if api.oom_killed:
        return True
    if api.health_status == "starting":
        return False
    if api.health_status == "unhealthy":
        return True
    if api.state_status in {"missing", "dead", "exited", "restarting"}:
        return True
    if observation.api_ready.ok is False:
        return True
    return not api.running


def worker_unhealthy(observation: RuntimeObservation) -> bool:
    worker = observation.forms_worker
    if not worker.configured:
        return False
    if worker.health_status == "starting":
        return False
    return service_hard_unhealthy(worker)


def prune_restart_timestamps(timestamps: list[str], *, now: datetime, window_seconds: int) -> list[str]:
    cutoff = now - timedelta(seconds=window_seconds)
    kept: list[str] = []
    for timestamp in timestamps:
        try:
            parsed = parse_utc(timestamp)
        except ValueError:
            continue
        if parsed >= cutoff:
            kept.append(isoformat_utc(parsed))
    return kept


def apply_observation_to_state(
    state: RecoveryState,
    observation: RuntimeObservation,
    config: RecoveryConfig,
    *,
    now: datetime,
) -> RecoveryState:
    state.api.restart_timestamps = prune_restart_timestamps(
        state.api.restart_timestamps,
        now=now,
        window_seconds=config.api_restart_window_seconds,
    )
    state.forms_worker.restart_timestamps = prune_restart_timestamps(
        state.forms_worker.restart_timestamps,
        now=now,
        window_seconds=config.worker_restart_window_seconds,
    )
    state.api.consecutive_unhealthy = state.api.consecutive_unhealthy + 1 if api_unhealthy(observation) else 0
    state.forms_worker.consecutive_unhealthy = (
        state.forms_worker.consecutive_unhealthy + 1 if worker_unhealthy(observation) else 0
    )
    return state


def restart_budget_exhausted(timestamps: list[str], *, max_restarts: int) -> bool:
    return len(timestamps) >= max_restarts


def decide_auto_recovery(
    observation: RuntimeObservation,
    state: RecoveryState,
    config: RecoveryConfig,
) -> RecoveryDecision:
    if service_hard_unhealthy(observation.db):
        return RecoveryDecision(
            action="collect_evidence",
            reason="database unhealthy or unavailable; stop before any broader restart",
        )

    if observation.api.oom_killed:
        return RecoveryDecision(
            action="collect_evidence",
            reason="API container hit OOMKilled; collect evidence before another restart",
        )

    if observation.forms_worker.oom_killed:
        return RecoveryDecision(
            action="collect_evidence",
            reason="forms worker hit OOMKilled; collect evidence before another restart",
        )

    api_is_unhealthy = api_unhealthy(observation)
    worker_is_unhealthy = worker_unhealthy(observation)

    if api_is_unhealthy and worker_is_unhealthy:
        return RecoveryDecision(
            action="collect_evidence",
            reason="API and forms worker are unhealthy together; do not guess which side to restart first",
        )

    if worker_is_unhealthy and state.forms_worker.consecutive_unhealthy >= config.worker_unhealthy_threshold:
        if observation.api_ready.ok is False:
            return RecoveryDecision(
                action="collect_evidence",
                reason="forms worker is unhealthy but API readiness is also failing; collect evidence instead of restarting only the worker",
            )
        if observation.forms_worker.restart_count >= config.max_container_restart_count_before_manual:
            return RecoveryDecision(
                action="collect_evidence",
                reason="forms worker already looks like a container restart loop; stop for evidence",
            )
        if restart_budget_exhausted(
            state.forms_worker.restart_timestamps,
            max_restarts=config.worker_max_restarts_per_window,
        ):
            return RecoveryDecision(
                action="collect_evidence",
                reason="forms worker exhausted the automatic restart budget for the current window",
            )
        return RecoveryDecision(
            action="restart_forms_worker",
            target_service=observation.forms_worker.service_name,
            reason="forms worker unhealthy across consecutive probes while API readiness stayed healthy",
        )

    if api_is_unhealthy and state.api.consecutive_unhealthy >= config.api_unhealthy_threshold:
        if observation.api.restart_count >= config.max_container_restart_count_before_manual:
            return RecoveryDecision(
                action="collect_evidence",
                reason="API container already looks like a restart loop; stop for evidence",
            )
        if restart_budget_exhausted(
            state.api.restart_timestamps,
            max_restarts=config.api_max_restarts_per_window,
        ):
            return RecoveryDecision(
                action="collect_evidence",
                reason="API exhausted the automatic restart budget for the current window",
            )
        return RecoveryDecision(
            action="restart_api",
            target_service=observation.api.service_name,
            reason="API readiness failed across consecutive probes while database stayed healthy",
        )

    return RecoveryDecision(action="noop", reason="no sustained unhealthy state crossed the automatic remediation threshold")


def load_state(path: Path) -> RecoveryState:
    if not path.exists():
        return RecoveryState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RecoveryState()

    api_payload = payload.get("api") if isinstance(payload, dict) else None
    worker_payload = payload.get("forms_worker") if isinstance(payload, dict) else None
    return RecoveryState(
        api=ServiceRecoveryState(**api_payload) if isinstance(api_payload, dict) else ServiceRecoveryState(),
        forms_worker=(
            ServiceRecoveryState(**worker_payload) if isinstance(worker_payload, dict) else ServiceRecoveryState()
        ),
        last_decision=payload.get("last_decision", {}) if isinstance(payload, dict) else {},
    )


def save_state(path: Path, state: RecoveryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )


def choose_compose_command() -> list[str]:
    docker_compose = run_command(["docker", "compose", "version"], timeout_seconds=10.0)
    if docker_compose.returncode == 0:
        return ["docker", "compose"]
    legacy = run_command(["docker-compose", "version"], timeout_seconds=10.0)
    if legacy.returncode == 0:
        return ["docker-compose"]
    raise RuntimeError("Neither docker compose nor docker-compose is available")


def detect_stack_dir() -> Path:
    candidate_names = [
        "checkcheck-app-1",
        "checkcheck-api-1",
        "checkcheck-db-1",
        "checkcheck-forms-worker-1",
    ]
    for candidate_name in candidate_names:
        result = run_command(
            [
                "docker",
                "inspect",
                "--format",
                "{{ index .Config.Labels \"com.docker.compose.project.working_dir\" }}",
                candidate_name,
            ],
            timeout_seconds=10.0,
        )
        if result.returncode != 0:
            continue
        candidate = result.stdout.strip()
        if candidate:
            path = Path(candidate)
            if path.is_dir():
                return path
    raise RuntimeError("Could not detect the docker compose working directory automatically")


def resolve_compose_file(stack_dir: Path, requested: str | None) -> Path:
    if requested:
        compose_path = Path(requested)
        if not compose_path.is_absolute():
            compose_path = stack_dir / compose_path
        if compose_path.is_file():
            return compose_path
        raise RuntimeError(f"Compose file not found: {compose_path}")

    default_compose = stack_dir / "docker-compose.yml"
    if default_compose.is_file():
        return default_compose

    api_only_compose = stack_dir / "docker-compose.api.yml"
    if api_only_compose.is_file():
        return api_only_compose

    raise RuntimeError("Could not resolve a compose file automatically")


def compose_command(compose_cmd: list[str], compose_file: Path, *args: str) -> list[str]:
    return [*compose_cmd, "-f", str(compose_file), *args]


def list_services(compose_cmd: list[str], stack_dir: Path, compose_file: Path) -> list[str]:
    result = run_command(compose_command(compose_cmd, compose_file, "config", "--services"), cwd=stack_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Could not list compose services: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def inspect_service(
    compose_cmd: list[str],
    stack_dir: Path,
    compose_file: Path,
    service_name: str,
    *,
    configured: bool,
) -> tuple[ServiceObservation, dict[str, Any] | None]:
    if not configured:
        return ServiceObservation(service_name=service_name, configured=False), None

    container_id_result = run_command(
        compose_command(compose_cmd, compose_file, "ps", "-q", service_name),
        cwd=stack_dir,
        timeout_seconds=15.0,
    )
    container_id = container_id_result.stdout.strip() if container_id_result.returncode == 0 else ""
    if not container_id:
        return ServiceObservation(service_name=service_name, configured=True), None

    inspect_result = run_command(["docker", "inspect", container_id], timeout_seconds=15.0)
    if inspect_result.returncode != 0:
        return ServiceObservation(service_name=service_name, configured=True, container_id=container_id), None

    payload = json.loads(inspect_result.stdout)
    inspection = payload[0] if payload else {}
    state = inspection.get("State", {}) if isinstance(inspection, dict) else {}
    health = state.get("Health", {}) if isinstance(state, dict) else {}
    observation = ServiceObservation(
        service_name=service_name,
        configured=True,
        container_id=container_id,
        container_name=str(inspection.get("Name") or "").lstrip("/") or None,
        state_status=str(state.get("Status") or "missing"),
        health_status=str(health.get("Status") or "none"),
        restart_count=int(inspection.get("RestartCount") or 0),
        oom_killed=bool(state.get("OOMKilled") or False),
        running=bool(state.get("Running") or False),
    )
    return observation, inspection


def extract_host_port(inspection: dict[str, Any] | None, container_port: str = "8000/tcp") -> int | None:
    if not isinstance(inspection, dict):
        return None
    network_settings = inspection.get("NetworkSettings")
    if not isinstance(network_settings, dict):
        return None
    ports = network_settings.get("Ports")
    if not isinstance(ports, dict):
        return None
    bindings = ports.get(container_port)
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        host_port = binding.get("HostPort")
        if not host_port:
            continue
        try:
            return int(str(host_port))
        except ValueError:
            continue
    return None


def probe_json(url: str | None, *, timeout_seconds: float) -> ProbeResult:
    if not url:
        return ProbeResult(url=None, ok=False, error="url not configured")

    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    status_code: int | None = None
    raw_body: str | None = None
    error: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        raw_body = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        error = str(exc.reason)
    except Exception as exc:  # pragma: no cover - defensive runtime guard.
        error = str(exc)

    json_body: dict[str, Any] | None = None
    if raw_body:
        try:
            parsed = json.loads(raw_body)
            if isinstance(parsed, dict):
                json_body = parsed
        except json.JSONDecodeError:
            json_body = None

    return ProbeResult(
        url=url,
        ok=bool(status_code is not None and status_code < 400),
        status_code=status_code,
        raw_body=raw_body,
        json_body=json_body,
        error=error,
    )


def capture_command_output(
    evidence_dir: Path,
    file_name: str,
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: float = 30.0,
) -> None:
    target_path = evidence_dir / file_name
    try:
        result = run_command(command, cwd=cwd, timeout_seconds=timeout_seconds)
        content = (
            "COMMAND: " + " ".join(command) + "\n\n"
            + result.stdout
            + ("\n" if result.stdout and not result.stdout.endswith("\n") else "")
            + result.stderr
            + ("\n" if result.stderr and not result.stderr.endswith("\n") else "")
            + f"EXIT_CODE: {result.returncode}\n"
        )
    except subprocess.TimeoutExpired:
        content = "COMMAND: " + " ".join(command) + "\n\nEXIT_CODE: timeout\n"
    target_path.write_text(content, encoding="utf-8")


def write_json_file(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def collect_evidence(
    observation: RuntimeObservation,
    state: RecoveryState,
    decision: RecoveryDecision,
    compose_cmd: list[str],
    stack_dir: Path,
    compose_file: Path,
    evidence_root: Path,
    config: RecoveryConfig,
) -> Path:
    stamp = utc_now().strftime("%Y-%m-%dT%H%M%SZ")
    evidence_dir = evidence_root / f"{stamp}-{decision.action}"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    write_json_file(
        evidence_dir / "00_decision.json",
        {
            "decision": asdict(decision),
            "observation": asdict(observation),
            "state": asdict(state),
            "captured_at": observation.observed_at,
        },
    )
    capture_command_output(
        evidence_dir,
        "01_docker_compose_ps.txt",
        compose_command(compose_cmd, compose_file, "ps"),
        cwd=stack_dir,
    )

    services_to_capture = [observation.api, observation.db]
    if observation.forms_worker.configured:
        services_to_capture.append(observation.forms_worker)

    for index, service in enumerate(services_to_capture, start=2):
        if service.container_id:
            prefix = f"{index:02d}_{service.service_name.replace('-', '_')}"
            capture_command_output(
                evidence_dir,
                f"{prefix}_inspect.txt",
                ["docker", "inspect", service.container_id],
            )
            capture_command_output(
                evidence_dir,
                f"{prefix}_logs.txt",
                ["docker", "logs", f"--tail={config.logs_tail_lines}", service.container_id],
                timeout_seconds=45.0,
            )

    write_json_file(evidence_dir / "20_api_ready_probe.json", asdict(observation.api_ready))
    write_json_file(evidence_dir / "21_api_summary_probe.json", asdict(observation.api_summary))

    if observation.forms_worker.configured:
        capture_command_output(
            evidence_dir,
            "22_forms_worker_healthcheck.txt",
            compose_command(
                compose_cmd,
                compose_file,
                "exec",
                "-T",
                observation.forms_worker.service_name,
                "python",
                "-m",
                "sistema.app.forms_worker_healthcheck",
            ),
            cwd=stack_dir,
            timeout_seconds=30.0,
        )

    return evidence_dir


def restart_service(
    compose_cmd: list[str],
    stack_dir: Path,
    compose_file: Path,
    service_name: str,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        compose_command(compose_cmd, compose_file, "restart", service_name),
        cwd=stack_dir,
        timeout_seconds=60.0,
    )


def default_state_file(stack_dir: Path, compose_file: Path) -> Path:
    stem = compose_file.stem.replace(".", "_")
    return stack_dir / f".{stem}.auto_recovery_state.json"


def default_evidence_root(stack_dir: Path, compose_file: Path) -> Path:
    stem = compose_file.stem.replace(".", "_")
    return stack_dir / "auto_recovery_evidence" / stem


def build_observation(
    compose_cmd: list[str],
    stack_dir: Path,
    compose_file: Path,
    *,
    config: RecoveryConfig,
) -> RuntimeObservation:
    services = set(list_services(compose_cmd, stack_dir, compose_file))
    api_service_name = "app" if "app" in services else "api" if "api" in services else None
    if api_service_name is None:
        raise RuntimeError("Compose file does not define an app or api service")

    api_observation, api_inspection = inspect_service(
        compose_cmd,
        stack_dir,
        compose_file,
        api_service_name,
        configured=True,
    )
    db_observation, _ = inspect_service(
        compose_cmd,
        stack_dir,
        compose_file,
        "db",
        configured="db" in services,
    )
    forms_worker_observation, _ = inspect_service(
        compose_cmd,
        stack_dir,
        compose_file,
        "forms-worker",
        configured="forms-worker" in services,
    )

    host_port = extract_host_port(api_inspection)
    ready_url = f"http://127.0.0.1:{host_port}/api/health/ready" if host_port else None
    summary_url = f"http://127.0.0.1:{host_port}/api/health" if host_port else None
    api_ready = probe_json(ready_url, timeout_seconds=config.health_probe_timeout_seconds)
    api_summary = probe_json(summary_url, timeout_seconds=config.health_probe_timeout_seconds)

    return RuntimeObservation(
        api=api_observation,
        db=db_observation,
        forms_worker=forms_worker_observation,
        api_ready=api_ready,
        api_summary=api_summary,
        observed_at=isoformat_utc(utc_now()),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded auto-recovery for sustained unhealthy states in the Checkcheck stack.",
    )
    parser.add_argument("--stack-dir", help="Docker compose working directory. Auto-detected when omitted.")
    parser.add_argument("--compose-file", help="Compose file path relative to the stack dir or absolute path.")
    parser.add_argument("--state-file", help="Override the persistent recovery state file.")
    parser.add_argument("--evidence-root", help="Override the evidence directory root.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate and capture evidence without restarting anything.")
    parser.add_argument("--api-unhealthy-threshold", type=int, default=3)
    parser.add_argument("--worker-unhealthy-threshold", type=int, default=3)
    parser.add_argument("--api-restart-window-seconds", type=int, default=5400)
    parser.add_argument("--worker-restart-window-seconds", type=int, default=3600)
    parser.add_argument("--api-max-restarts-per-window", type=int, default=1)
    parser.add_argument("--worker-max-restarts-per-window", type=int, default=2)
    parser.add_argument("--max-container-restart-count-before-manual", type=int, default=2)
    parser.add_argument("--health-probe-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--logs-tail-lines", type=int, default=200)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = RecoveryConfig(
        api_unhealthy_threshold=args.api_unhealthy_threshold,
        worker_unhealthy_threshold=args.worker_unhealthy_threshold,
        api_restart_window_seconds=args.api_restart_window_seconds,
        worker_restart_window_seconds=args.worker_restart_window_seconds,
        api_max_restarts_per_window=args.api_max_restarts_per_window,
        worker_max_restarts_per_window=args.worker_max_restarts_per_window,
        max_container_restart_count_before_manual=args.max_container_restart_count_before_manual,
        health_probe_timeout_seconds=args.health_probe_timeout_seconds,
        logs_tail_lines=args.logs_tail_lines,
    )

    stack_dir = Path(args.stack_dir) if args.stack_dir else detect_stack_dir()
    compose_file = resolve_compose_file(stack_dir, args.compose_file)
    state_file = Path(args.state_file) if args.state_file else default_state_file(stack_dir, compose_file)
    evidence_root = Path(args.evidence_root) if args.evidence_root else default_evidence_root(stack_dir, compose_file)
    compose_cmd = choose_compose_command()

    observation = build_observation(compose_cmd, stack_dir, compose_file, config=config)
    state = load_state(state_file)
    now = utc_now()
    apply_observation_to_state(state, observation, config, now=now)
    decision = decide_auto_recovery(observation, state, config)

    evidence_dir: Path | None = None
    restart_result: subprocess.CompletedProcess[str] | None = None
    if decision.action != "noop":
        evidence_dir = collect_evidence(
            observation,
            state,
            decision,
            compose_cmd,
            stack_dir,
            compose_file,
            evidence_root,
            config,
        )

    if decision.action in {"restart_api", "restart_forms_worker"} and decision.target_service and not args.dry_run:
        restart_result = restart_service(compose_cmd, stack_dir, compose_file, decision.target_service)
        if restart_result.returncode == 0:
            service_state = state.api if decision.action == "restart_api" else state.forms_worker
            service_state.restart_timestamps.append(isoformat_utc(now))
            service_state.last_action = decision.action
            service_state.last_reason = decision.reason
            if evidence_dir is not None:
                capture_command_output(
                    evidence_dir,
                    "90_post_restart_compose_ps.txt",
                    compose_command(compose_cmd, compose_file, "ps"),
                    cwd=stack_dir,
                )
                capture_command_output(
                    evidence_dir,
                    "91_restart_command.txt",
                    compose_command(compose_cmd, compose_file, "restart", decision.target_service),
                    cwd=stack_dir,
                )
        else:
            decision = RecoveryDecision(
                action="collect_evidence",
                reason=f"automatic restart command for {decision.target_service} failed; stop for manual intervention",
            )
    elif decision.action == "collect_evidence":
        state.api.last_action = "collect_evidence"
        state.api.last_reason = decision.reason

    state.last_decision = {
        **asdict(decision),
        "compose_file": str(compose_file),
        "dry_run": args.dry_run,
        "evidence_dir": str(evidence_dir) if evidence_dir is not None else None,
        "observed_at": observation.observed_at,
        "restart_command_exit_code": restart_result.returncode if restart_result is not None else None,
    }
    save_state(state_file, state)

    payload = {
        "decision": asdict(decision),
        "dry_run": args.dry_run,
        "evidence_dir": str(evidence_dir) if evidence_dir is not None else None,
        "observation": asdict(observation),
        "state_file": str(state_file),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if decision.action == "collect_evidence":
        return 2
    if restart_result is not None and restart_result.returncode != 0:
        return restart_result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())