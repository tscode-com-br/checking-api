from __future__ import annotations

import csv
from pathlib import Path

from scripts.load.phase10_reporting import build_before_after_payload, build_before_after_report, parse_locust_summary


def _write_locust_stats_csv(csv_path: Path) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Type",
                "Name",
                "Request Count",
                "Failure Count",
                "Median Response Time",
                "Average Response Time",
                "Min Response Time",
                "Max Response Time",
                "Average Content Size",
                "Requests/s",
                "Failures/s",
                "50%",
                "66%",
                "75%",
                "80%",
                "90%",
                "95%",
                "98%",
                "99%",
                "99.9%",
                "100%",
            ]
        )
        writer.writerow(["GET", "GET /api/health/ready", 10, 0, 12, 15.3, 5, 30, 100, 1.0, 0.0, 12, 13, 14, 15, 20, 24, 28, 29, 30, 30])
        writer.writerow(["", "Aggregated", 120, 3, 45, 52.3, 10, 240, 1234, 12.5, 0.3, 45, 48, 50, 55, 80, 110, 150, 190, 240, 240])


def test_parse_locust_summary_reads_aggregated_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "phase10_integrated_stats.csv"
    _write_locust_stats_csv(csv_path)

    summary = parse_locust_summary(csv_path)

    assert summary is not None
    assert summary.request_count == 120
    assert summary.failure_count == 3
    assert summary.requests_per_second == 12.5
    assert summary.p95_response_time == 110.0
    assert summary.p99_response_time == 190.0


def test_build_before_after_report_marks_blockers_for_failed_run(tmp_path: Path) -> None:
    csv_path = tmp_path / "phase10_integrated_stats.csv"
    _write_locust_stats_csv(csv_path)
    summary = parse_locust_summary(csv_path)

    before_snapshot = {
        "health": {"body": {"ready": True, "overall_status": "ok"}},
        "admin": {
            "body": {
                "forms_queue": {
                    "backlog_count": 1,
                    "failed_count": 0,
                    "worker": {"stale": False, "running": True},
                },
                "database": {
                    "pool": {"checked_out": 2, "current_open_connections": 4, "usage_ratio": 0.2},
                    "latency": {"recent_p95_query_ms": 25},
                    "server_connections": {"active_database_connections": 4},
                    "recommended_alert_thresholds": {
                        "pool_usage_warning_ratio": 0.7,
                        "recent_query_p95_warning_ms": 100,
                        "postgres_active_connections_warning": 8,
                    },
                },
            }
        },
        "host": {"body": {"cpu_percent": 35.0, "memory_percent": 45.0}},
    }
    after_snapshot = {
        "health": {"body": {"ready": False, "overall_status": "unready"}},
        "admin": {
            "body": {
                "forms_queue": {
                    "backlog_count": 7,
                    "failed_count": 2,
                    "worker": {"stale": True, "running": False},
                },
                "database": {
                    "pool": {"checked_out": 8, "current_open_connections": 12, "usage_ratio": 0.9},
                    "latency": {"recent_p95_query_ms": 180},
                    "server_connections": {"active_database_connections": 12},
                    "recommended_alert_thresholds": {
                        "pool_usage_warning_ratio": 0.7,
                        "recent_query_p95_warning_ms": 100,
                        "postgres_active_connections_warning": 8,
                    },
                },
            }
        },
        "host": {"body": {"cpu_percent": 91.0, "memory_percent": 92.0}},
    }

    payload = build_before_after_payload(
        profile="integrated",
        base_url="http://127.0.0.1:8000",
        exit_code=1,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    report = build_before_after_report(
        profile="integrated",
        base_url="http://127.0.0.1:8000",
        exit_code=1,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )

    assert payload["status"] == "blocked"
    assert any("phase9-startup-migration-deploy-hardening" in blocker for blocker in payload["blockers"])
    assert any("phase9-deploy-rollback" in blocker for blocker in payload["blockers"])
    assert "Status: BLOCKED" in report
    assert "| Forms backlog | 1 | 7 | +6 |" in report
    assert "Host CPU usage reached 90% or higher" in report


def test_build_before_after_report_reads_current_admin_snapshot_shape(tmp_path: Path) -> None:
    csv_path = tmp_path / "phase10_web_check_stats.csv"
    _write_locust_stats_csv(csv_path)
    summary = parse_locust_summary(csv_path)

    before_snapshot = {
        "health": {"status_code": 200, "body": {"ready": True, "overall_status": "ok"}},
        "admin": {
            "forms_queue": {
                "backlog_count": 7,
                "failed_count": 0,
                "worker": {"enabled": True, "stale": False, "running": False},
            },
            "database": {
                "pool": {"checked_out": 1, "current_open_connections": 1, "usage_ratio": 0.067},
                "latency": {"recent_p95_query_ms": 2},
                "server_connections": {"active_database_connections": None},
                "recommended_alert_thresholds": {
                    "pool_usage_warning_ratio": 0.8,
                    "recent_query_p95_warning_ms": 150,
                    "postgres_active_connections_warning": 24,
                },
            },
        },
        "host": {"body": {"cpu_percent": 17.1, "memory_percent": 84.3}},
    }
    after_snapshot = {
        "health": {"status_code": 200, "body": {"ready": True, "overall_status": "ok"}},
        "admin": {
            "forms_queue": {
                "backlog_count": 7,
                "failed_count": 0,
                "worker": {"enabled": True, "stale": False, "running": False},
            },
            "database": {
                "pool": {"checked_out": 1, "current_open_connections": 1, "usage_ratio": 0.067},
                "latency": {"recent_p95_query_ms": 2},
                "server_connections": {"active_database_connections": None},
                "recommended_alert_thresholds": {
                    "pool_usage_warning_ratio": 0.8,
                    "recent_query_p95_warning_ms": 150,
                    "postgres_active_connections_warning": 24,
                },
            },
        },
        "host": {"body": {"cpu_percent": 18.5, "memory_percent": 86.9}},
    }

    payload = build_before_after_payload(
        profile="web-check",
        base_url="http://127.0.0.1:8000",
        exit_code=1,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    report = build_before_after_report(
        profile="web-check",
        base_url="http://127.0.0.1:8000",
        exit_code=1,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )

    assert payload["status"] == "blocked"
    assert any("Forms worker became stale or stopped running under load" in blocker for blocker in payload["blockers"])
    assert "| Forms backlog | 7 | 7 | +0 |" in report
    assert "| Forms worker running | no | no | n/a |" in report
    assert "| DB checked out | 1 | 1 | +0 |" in report