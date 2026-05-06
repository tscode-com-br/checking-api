from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

import httpx


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "temp_011_phase6_backend_db_validation_report.json"
HEAD_WORKTREE_PATH = ROOT / ".copilot-temp" / "phase6-baseline-head"

ADMIN_KEY = "HR70"
ADMIN_PASSWORD = "eAcacdLe2"
WEB_USER_KEY = "WB90"
WEB_USER_PASSWORD = "abc123"
MOBILE_USER_KEY = "MB90"
MOBILE_SHARED_KEY = "mobile-test-key"
POSTGRES_DB = "checking"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
FORMS_URL = "https://example.com/form"

DEFAULT_BULK_USERS_PER_STATE = 60
DEFAULT_WARMUP_REQUESTS = 3
DEFAULT_SAMPLES = 40
DEFAULT_CONCURRENCY = 6
DEFAULT_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class ComposeBackend:
    kind: str
    description: str


@dataclass(frozen=True)
class VariantConfig:
    name: str
    repo_root: Path
    api_port: int
    postgres_port: int
    compose_project_name: str
    image_name: str
    git_label: str


@dataclass(frozen=True)
class RouteSpec:
    name: str
    method: str
    path: str
    client_kind: str
    params: dict[str, str] | None = None


HOT_ROUTES = (
    RouteSpec(
        name="web_state",
        method="GET",
        path="/api/web/check/state",
        client_kind="web",
        params={"chave": WEB_USER_KEY},
    ),
    RouteSpec(
        name="mobile_state",
        method="GET",
        path="/api/mobile/state",
        client_kind="mobile",
        params={"chave": MOBILE_USER_KEY},
    ),
    RouteSpec(
        name="admin_checkin",
        method="GET",
        path="/api/admin/checkin",
        client_kind="admin",
    ),
    RouteSpec(
        name="admin_checkout",
        method="GET",
        path="/api/admin/checkout",
        client_kind="admin",
    ),
    RouteSpec(
        name="admin_projects",
        method="GET",
        path="/api/admin/projects",
        client_kind="admin",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client-mode",
        action="store_true",
        help="Run only the HTTP seed/measurement client logic inside a Compose network.",
    )
    parser.add_argument(
        "--client-phase",
        choices=["seed", "measure"],
        help="Client-mode phase to execute.",
    )
    parser.add_argument(
        "--base-url",
        help="Base URL used by the client-mode HTTP runner.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        choices=["before_head", "after_worktree"],
        help="Run only the selected variant. Can be used multiple times.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES,
        help="Measured requests per route.",
    )
    parser.add_argument(
        "--warmup-requests",
        type=int,
        default=DEFAULT_WARMUP_REQUESTS,
        help="Warmup requests per route before measurement.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Concurrent requests per route group.",
    )
    parser.add_argument(
        "--bulk-users-per-state",
        type=int,
        default=DEFAULT_BULK_USERS_PER_STATE,
        help="Synthetic users seeded in each admin state bucket.",
    )
    parser.add_argument(
        "--report-path",
        default=str(REPORT_PATH),
        help="Where to write the JSON report.",
    )
    return parser.parse_args()


def reserve_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def resolve_compose_backend() -> ComposeBackend:
    docker_compose = shutil.which("docker-compose")
    if docker_compose:
        return ComposeBackend(kind="docker-compose", description="docker-compose")

    docker = shutil.which("docker")
    if docker:
        result = run_command([docker, "compose", "version"], capture_output=True)
        if result.returncode == 0:
            return ComposeBackend(kind="docker", description="docker compose")

    wsl = shutil.which("wsl")
    if wsl:
        result = run_command([wsl, "-d", "Ubuntu", "--", "docker", "compose", "version"], capture_output=True)
        if result.returncode == 0:
            return ComposeBackend(kind="wsl", description="wsl -d Ubuntu -- docker compose")

    raise RuntimeError("Neither native Docker Compose nor the Ubuntu WSL Docker Compose backend is available")


def windows_to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def build_compose_command(
    backend: ComposeBackend,
    *,
    repo_root: Path,
    env_overrides: dict[str, str],
    compose_args: list[str],
) -> tuple[list[str], Path | None, dict[str, str] | None]:
    if backend.kind == "docker-compose":
        env = os.environ.copy()
        env.update(env_overrides)
        return ["docker-compose", *compose_args], repo_root, env

    if backend.kind == "docker":
        env = os.environ.copy()
        env.update(env_overrides)
        return ["docker", "compose", *compose_args], repo_root, env

    if backend.kind == "wsl":
        linux_repo_root = windows_to_wsl_path(repo_root)
        env_args = [f"{key}={value}" for key, value in env_overrides.items()]
        command = [
            "wsl",
            "-d",
            "Ubuntu",
            "--cd",
            linux_repo_root,
            "--",
            "env",
            *env_args,
            "docker",
            "compose",
            *compose_args,
        ]
        return command, None, None

    raise RuntimeError(f"Unsupported compose backend: {backend.kind}")


def run_compose(
    backend: ComposeBackend,
    *,
    repo_root: Path,
    env_overrides: dict[str, str],
    compose_args: list[str],
    capture_output: bool = False,
) -> str | None:
    command, cwd, env = build_compose_command(
        backend,
        repo_root=repo_root,
        env_overrides=env_overrides,
        compose_args=compose_args,
    )
    result = run_command(command, cwd=cwd, env=env, capture_output=capture_output)
    if result.returncode != 0:
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        raise RuntimeError(
            "Compose command failed:\n"
            f"command={' '.join(command)}\n"
            f"exit_code={result.returncode}\n"
            f"stdout={stdout}\n"
            f"stderr={stderr}"
        )
    if capture_output:
        return result.stdout.strip()
    return None


def git_head_commit(repo_root: Path) -> str:
    result = run_command(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "Unable to resolve git HEAD")
    return (result.stdout or "").strip()


def prepare_head_worktree(repo_root: Path, worktree_path: Path) -> Path:
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree_path)], capture_output=True)
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
    result = run_command(
        ["git", "-C", str(repo_root), "worktree", "add", "--force", "--detach", str(worktree_path), "HEAD"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Unable to create HEAD worktree")
    return worktree_path


def cleanup_head_worktree(repo_root: Path, worktree_path: Path) -> None:
    run_command(["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree_path)], capture_output=True)
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)


def build_variant_configs(selected_variants: set[str] | None) -> list[VariantConfig]:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    baseline_worktree = prepare_head_worktree(ROOT, HEAD_WORKTREE_PATH)

    variants = {
        "before_head": VariantConfig(
            name="before_head",
            repo_root=baseline_worktree,
            api_port=reserve_tcp_port(),
            postgres_port=reserve_tcp_port(),
            compose_project_name=f"phase6before{timestamp}",
            image_name=f"checkcheck-phase6-before:{timestamp}",
            git_label=git_head_commit(ROOT),
        ),
        "after_worktree": VariantConfig(
            name="after_worktree",
            repo_root=ROOT,
            api_port=reserve_tcp_port(),
            postgres_port=reserve_tcp_port(),
            compose_project_name=f"phase6after{timestamp}",
            image_name=f"checkcheck-phase6-after:{timestamp}",
            git_label="working-tree",
        ),
    }
    ordered_names = ["before_head", "after_worktree"]
    if selected_variants:
        ordered_names = [name for name in ordered_names if name in selected_variants]
    return [variants[name] for name in ordered_names]


def mount_workspace_path(backend: ComposeBackend, workspace_root: Path) -> str:
    if backend.kind == "wsl":
        return windows_to_wsl_path(workspace_root)
    return str(workspace_root)


def variant_env(variant: VariantConfig) -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "APP_HOST": "0.0.0.0",
        "APP_PORT": "8000",
        "DATABASE_URL": f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/{POSTGRES_DB}",
        "API_PORT": str(variant.api_port),
        "POSTGRES_BIND_ADDRESS": "127.0.0.1",
        "POSTGRES_PORT": str(variant.postgres_port),
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "BOOTSTRAP_ADMIN_KEY": ADMIN_KEY,
        "BOOTSTRAP_ADMIN_PASSWORD": ADMIN_PASSWORD,
        "BOOTSTRAP_ADMIN_NAME": "Tamer Salmem",
        "ADMIN_SESSION_SECRET": "phase6-benchmark-secret",
        "MOBILE_APP_SHARED_KEY": MOBILE_SHARED_KEY,
        "FORMS_URL": FORMS_URL,
        "FORMS_QUEUE_ENABLED": "false",
        "SERVE_ADMIN_SITE_IN_API": "false",
        "SERVE_USER_SITE_IN_API": "false",
        "SERVE_TRANSPORT_SITE_IN_API": "false",
        "CHECKCHECK_API_IMAGE": variant.image_name,
    }


async def wait_for_api_ready(base_url: str, *, timeout_seconds: float = 180.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    async with httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=5.0) as client:
        while time.monotonic() < deadline:
            for path in ("/api/health/ready", "/api/health"):
                try:
                    response = await client.get(path)
                    if response.status_code == 200:
                        return
                    last_error = f"{path} -> {response.status_code}"
                except Exception as exc:  # pragma: no cover - startup race guard.
                    last_error = str(exc)
            await asyncio.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for API readiness at {base_url}: {last_error}")


def wait_for_api_ready_in_container(
    backend: ComposeBackend,
    *,
    variant: VariantConfig,
    env_overrides: dict[str, str],
    timeout_seconds: float = 180.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    probe_snippet = (
        "import urllib.request\n"
        "for path in ('/api/health/ready', '/api/health'):\n"
        "    try:\n"
        "        response = urllib.request.urlopen(f'http://127.0.0.1:8000{path}', timeout=5)\n"
        "        raise SystemExit(0 if response.status == 200 else 1)\n"
        "    except Exception:\n"
        "        continue\n"
        "raise SystemExit(1)"
    )
    compose_prefix = ["-p", variant.compose_project_name, "-f", "docker-compose.api.yml"]
    while time.monotonic() < deadline:
        try:
            result = run_compose(
                backend,
                repo_root=variant.repo_root,
                env_overrides=env_overrides,
                compose_args=[*compose_prefix, "exec", "-T", "api", "python", "-c", probe_snippet],
                capture_output=True,
            )
            if result is not None:
                return
        except RuntimeError:
            pass
        time.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for in-container API readiness for variant {variant.name}")


async def expect_status_ok(response: httpx.Response, *, expected_status: int) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.status_code != expected_status:
        raise RuntimeError(f"Unexpected HTTP {response.status_code}: {payload}")
    if isinstance(payload, dict):
        return payload
    return {"payload": payload}


async def login_admin_client(base_url: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=DEFAULT_TIMEOUT_SECONDS)
    response = await client.post("/api/admin/auth/login", json={"chave": ADMIN_KEY, "senha": ADMIN_PASSWORD})
    payload = await expect_status_ok(response, expected_status=200)
    if not payload.get("ok", False):
        raise RuntimeError(f"Admin login did not return ok=true: {payload}")
    session_response = await client.get("/api/admin/auth/session")
    session_payload = await expect_status_ok(session_response, expected_status=200)
    if not session_payload.get("authenticated", False):
        raise RuntimeError(f"Admin session did not authenticate after login: {session_payload}")
    return client


async def login_web_client(base_url: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=DEFAULT_TIMEOUT_SECONDS)
    response = await client.post("/api/web/auth/login", json={"chave": WEB_USER_KEY, "senha": WEB_USER_PASSWORD})
    payload = await expect_status_ok(response, expected_status=200)
    if not payload.get("authenticated", False):
        raise RuntimeError(f"Web login did not authenticate: {payload}")
    return client


async def seed_web_user(base_url: str) -> None:
    async with httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        response = await client.post(
            "/api/web/auth/register-user",
            json={
                "chave": WEB_USER_KEY,
                "nome": "Benchmark Web User",
                "projeto": "P80",
                "email": "benchmark-web@example.com",
                "senha": WEB_USER_PASSWORD,
                "confirmar_senha": WEB_USER_PASSWORD,
            },
        )
        await expect_status_ok(response, expected_status=201)

        now = datetime.now(UTC)
        actions = (
            ("checkin", now - timedelta(hours=3), "Web A"),
            ("checkout", now - timedelta(hours=2), "Web B"),
            ("checkin", now - timedelta(minutes=45), "Web C"),
        )
        for index, (action, event_time, local_name) in enumerate(actions, start=1):
            response = await client.post(
                "/api/web/check",
                json={
                    "chave": WEB_USER_KEY,
                    "projeto": "P80",
                    "action": action,
                    "informe": "normal",
                    "local": local_name,
                    "event_time": event_time.isoformat(),
                    "client_event_id": f"phase6-web-{index}",
                },
            )
            await expect_status_ok(response, expected_status=200)


async def submit_mobile_event(client: httpx.AsyncClient, *, chave: str, projeto: str, action: str, event_time: datetime, local_name: str, client_event_id: str) -> None:
    response = await client.post(
        "/api/mobile/events/submit",
        headers={"x-mobile-shared-key": MOBILE_SHARED_KEY},
        json={
            "chave": chave,
            "projeto": projeto,
            "action": action,
            "local": local_name,
            "event_time": event_time.isoformat(),
            "client_event_id": client_event_id,
        },
    )
    await expect_status_ok(response, expected_status=200)


async def seed_mobile_user(base_url: str) -> None:
    async with httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        now = datetime.now(UTC)
        actions = (
            ("checkin", now - timedelta(hours=4), "Android A"),
            ("checkout", now - timedelta(hours=1, minutes=30), "Android B"),
            ("checkin", now - timedelta(minutes=30), "Android C"),
        )
        for index, (action, event_time, local_name) in enumerate(actions, start=1):
            await submit_mobile_event(
                client,
                chave=MOBILE_USER_KEY,
                projeto="P82",
                action=action,
                event_time=event_time,
                local_name=local_name,
                client_event_id=f"phase6-mobile-{index}",
            )


async def seed_bulk_admin_presence_users(base_url: str, *, users_per_state: int) -> None:
    projects = ("P80", "P82", "P83")
    now = datetime.now(UTC)
    async with httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        for index in range(users_per_state):
            await submit_mobile_event(
                client,
                chave=f"CI{index:02d}",
                projeto=projects[index % len(projects)],
                action="checkin",
                event_time=now - timedelta(minutes=10 + index),
                local_name=f"Checkin-{index % 9}",
                client_event_id=f"phase6-bulk-checkin-{index}",
            )
        for index in range(users_per_state):
            await submit_mobile_event(
                client,
                chave=f"CO{index:02d}",
                projeto=projects[index % len(projects)],
                action="checkout",
                event_time=now - timedelta(minutes=15 + index),
                local_name=f"Checkout-{index % 9}",
                client_event_id=f"phase6-bulk-checkout-{index}",
            )


async def seed_benchmark_data(base_url: str, *, users_per_state: int) -> None:
    await seed_web_user(base_url)
    await seed_mobile_user(base_url)
    await seed_bulk_admin_presence_users(base_url, users_per_state=users_per_state)


def percentile_ms(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = max(((len(ordered) * percentile + 99) // 100) - 1, 0)
    return round(ordered[index], 2)


def summarize_latencies(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
        "avg_ms": round(sum(values) / len(values), 2),
        "p50_ms": percentile_ms(values, 50),
        "p95_ms": percentile_ms(values, 95),
        "p99_ms": percentile_ms(values, 99),
    }


async def run_route_requests(
    client: httpx.AsyncClient,
    route: RouteSpec,
    *,
    samples: int,
    concurrency: int,
) -> list[float]:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []

    async def issue_request() -> None:
        async with semaphore:
            started_at = perf_counter()
            response = await client.request(route.method, route.path, params=route.params)
            latency_ms = (perf_counter() - started_at) * 1000.0
            if response.status_code != 200:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {"raw": response.text}
                raise RuntimeError(f"Route {route.name} failed with HTTP {response.status_code}: {payload}")
            latencies.append(latency_ms)

    await asyncio.gather(*[issue_request() for _ in range(samples)])
    return latencies


async def run_route_warmups(client: httpx.AsyncClient, route: RouteSpec, *, warmup_requests: int) -> None:
    for _ in range(warmup_requests):
        response = await client.request(route.method, route.path, params=route.params)
        if response.status_code != 200:
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
            raise RuntimeError(f"Warmup failed for {route.name}: {payload}")


def inspect_api_pool_config(
    backend: ComposeBackend,
    *,
    variant: VariantConfig,
    env_overrides: dict[str, str],
) -> dict[str, object]:
    snippet = (
        "import json\n"
        "from sistema.app.database import engine\n"
        "def safe_call(name):\n"
        "    method = getattr(engine.pool, name, None)\n"
        "    if callable(method):\n"
        "        try:\n"
        "            return method()\n"
        "        except Exception:\n"
        "            return None\n"
        "    return None\n"
        "payload = {\n"
        "    'dialect': engine.dialect.name,\n"
        "    'driver': engine.dialect.driver,\n"
        "    'pool_class': type(engine.pool).__name__,\n"
        "    'status': engine.pool.status() if hasattr(engine.pool, 'status') else None,\n"
        "    'configured_pool_size': safe_call('size'),\n"
        "    'configured_max_overflow': getattr(engine.pool, '_max_overflow', None),\n"
        "    'configured_pool_timeout_seconds': getattr(engine.pool, '_timeout', None),\n"
        "    'configured_pool_recycle_seconds': getattr(engine.pool, '_recycle', None),\n"
        "    'pool_pre_ping': getattr(engine.pool, '_pre_ping', None),\n"
        "}\n"
        "print(json.dumps(payload, sort_keys=True))"
    )
    output = run_compose(
        backend,
        repo_root=variant.repo_root,
        env_overrides=env_overrides,
        compose_args=[
            "-p",
            variant.compose_project_name,
            "-f",
            "docker-compose.api.yml",
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            snippet,
        ],
        capture_output=True,
    )
    return json.loads(output or "{}")


def query_pg_stat_activity(
    backend: ComposeBackend,
    *,
    variant: VariantConfig,
    env_overrides: dict[str, str],
) -> dict[str, int]:
    query = (
        "SELECT json_build_object("
        "'database_connections_total', GREATEST(COUNT(*) - 1, 0),"
        "'active_database_connections', GREATEST(COUNT(*) FILTER (WHERE state = 'active') - 1, 0),"
        "'waiting_database_connections', COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL AND state <> 'idle'),"
        "'idle_in_transaction_connections', COUNT(*) FILTER (WHERE state = 'idle in transaction')"
        ")::text "
        "FROM pg_stat_activity WHERE datname = current_database();"
    )
    output = run_compose(
        backend,
        repo_root=variant.repo_root,
        env_overrides=env_overrides,
        compose_args=[
            "-p",
            variant.compose_project_name,
            "-f",
            "docker-compose.api.yml",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-Atc",
            query,
        ],
        capture_output=True,
    )
    return json.loads(output or "{}")


async def fetch_database_diagnostics(admin_client: httpx.AsyncClient) -> dict[str, object] | None:
    response = await admin_client.get("/api/admin/diagnostics/database")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise RuntimeError(f"Unexpected diagnostics status {response.status_code}: {response.text}")
    return response.json()


async def measure_http_suite(
    *,
    base_url: str,
    samples: int,
    warmup_requests: int,
    concurrency: int,
) -> dict[str, object]:
    await wait_for_api_ready(base_url)
    admin_client = await login_admin_client(base_url)
    web_client = await login_web_client(base_url)
    mobile_client = httpx.AsyncClient(
        base_url=base_url,
        follow_redirects=True,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        headers={"x-mobile-shared-key": MOBILE_SHARED_KEY},
    )
    try:
        suite_before_diagnostics = compact_diagnostics(await fetch_database_diagnostics(admin_client))
        clients = {
            "admin": admin_client,
            "web": web_client,
            "mobile": mobile_client,
        }
        route_results: list[dict[str, object]] = []
        for route in HOT_ROUTES:
            client = clients[route.client_kind]
            await run_route_warmups(client, route, warmup_requests=warmup_requests)

            diagnostics_before = await fetch_database_diagnostics(admin_client)
            latencies = await run_route_requests(
                client,
                route,
                samples=samples,
                concurrency=concurrency,
            )
            diagnostics_after = await fetch_database_diagnostics(admin_client)

            query_total_before = extract_hot_path_query_total(diagnostics_before, route)
            query_total_after = extract_hot_path_query_total(diagnostics_after, route)
            query_delta = None
            queries_per_request = None
            if query_total_before is not None and query_total_after is not None:
                query_delta = query_total_after - query_total_before
                queries_per_request = round(query_delta / samples, 3)

            route_results.append(
                {
                    "route": route.name,
                    "path": route.path,
                    "client_kind": route.client_kind,
                    "latency_ms": summarize_latencies(latencies),
                    "query_total_delta": query_delta,
                    "queries_per_request": queries_per_request,
                    "diagnostics_before": compact_diagnostics(diagnostics_before),
                    "diagnostics_after": compact_diagnostics(diagnostics_after),
                }
            )

        suite_after_diagnostics = compact_diagnostics(await fetch_database_diagnostics(admin_client))
    finally:
        await admin_client.aclose()
        await web_client.aclose()
        await mobile_client.aclose()

    return {
        "suite_before_diagnostics": suite_before_diagnostics,
        "suite_after_diagnostics": suite_after_diagnostics,
        "routes": route_results,
    }


def compact_diagnostics(payload: dict[str, object] | None) -> dict[str, object] | None:
    if payload is None:
        return None
    pool = dict(payload.get("pool", {}))
    server_connections = dict(payload.get("server_connections", {}))
    return {
        "pool": {
            "configured_pool_size": pool.get("configured_pool_size"),
            "configured_max_overflow": pool.get("configured_max_overflow"),
            "configured_pool_timeout_seconds": pool.get("configured_pool_timeout_seconds"),
            "configured_pool_recycle_seconds": pool.get("configured_pool_recycle_seconds"),
            "total_capacity": pool.get("total_capacity"),
            "checked_out": pool.get("checked_out"),
            "current_open_connections": pool.get("current_open_connections"),
            "open_connections_high_watermark": pool.get("open_connections_high_watermark"),
            "checked_out_high_watermark": pool.get("checked_out_high_watermark"),
            "total_connect_events": pool.get("total_connect_events"),
            "total_checkout_events": pool.get("total_checkout_events"),
        },
        "server_connections": {
            "source": server_connections.get("source"),
            "database_connections_total": server_connections.get("database_connections_total"),
            "active_database_connections": server_connections.get("active_database_connections"),
            "waiting_database_connections": server_connections.get("waiting_database_connections"),
            "idle_in_transaction_connections": server_connections.get("idle_in_transaction_connections"),
        },
    }


def extract_hot_path_query_total(payload: dict[str, object] | None, route: RouteSpec) -> int | None:
    if payload is None:
        return None
    latency = dict(payload.get("latency", {}))
    hot_paths = latency.get("hot_paths", [])
    for item in hot_paths:
        if isinstance(item, dict) and item.get("path") == route.path:
            value = item.get("total_query_count")
            return int(value) if isinstance(value, int) else None
    return None


async def benchmark_variant(
    backend: ComposeBackend,
    *,
    variant: VariantConfig,
    samples: int,
    warmup_requests: int,
    concurrency: int,
    users_per_state: int,
) -> dict[str, object]:
    env_overrides = variant_env(variant)
    compose_prefix = ["-p", variant.compose_project_name, "-f", "docker-compose.api.yml"]
    workspace_mount = mount_workspace_path(backend, ROOT)
    client_report_path = ROOT / ".copilot-temp" / f"phase6_client_{variant.name}.json"
    client_report_path.parent.mkdir(parents=True, exist_ok=True)
    if client_report_path.exists():
        client_report_path.unlink()

    run_compose(
        backend,
        repo_root=variant.repo_root,
        env_overrides=env_overrides,
        compose_args=[*compose_prefix, "up", "-d", "--build", "db", "api"],
    )

    try:
        wait_for_api_ready_in_container(backend, variant=variant, env_overrides=env_overrides)
        pool_config = inspect_api_pool_config(backend, variant=variant, env_overrides=env_overrides)
        run_compose(
            backend,
            repo_root=variant.repo_root,
            env_overrides=env_overrides,
            compose_args=[
                *compose_prefix,
                "run",
                "--rm",
                "--no-deps",
                "-v",
                f"{workspace_mount}:/workspace",
                "api",
                "python",
                "/workspace/scripts/homologate_temp_011_phase6_backend_db_validation.py",
                "--client-mode",
                "--client-phase",
                "seed",
                "--base-url",
                "http://api:8000",
                "--bulk-users-per-state",
                str(users_per_state),
                "--report-path",
                f"/workspace/.copilot-temp/{client_report_path.name}",
            ],
        )

        suite_before_pg = query_pg_stat_activity(backend, variant=variant, env_overrides=env_overrides)

        run_compose(
            backend,
            repo_root=variant.repo_root,
            env_overrides=env_overrides,
            compose_args=[
                *compose_prefix,
                "run",
                "--rm",
                "--no-deps",
                "-v",
                f"{workspace_mount}:/workspace",
                "api",
                "python",
                "/workspace/scripts/homologate_temp_011_phase6_backend_db_validation.py",
                "--client-mode",
                "--client-phase",
                "measure",
                "--base-url",
                "http://api:8000",
                "--samples",
                str(samples),
                "--warmup-requests",
                str(warmup_requests),
                "--concurrency",
                str(concurrency),
                "--report-path",
                f"/workspace/.copilot-temp/{client_report_path.name}",
            ],
        )

        suite_after_pg = query_pg_stat_activity(backend, variant=variant, env_overrides=env_overrides)
        client_report = json.loads(client_report_path.read_text(encoding="utf-8"))

        return {
            "variant": variant.name,
            "git_label": variant.git_label,
            "repo_root": str(variant.repo_root),
            "compose_project_name": variant.compose_project_name,
            "compose_backend": backend.description,
            "base_url": "http://api:8000",
            "pool_config": pool_config,
            "suite_before_pg_stat_activity": suite_before_pg,
            "suite_before_diagnostics": client_report.get("suite_before_diagnostics"),
            "suite_after_pg_stat_activity": suite_after_pg,
            "suite_after_diagnostics": client_report.get("suite_after_diagnostics"),
            "routes": client_report.get("routes", []),
        }
    finally:
        run_compose(
            backend,
            repo_root=variant.repo_root,
            env_overrides=env_overrides,
            compose_args=[*compose_prefix, "down", "-v", "--remove-orphans"],
            capture_output=True,
        )
        if client_report_path.exists():
            client_report_path.unlink()


def build_route_comparison(before_variant: dict[str, object], after_variant: dict[str, object]) -> list[dict[str, object]]:
    before_routes = {item["route"]: item for item in before_variant["routes"]}
    comparisons: list[dict[str, object]] = []
    for after_item in after_variant["routes"]:
        route_name = str(after_item["route"])
        before_item = before_routes[route_name]
        before_latency = dict(before_item["latency_ms"])
        after_latency = dict(after_item["latency_ms"])
        comparisons.append(
            {
                "route": route_name,
                "path": after_item["path"],
                "before_latency_ms": before_latency,
                "after_latency_ms": after_latency,
                "delta_p50_ms": round(after_latency["p50_ms"] - before_latency["p50_ms"], 2),
                "delta_p95_ms": round(after_latency["p95_ms"] - before_latency["p95_ms"], 2),
                "delta_p99_ms": round(after_latency["p99_ms"] - before_latency["p99_ms"], 2),
                "before_queries_per_request": before_item.get("queries_per_request"),
                "after_queries_per_request": after_item.get("queries_per_request"),
                "before_pg_stat_activity_after": before_item.get("pg_stat_activity_after"),
                "after_pg_stat_activity_after": after_item.get("pg_stat_activity_after"),
            }
        )
    return comparisons


def build_tradeoffs(route_comparisons: list[dict[str, object]]) -> list[dict[str, object]]:
    tradeoffs: list[dict[str, object]] = []
    for item in route_comparisons:
        regressions = []
        if item["delta_p50_ms"] > 0:
            regressions.append(f"p50 +{item['delta_p50_ms']} ms")
        if item["delta_p95_ms"] > 0:
            regressions.append(f"p95 +{item['delta_p95_ms']} ms")
        if item["delta_p99_ms"] > 0:
            regressions.append(f"p99 +{item['delta_p99_ms']} ms")
        improvements = []
        if item["delta_p50_ms"] < 0:
            improvements.append(f"p50 {item['delta_p50_ms']} ms")
        if item["delta_p95_ms"] < 0:
            improvements.append(f"p95 {item['delta_p95_ms']} ms")
        if item["delta_p99_ms"] < 0:
            improvements.append(f"p99 {item['delta_p99_ms']} ms")
        if improvements or regressions:
            tradeoffs.append(
                {
                    "route": item["route"],
                    "improvements": improvements,
                    "regressions": regressions,
                }
            )
    return tradeoffs


def build_connection_comparison(before_variant: dict[str, object], after_variant: dict[str, object]) -> dict[str, object]:
    return {
        "before_head": {
            "pool_config": before_variant.get("pool_config"),
            "suite_before_pg_stat_activity": before_variant.get("suite_before_pg_stat_activity"),
            "suite_after_pg_stat_activity": before_variant.get("suite_after_pg_stat_activity"),
            "suite_before_diagnostics": before_variant.get("suite_before_diagnostics"),
            "suite_after_diagnostics": before_variant.get("suite_after_diagnostics"),
        },
        "after_worktree": {
            "pool_config": after_variant.get("pool_config"),
            "suite_before_pg_stat_activity": after_variant.get("suite_before_pg_stat_activity"),
            "suite_after_pg_stat_activity": after_variant.get("suite_after_pg_stat_activity"),
            "suite_before_diagnostics": after_variant.get("suite_before_diagnostics"),
            "suite_after_diagnostics": after_variant.get("suite_after_diagnostics"),
        },
    }


async def run_measurement(args: argparse.Namespace) -> dict[str, object]:
    backend = resolve_compose_backend()
    selected_variants = set(args.variant or [])
    variants = build_variant_configs(selected_variants or None)

    try:
        variant_reports = []
        for variant in variants:
            variant_reports.append(
                await benchmark_variant(
                    backend,
                    variant=variant,
                    samples=args.samples,
                    warmup_requests=args.warmup_requests,
                    concurrency=args.concurrency,
                    users_per_state=args.bulk_users_per_state,
                )
            )
    finally:
        cleanup_head_worktree(ROOT, HEAD_WORKTREE_PATH)

    report: dict[str, object] = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "head_commit": git_head_commit(ROOT),
        "compose_backend": backend.description,
        "benchmark_config": {
            "samples_per_route": args.samples,
            "warmup_requests_per_route": args.warmup_requests,
            "concurrency_per_route": args.concurrency,
            "bulk_users_per_state": args.bulk_users_per_state,
        },
        "variants": variant_reports,
    }

    reports_by_name = {item["variant"]: item for item in variant_reports}
    if "before_head" in reports_by_name and "after_worktree" in reports_by_name:
        route_comparisons = build_route_comparison(
            reports_by_name["before_head"],
            reports_by_name["after_worktree"],
        )
        report["comparison"] = {
            "routes": route_comparisons,
            "connection_usage": build_connection_comparison(
                reports_by_name["before_head"],
                reports_by_name["after_worktree"],
            ),
            "tradeoffs": build_tradeoffs(route_comparisons),
        }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


async def run_client_mode(args: argparse.Namespace) -> dict[str, object]:
    if not args.base_url:
        raise RuntimeError("--base-url is required in --client-mode")
    if args.client_phase == "seed":
        await seed_benchmark_data(args.base_url, users_per_state=args.bulk_users_per_state)
        report = {"phase": "seed", "ok": True}
    elif args.client_phase == "measure":
        report = await measure_http_suite(
            base_url=args.base_url,
            samples=args.samples,
            warmup_requests=args.warmup_requests,
            concurrency=args.concurrency,
        )
        report["phase"] = "measure"
    else:
        raise RuntimeError("--client-phase must be one of: seed, measure")

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    args = parse_args()
    if args.client_mode:
        report = asyncio.run(run_client_mode(args))
    else:
        report = asyncio.run(run_measurement(args))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()