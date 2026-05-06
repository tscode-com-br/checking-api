from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Phase10LocustSummary:
    request_count: int
    failure_count: int
    median_response_time: float | None
    average_response_time: float | None
    max_response_time: float | None
    requests_per_second: float | None
    failures_per_second: float | None
    p50_response_time: float | None
    p95_response_time: float | None
    p99_response_time: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse_int(raw_value: object) -> int:
    if raw_value in (None, ""):
        return 0
    return int(float(str(raw_value)))


def _parse_float(raw_value: object) -> float | None:
    if raw_value in (None, ""):
        return None
    return float(str(raw_value))


def _resolve_aggregated_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    for row in rows:
        row_name = str(row.get("Name") or "").strip().lower()
        if row_name in {"aggregated", "total"}:
            return row
    if not rows:
        return None
    return max(rows, key=lambda row: _parse_int(row.get("Request Count")))


def parse_locust_summary(csv_path: str | Path) -> Phase10LocustSummary | None:
    resolved_path = Path(csv_path).resolve()
    if not resolved_path.exists():
        return None

    with resolved_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    aggregated_row = _resolve_aggregated_row(rows)
    if aggregated_row is None:
        return None

    return Phase10LocustSummary(
        request_count=_parse_int(aggregated_row.get("Request Count")),
        failure_count=_parse_int(aggregated_row.get("Failure Count")),
        median_response_time=_parse_float(aggregated_row.get("Median Response Time")),
        average_response_time=_parse_float(aggregated_row.get("Average Response Time")),
        max_response_time=_parse_float(aggregated_row.get("Max Response Time")),
        requests_per_second=_parse_float(aggregated_row.get("Requests/s")),
        failures_per_second=_parse_float(aggregated_row.get("Failures/s")),
        p50_response_time=_parse_float(aggregated_row.get("50%")),
        p95_response_time=_parse_float(aggregated_row.get("95%")),
        p99_response_time=_parse_float(aggregated_row.get("99%")),
    )


def _snapshot_payload(snapshot: dict[str, object] | None, key: str) -> dict[str, object]:
    if not isinstance(snapshot, dict):
        return {}
    raw_value = snapshot.get(key)
    if not isinstance(raw_value, dict):
        return {}
    body = raw_value.get("body")
    if isinstance(body, dict):
        return body
    return raw_value


