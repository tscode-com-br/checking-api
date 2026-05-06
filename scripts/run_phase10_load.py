from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load.phase10_reporting import build_before_after_payload, build_before_after_report, parse_locust_summary
from scripts.load.phase10_support import Phase10HarnessConfig, load_phase10_harness_config

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency for richer host metrics
    psutil = None


DEFAULT_LOCUSTFILE = ROOT / "scripts" / "load" / "phase10_locustfile.py"
DEFAULT_CONFIG = ROOT / "scripts" / "load" / "phase10_web_check.example.json"
DEFAULT_RESULTS_ROOT = ROOT / "docs" / "artifacts" / "phase10"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Phase 10 load harness")
    parser.add_argument(
        "--profile",
        default="web-check",
        choices=("web-check", "admin", "transport", "forms-backlog", "integrated"),
        help="Harness profile to execute",
    )
    parser.add_argument("--base-url", required=True, help="Base URL for the target application, for example http://127.0.0.1:8000")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to the JSON harness config")
    parser.add_argument("--users", type=int, default=20, help="Total concurrent virtual users")
    parser.add_argument("--spawn-rate", type=float, default=5.0, help="User spawn rate per second")
    parser.add_argument("--run-time", default="2m", help="Locust run time, for example 90s or 5m")
    parser.add_argument("--results-dir", default="", help="Directory for CSV, HTML and stdout artifacts")
    parser.add_argument("--web-ui", action="store_true", help="Launch Locust with the Web UI instead of headless mode")
    return parser


def resolve_results_dir(raw_value: str, profile: str) -> Path:
    if raw_value:
        return Path(raw_value).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (DEFAULT_RESULTS_ROOT / f"{profile}-{timestamp}").resolve()


def _build_profile_prefix(results_dir: Path, profile: str) -> str:
    return f"phase10_{profile.replace('-', '_')}"


def build_locust_command(args: argparse.Namespace, results_dir: Path) -> list[str]:
    artifact_prefix = _build_profile_prefix(results_dir, args.profile)
    csv_prefix = results_dir / artifact_prefix
    html_report = results_dir / f"{artifact_prefix}.html"
    command = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(DEFAULT_LOCUSTFILE),
        "--host",
        args.base_url,
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "-t",
        args.run_time,
        "--csv",
        str(csv_prefix),
        "--html",
        str(html_report),
    ]
    if not args.web_ui:
        command.append("--headless")
    return command


