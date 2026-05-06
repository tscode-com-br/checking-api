import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

import pytest


POSTGRES_DATABASE_URL_ENV = "CHECKCHECK_MULTIWORKER_DATABASE_URL"


def reserve_tcp_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def resolve_postgres_database_url() -> str:
    database_url = str(os.environ.get(POSTGRES_DATABASE_URL_ENV, "")).strip()
    if not database_url:
        pytest.skip(
            f"Set {POSTGRES_DATABASE_URL_ENV} to a reachable PostgreSQL URL to run the real multiworker validation."
        )
    if not database_url.startswith("postgresql"):
        pytest.skip(
            f"{POSTGRES_DATABASE_URL_ENV} must point to PostgreSQL because the cross-worker broker depends on LISTEN/NOTIFY."
        )
    return database_url


def build_runtime_env(*, database_url: str, exports_dir: Path, admin_key: str, admin_password: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "development",
            "DATABASE_URL": database_url,
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "PETROBRASP80P82P83",
            "ADMIN_SESSION_SECRET": "multiworker-test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": admin_key,
            "BOOTSTRAP_ADMIN_NAME": "Multiworker Validation",
            "BOOTSTRAP_ADMIN_PASSWORD": admin_password,
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_EXPORTS_DIR": str(exports_dir),
        }
    )
    return env


def run_migrations(*, repo_root: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return

    raise AssertionError(
        "Failed to prepare the PostgreSQL schema for the multiworker validation.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def perform_json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[int, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"{base_url}{path}", data=body, method=method.upper())
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    for header_name, header_value in (headers or {}).items():
        request.add_header(header_name, header_value)

    opener_to_use = opener or urllib.request.build_opener()
    try:
        with opener_to_use.open(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        raw_body = exc.read().decode("utf-8")

    try:
        parsed_body: object = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        parsed_body = raw_body
    return status_code, parsed_body


def wait_for_health(base_url: str, *, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status = None
    last_body = None
    while time.monotonic() < deadline:
        try:
            status_code, payload = perform_json_request(base_url, "/api/health", timeout_seconds=2.0)
            last_status = status_code
            last_body = payload
            if status_code == 200:
                return
        except Exception as exc:  # pragma: no cover - exercised only on server startup races.
            last_body = str(exc)
        time.sleep(0.1)

    raise AssertionError(
        f"Timed out waiting for {base_url}/api/health. Last status={last_status!r}, body={last_body!r}"
    )


@contextmanager
def run_uvicorn_process(*, repo_root: Path, env: dict[str, str], port: int, log_path: Path):
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sistema.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=repo_root,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        wait_for_health(base_url)
        yield base_url
    except Exception:
        log_handle.flush()
        server_output = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        raise AssertionError(f"Failed while running HTTP process on {base_url}.\n{server_output}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log_handle.close()


def build_cookie_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def login_admin(base_url: str, opener: urllib.request.OpenerDirector, *, chave: str, senha: str) -> None:
    status_code, payload = perform_json_request(
        base_url,
        "/api/admin/auth/login",
        method="POST",
        payload={"chave": chave, "senha": senha},
        opener=opener,
    )
    assert status_code == 200, payload
    assert isinstance(payload, dict)
    assert payload.get("authenticated") is True, payload


def login_transport(base_url: str, opener: urllib.request.OpenerDirector, *, chave: str, senha: str) -> None:
    status_code, payload = perform_json_request(
        base_url,
        "/api/transport/auth/verify",
        method="POST",
        payload={"chave": chave, "senha": senha},
        opener=opener,
    )
    assert status_code == 200, payload
    assert isinstance(payload, dict)
    assert payload.get("authenticated") is True, payload


def rotate_admin_password(
    base_url: str,
    opener: urllib.request.OpenerDirector,
    *,
    current_password: str,
    new_password: str,
) -> None:
    status_code, payload = perform_json_request(
        base_url,
        "/api/admin/auth/change-password",
        method="POST",
        payload={
            "senha_atual": current_password,
            "nova_senha": new_password,
        },
        opener=opener,
    )
    assert status_code == 200, payload
    assert isinstance(payload, dict)
    assert payload.get("ok") is True, payload


@contextmanager
def open_sse_stream(
    base_url: str,
    path: str,
    *,
    opener: urllib.request.OpenerDirector,
    timeout_seconds: float = 10.0,
):
    request = urllib.request.Request(f"{base_url}{path}", method="GET")
    request.add_header("Accept", "text/event-stream")
    response = opener.open(request, timeout=timeout_seconds)
    try:
        yield response
    finally:
        response.close()


def read_next_sse_event(response, *, timeout_seconds: float = 10.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            raw_line = response.readline()
        except socket.timeout as exc:
            raise AssertionError("Timed out waiting for the next SSE payload.") from exc

        if not raw_line:
            continue

        line = raw_line.decode("utf-8").strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data: "):
            continue
        return json.loads(line.removeprefix("data: "))

    raise AssertionError("Timed out waiting for the next SSE payload.")


def test_multiworker_realtime_stays_coherent_across_two_http_processes(tmp_path: Path):
    database_url = resolve_postgres_database_url()
    repo_root = Path(__file__).resolve().parents[1]
    original_password = "mw-secret-1"
    rotated_password = "mw-secret-2"
    admin_key = uuid.uuid4().hex[:4].upper()
    runtime_env = build_runtime_env(
        database_url=database_url,
        exports_dir=tmp_path / "exports",
        admin_key=admin_key,
        admin_password=original_password,
    )

    run_migrations(repo_root=repo_root, env=runtime_env)

    port_a = reserve_tcp_port()
    port_b = reserve_tcp_port()
    log_a = tmp_path / "worker-a.log"
    log_b = tmp_path / "worker-b.log"

    with run_uvicorn_process(repo_root=repo_root, env=runtime_env, port=port_a, log_path=log_a) as base_url_a:
        with run_uvicorn_process(repo_root=repo_root, env=runtime_env, port=port_b, log_path=log_b) as base_url_b:
            admin_opener_a = build_cookie_opener()
            admin_opener_b = build_cookie_opener()
            transport_opener_b = build_cookie_opener()

            login_admin(base_url_a, admin_opener_a, chave=admin_key, senha=original_password)
            login_admin(base_url_b, admin_opener_b, chave=admin_key, senha=original_password)
            login_transport(base_url_b, transport_opener_b, chave=admin_key, senha=original_password)

            with open_sse_stream(base_url_a, "/api/admin/stream", opener=admin_opener_a) as admin_stream:
                with open_sse_stream(base_url_b, "/api/transport/stream", opener=transport_opener_b) as transport_stream:
                    assert read_next_sse_event(admin_stream)["reason"] == "connected"
                    assert read_next_sse_event(transport_stream)["reason"] == "connected"

                    rotate_admin_password(
                        base_url_b,
                        admin_opener_b,
                        current_password=original_password,
                        new_password=rotated_password,
                    )

                    admin_event_from_process_b = read_next_sse_event(admin_stream)
                    transport_event_same_process_b = read_next_sse_event(transport_stream)
                    assert admin_event_from_process_b["reason"] == "event"
                    assert transport_event_same_process_b["reason"] == "event"

                    rotate_admin_password(
                        base_url_a,
                        admin_opener_a,
                        current_password=rotated_password,
                        new_password=original_password,
                    )

                    admin_event_same_process_a = read_next_sse_event(admin_stream)
                    transport_event_from_process_a = read_next_sse_event(transport_stream)
                    assert admin_event_same_process_a["reason"] == "event"
                    assert transport_event_from_process_a["reason"] == "event"