def _nested_value(payload: dict[str, object], *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _format_number(value: object, *, digits: int = 2) -> str:
    if value in (None, ""):
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _format_delta(before: object, after: object, *, digits: int = 2) -> str:
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return "n/a"
    delta = after - before
    if isinstance(before, int) and isinstance(after, int):
        return f"{delta:+d}"
    return f"{delta:+.{digits}f}"


def _collect_blockers(
    *,
    profile: str,
    exit_code: int,
    summary: Phase10LocustSummary | None,
    before_snapshot: dict[str, object] | None,
    after_snapshot: dict[str, object] | None,
) -> list[str]:
    blockers: list[str] = []
    health_before = _snapshot_payload(before_snapshot, "health")
    health_after = _snapshot_payload(after_snapshot, "health")
    forms_before = _nested_value(_snapshot_payload(before_snapshot, "admin"), "forms_queue")
    forms_after = _nested_value(_snapshot_payload(after_snapshot, "admin"), "forms_queue")
    database_after = _nested_value(_snapshot_payload(after_snapshot, "admin"), "database")
    host_after = _snapshot_payload(after_snapshot, "host")

    if exit_code != 0:
        blockers.append(
            "Locust returned a non-zero exit code. Stop the rollout and re-check the scenario contract in "
            "docs/incidents/2026-05-06-504-phase10-load-harness.md."
        )
    if summary is None:
        blockers.append(
            "No aggregated Locust stats were produced. Stop the rollout and re-check the harness execution path in "
            "docs/incidents/2026-05-06-504-phase10-load-harness.md."
        )
    elif summary.failure_count > 0:
        blockers.append(
            "HTTP failures were observed during the load run. Stop the rollout and re-check the readiness gates and HTTP runtime baseline in "
            "docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md."
        )

    if health_before.get("ready") is False or health_after.get("ready") is False:
        blockers.append(
            "The application was unready before or after the run. Stop the rollout and return to the Phase 9 health gate in "
            "docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md."
        )
    if health_after.get("overall_status") not in {None, "ok", "degraded"}:
        blockers.append(
            "The post-run health status is not acceptable. Stop the rollout and validate the local/public health checkpoints defined in "
            "docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md."
        )

    if isinstance(forms_after, dict):
        worker_after = forms_after.get("worker") if isinstance(forms_after.get("worker"), dict) else {}
        backlog_before = forms_before.get("backlog_count", 0) if isinstance(forms_before, dict) else 0
        backlog_after = forms_after.get("backlog_count", 0)
        failed_before = forms_before.get("failed_count", 0) if isinstance(forms_before, dict) else 0
        failed_after = forms_after.get("failed_count", 0)
        worker_enabled = worker_after.get("enabled")
        worker_expected_running = worker_enabled is not False
        if worker_after.get("stale") is True or (worker_expected_running and worker_after.get("running") is False):
            blockers.append(
                "The Forms worker became stale or stopped running under load. Stop the rollout and use the rollback evidence matrix in "
                "docs/incidents/2026-05-05-504-phase9-deploy-rollback.md."
            )
        if isinstance(backlog_after, int) and isinstance(backlog_before, int) and isinstance(failed_after, int) and isinstance(failed_before, int):
            if backlog_after > backlog_before and failed_after > failed_before:
                blockers.append(
                    "Forms backlog and failed submissions both increased during the run. Stop the rollout and inspect the Forms worker rollback path in "
                    "docs/incidents/2026-05-05-504-phase9-deploy-rollback.md."
                )

    if isinstance(database_after, dict):
        pool = database_after.get("pool") if isinstance(database_after.get("pool"), dict) else {}
        latency = database_after.get("latency") if isinstance(database_after.get("latency"), dict) else {}
        server = database_after.get("server_connections") if isinstance(database_after.get("server_connections"), dict) else {}
        thresholds = (
            database_after.get("recommended_alert_thresholds")
            if isinstance(database_after.get("recommended_alert_thresholds"), dict)
            else {}
        )
        usage_ratio = pool.get("usage_ratio")
        usage_warning = thresholds.get("pool_usage_warning_ratio")
        recent_p95 = latency.get("recent_p95_query_ms")
        p95_warning = thresholds.get("recent_query_p95_warning_ms")
        active_connections = server.get("active_database_connections")
        active_warning = thresholds.get("postgres_active_connections_warning")
        if isinstance(usage_ratio, (int, float)) and isinstance(usage_warning, (int, float)) and usage_ratio >= usage_warning:
            blockers.append(
                "Database pool usage crossed the warning threshold after the run. Stop the rollout and re-check the guarded rollout sequence in "
                "docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md."
            )
        if isinstance(recent_p95, (int, float)) and isinstance(p95_warning, (int, float)) and recent_p95 >= p95_warning:
            blockers.append(
                "Database p95 query latency crossed the warning threshold after the run. Stop the rollout and inspect the HTTP runtime baseline in "
                "docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md."
            )
        if isinstance(active_connections, (int, float)) and isinstance(active_warning, (int, float)) and active_connections >= active_warning:
            blockers.append(
                "Active database connections crossed the warning threshold after the run. Stop the rollout and review the rollback evidence requirements in "
                "docs/incidents/2026-05-05-504-phase9-deploy-rollback.md."
            )

    if isinstance(host_after, dict):
        cpu_percent = host_after.get("cpu_percent")
        memory_percent = host_after.get("memory_percent")
        if isinstance(cpu_percent, (int, float)) and cpu_percent >= 90:
            blockers.append(
                "Host CPU usage reached 90% or higher during the run. Stop the rollout and preserve the evidence bundle before changing runtime capacity."
            )
        if isinstance(memory_percent, (int, float)) and memory_percent >= 90:
            blockers.append(
                "Host memory usage reached 90% or higher during the run. Stop the rollout and preserve the evidence bundle before changing runtime capacity."
            )

    if profile in {"web-check", "forms-backlog", "integrated"} and summary is not None and summary.request_count == 0:
        blockers.append(
            "The selected profile produced zero load requests. Stop the rollout and compare the scenario wiring with "
            "docs/incidents/2026-05-05-504-phase5-burst-measurement.md."
        )

    return blockers


def build_before_after_payload(
    *,
    profile: str,
    base_url: str,
    exit_code: int,
    summary: Phase10LocustSummary | None,
    before_snapshot: dict[str, object] | None,
    after_snapshot: dict[str, object] | None,
) -> dict[str, object]:
    blockers = _collect_blockers(
        profile=profile,
        exit_code=exit_code,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    return {
        "profile": profile,
        "base_url": base_url,
        "exit_code": exit_code,
        "status": "blocked" if blockers else "approved",
        "summary": summary.to_dict() if summary is not None else None,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "blockers": blockers,
    }


def build_before_after_report(
    *,
    profile: str,
    base_url: str,
    exit_code: int,
    summary: Phase10LocustSummary | None,
    before_snapshot: dict[str, object] | None,
    after_snapshot: dict[str, object] | None,
) -> str:
    payload = build_before_after_payload(
        profile=profile,
        base_url=base_url,
        exit_code=exit_code,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    before_health = _snapshot_payload(before_snapshot, "health")
    after_health = _snapshot_payload(after_snapshot, "health")
    before_admin = _snapshot_payload(before_snapshot, "admin")
    after_admin = _snapshot_payload(after_snapshot, "admin")
    before_forms = before_admin.get("forms_queue") if isinstance(before_admin.get("forms_queue"), dict) else {}
    after_forms = after_admin.get("forms_queue") if isinstance(after_admin.get("forms_queue"), dict) else {}
    before_database = before_admin.get("database") if isinstance(before_admin.get("database"), dict) else {}
    after_database = after_admin.get("database") if isinstance(after_admin.get("database"), dict) else {}
    before_host = _snapshot_payload(before_snapshot, "host")
    after_host = _snapshot_payload(after_snapshot, "host")

    lines = [
        f"# Phase 10 before/after report - {profile}",
        "",
        "## Outcome",
        "",
        f"- Status: {str(payload['status']).upper()}",
        f"- Base URL: `{base_url}`",
        f"- Locust exit code: `{exit_code}`",
        "",
        "## Load summary",
        "",
    ]

    if summary is None:
        lines.extend([
            "No aggregated Locust stats were found for this run.",
            "",
        ])
    else:
        lines.extend(
            [
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Request count | {_format_number(summary.request_count, digits=0)} |",
                f"| Failure count | {_format_number(summary.failure_count, digits=0)} |",
                f"| Requests/s | {_format_number(summary.requests_per_second)} |",
                f"| Failures/s | {_format_number(summary.failures_per_second)} |",
                f"| Median latency ms | {_format_number(summary.median_response_time)} |",
                f"| p50 latency ms | {_format_number(summary.p50_response_time)} |",
                f"| p95 latency ms | {_format_number(summary.p95_response_time)} |",
                f"| p99 latency ms | {_format_number(summary.p99_response_time)} |",
                f"| Max latency ms | {_format_number(summary.max_response_time)} |",
                "",
            ]
        )

    lines.extend(
        [
            "## Snapshot comparison",
            "",
            "| Metric | Before | After | Delta |",
            "| --- | ---: | ---: | ---: |",
            f"| Health ready | {_format_number(before_health.get('ready'))} | {_format_number(after_health.get('ready'))} | n/a |",
            f"| Health overall status | {_format_number(before_health.get('overall_status'), digits=0)} | {_format_number(after_health.get('overall_status'), digits=0)} | n/a |",
            f"| Forms backlog | {_format_number(before_forms.get('backlog_count'), digits=0)} | {_format_number(after_forms.get('backlog_count'), digits=0)} | {_format_delta(before_forms.get('backlog_count'), after_forms.get('backlog_count'), digits=0)} |",
            f"| Forms failed count | {_format_number(before_forms.get('failed_count'), digits=0)} | {_format_number(after_forms.get('failed_count'), digits=0)} | {_format_delta(before_forms.get('failed_count'), after_forms.get('failed_count'), digits=0)} |",
            f"| Forms worker running | {_format_number(_nested_value(before_forms, 'worker', 'running'))} | {_format_number(_nested_value(after_forms, 'worker', 'running'))} | n/a |",
            f"| Forms worker stale | {_format_number(_nested_value(before_forms, 'worker', 'stale'))} | {_format_number(_nested_value(after_forms, 'worker', 'stale'))} | n/a |",
            f"| DB checked out | {_format_number(_nested_value(before_database, 'pool', 'checked_out'), digits=0)} | {_format_number(_nested_value(after_database, 'pool', 'checked_out'), digits=0)} | {_format_delta(_nested_value(before_database, 'pool', 'checked_out'), _nested_value(after_database, 'pool', 'checked_out'), digits=0)} |",
            f"| DB current open connections | {_format_number(_nested_value(before_database, 'pool', 'current_open_connections'), digits=0)} | {_format_number(_nested_value(after_database, 'pool', 'current_open_connections'), digits=0)} | {_format_delta(_nested_value(before_database, 'pool', 'current_open_connections'), _nested_value(after_database, 'pool', 'current_open_connections'), digits=0)} |",
            f"| DB recent p95 query ms | {_format_number(_nested_value(before_database, 'latency', 'recent_p95_query_ms'))} | {_format_number(_nested_value(after_database, 'latency', 'recent_p95_query_ms'))} | {_format_delta(_nested_value(before_database, 'latency', 'recent_p95_query_ms'), _nested_value(after_database, 'latency', 'recent_p95_query_ms'))} |",
            f"| Host CPU percent | {_format_number(before_host.get('cpu_percent'))} | {_format_number(after_host.get('cpu_percent'))} | {_format_delta(before_host.get('cpu_percent'), after_host.get('cpu_percent'))} |",
            f"| Host memory percent | {_format_number(before_host.get('memory_percent'))} | {_format_number(after_host.get('memory_percent'))} | {_format_delta(before_host.get('memory_percent'), after_host.get('memory_percent'))} |",
            "",
        ]
    )

    host_notes = [note for note in [before_host.get("note"), after_host.get("note")] if isinstance(note, str) and note]
    if host_notes:
        lines.extend(
            [
                "## Capture notes",
                "",
                *[f"- {note}" for note in dict.fromkeys(host_notes)],
                "",
            ]
        )

    lines.extend(["## Blocking references", ""])
    blockers = payload["blockers"]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- No rollout blocker was detected by the automated checks in this report.")
    lines.extend(
        [
            "",
            "## Evidence to preserve",
            "",
            "- `phase10_<profile>_stats.csv`",
            "- `phase10_<profile>.html`",
            "- `phase10_<profile>.stdout.log` and `phase10_<profile>.stderr.log`",
            "- `phase10_<profile>.command.txt`",
            "- `phase10_<profile>_before_snapshot.json`",
            "- `phase10_<profile>_after_snapshot.json`",
            "- `phase10_<profile>_before_after.json`",
        ]
    )
    return "\n".join(lines) + "\n"