def _is_local_target(base_url: str) -> bool:
    hostname = (urlparse(base_url).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost", "::1"}


def _request_json(session: requests.Session, method: str, url: str, **kwargs: object) -> dict[str, object]:
    try:
        response = session.request(method=method, url=url, timeout=15, **kwargs)
    except requests.RequestException as exc:
        return {"error": str(exc)}

    try:
        body: object = response.json()
    except ValueError:
        body = {"raw_text": response.text[:400]}
    return {
        "status_code": response.status_code,
        "body": body,
    }


def _capture_host_metrics(base_url: str) -> dict[str, object]:
    if not _is_local_target(base_url):
        return {
            "body": {
                "available": False,
                "note": "Host CPU and memory capture only runs automatically for local targets.",
            }
        }
    if psutil is None:
        return {
            "body": {
                "available": False,
                "note": "psutil is not installed in the current Python environment.",
            }
        }

    virtual_memory = psutil.virtual_memory()
    return {
        "body": {
            "available": True,
            "cpu_percent": round(psutil.cpu_percent(interval=0.2), 2),
            "memory_percent": round(float(virtual_memory.percent), 2),
            "available_memory_mb": round(float(virtual_memory.available) / (1024 * 1024), 2),
            "total_memory_mb": round(float(virtual_memory.total) / (1024 * 1024), 2),
        }
    }


def capture_phase10_snapshot(
    *,
    base_url: str,
    profile: str,
    harness_config: Phase10HarnessConfig,
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "base_url": base_url,
    }
    with requests.Session() as session:
        snapshot["health"] = _request_json(session, "GET", urljoin(base_url.rstrip("/") + "/", "api/health/ready"))
        snapshot["host"] = _capture_host_metrics(base_url)

        if harness_config.admin is not None:
            admin_login = _request_json(
                session,
                "POST",
                urljoin(base_url.rstrip("/") + "/", harness_config.admin.login_path.lstrip("/")),
                json={
                    "chave": harness_config.admin.credentials.chave,
                    "senha": harness_config.admin.credentials.senha,
                },
            )
            snapshot["admin_login"] = admin_login
            if admin_login.get("status_code") == 200:
                snapshot["admin"] = {
                    "forms_queue": _request_json(
                        session,
                        "GET",
                        urljoin(base_url.rstrip("/") + "/", harness_config.admin.forms_queue_diagnostics_path.lstrip("/")),
                    ).get("body"),
                    "database": _request_json(
                        session,
                        "GET",
                        urljoin(base_url.rstrip("/") + "/", harness_config.admin.database_diagnostics_path.lstrip("/")),
                    ).get("body"),
                }
            else:
                snapshot["admin"] = {
                    "error": "Admin diagnostics were skipped because the admin login failed."
                }

    return snapshot


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        parser.error(f"Harness config not found: {config_path}")

    if args.users <= 0:
        parser.error("--users must be greater than zero")
    if args.spawn_rate <= 0:
        parser.error("--spawn-rate must be greater than zero")

    results_dir = resolve_results_dir(args.results_dir, args.profile)
    results_dir.mkdir(parents=True, exist_ok=True)

    harness_config = load_phase10_harness_config(config_path)
    artifact_prefix = _build_profile_prefix(results_dir, args.profile)

    before_snapshot = capture_phase10_snapshot(base_url=args.base_url, profile=args.profile, harness_config=harness_config)
    before_snapshot_path = results_dir / f"{artifact_prefix}_before_snapshot.json"
    before_snapshot_path.write_text(json.dumps(before_snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    command = build_locust_command(args, results_dir)
    environment = os.environ.copy()
    environment["CHECKCHECK_PHASE10_CONFIG"] = str(config_path)

    stdout_path = results_dir / f"{artifact_prefix}.stdout.log"
    stderr_path = results_dir / f"{artifact_prefix}.stderr.log"
    metadata_path = results_dir / f"{artifact_prefix}.command.txt"
    metadata_path.write_text(
        "\n".join(
            [
                f"base_url={args.base_url}",
                f"profile={args.profile}",
                f"config={config_path}",
                f"users={args.users}",
                f"spawn_rate={args.spawn_rate}",
                f"run_time={args.run_time}",
                f"web_ui={args.web_ui}",
                "command=" + " ".join(command),
            ]
        ),
        encoding="utf-8",
    )

    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            env={**environment, "CHECKCHECK_PHASE10_PROFILE": args.profile},
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )

    after_snapshot = capture_phase10_snapshot(base_url=args.base_url, profile=args.profile, harness_config=harness_config)
    after_snapshot_path = results_dir / f"{artifact_prefix}_after_snapshot.json"
    after_snapshot_path.write_text(json.dumps(after_snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = parse_locust_summary(results_dir / f"{artifact_prefix}_stats.csv")
    report_payload = build_before_after_payload(
        profile=args.profile,
        base_url=args.base_url,
        exit_code=completed.returncode,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    report_payload_path = results_dir / f"{artifact_prefix}_before_after.json"
    report_payload_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    report_markdown = build_before_after_report(
        profile=args.profile,
        base_url=args.base_url,
        exit_code=completed.returncode,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    report_markdown_path = results_dir / f"{artifact_prefix}_before_after.md"
    report_markdown_path.write_text(report_markdown, encoding="utf-8")

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())