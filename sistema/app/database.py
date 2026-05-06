from dataclasses import dataclass
import json
import logging
import threading
from collections import Counter, deque
from contextvars import ContextVar
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .core.config import settings


DATABASE_HOT_PATHS = (
    "/api/web/check/state",
    "/api/mobile/state",
    "/api/admin/checkin",
    "/api/admin/checkout",
    "/api/admin/projects",
)
DATABASE_RECENT_QUERY_SAMPLE_SIZE = 500
DATABASE_SLOW_QUERY_LOG_THRESHOLD_MS = 250
DATABASE_POOL_USAGE_WARNING_RATIO = 0.8
DATABASE_POOL_USAGE_CRITICAL_RATIO = 1.0
DATABASE_RECENT_QUERY_P95_WARNING_MS = 150
DATABASE_RECENT_QUERY_P95_CRITICAL_MS = 300
DATABASE_POSTGRES_ACTIVE_CONNECTIONS_WARNING = 24
DATABASE_POSTGRES_ACTIVE_CONNECTIONS_CRITICAL = 32
DATABASE_POSTGRES_WAITING_CONNECTIONS_WARNING = 1
DATABASE_POSTGRES_WAITING_CONNECTIONS_CRITICAL = 3
DATABASE_POSTGRES_IDLE_IN_TRANSACTION_WARNING = 1
DATABASE_TELEMETRY_LOGGER = logging.getLogger("checking.db")
_DATABASE_REQUEST_ID: ContextVar[str | None] = ContextVar("database_request_id", default=None)
_DATABASE_REQUEST_PATH: ContextVar[str | None] = ContextVar("database_request_path", default=None)


@dataclass(frozen=True)
class DatabasePoolConfig:
    pool_size: int | None
    max_overflow: int | None
    pool_timeout_seconds: int | None
    pool_recycle_seconds: int | None
    pool_pre_ping: bool = True


def _require_positive_integer(value: int, *, name: str) -> int:
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def _require_non_negative_integer(value: int, *, name: str) -> int:
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater")
    return value


def resolve_database_pool_config(
    *,
    database_url: str,
    pool_size: int,
    max_overflow: int,
    pool_timeout_seconds: int,
    pool_recycle_seconds: int,
) -> DatabasePoolConfig:
    backend_name = make_url(database_url).get_backend_name()
    if backend_name == "sqlite":
        return DatabasePoolConfig(
            pool_size=None,
            max_overflow=None,
            pool_timeout_seconds=None,
            pool_recycle_seconds=None,
        )

    return DatabasePoolConfig(
        pool_size=_require_positive_integer(pool_size, name="DATABASE_POOL_SIZE"),
        max_overflow=_require_non_negative_integer(max_overflow, name="DATABASE_MAX_OVERFLOW"),
        pool_timeout_seconds=_require_positive_integer(
            pool_timeout_seconds,
            name="DATABASE_POOL_TIMEOUT_SECONDS",
        ),
        pool_recycle_seconds=_require_positive_integer(
            pool_recycle_seconds,
            name="DATABASE_POOL_RECYCLE_SECONDS",
        ),
    )


def build_database_engine_kwargs(pool_config: DatabasePoolConfig) -> dict[str, object]:
    kwargs: dict[str, object] = {"pool_pre_ping": pool_config.pool_pre_ping}
    if pool_config.pool_size is not None:
        kwargs["pool_size"] = pool_config.pool_size
    if pool_config.max_overflow is not None:
        kwargs["max_overflow"] = pool_config.max_overflow
    if pool_config.pool_timeout_seconds is not None:
        kwargs["pool_timeout"] = pool_config.pool_timeout_seconds
    if pool_config.pool_recycle_seconds is not None:
        kwargs["pool_recycle"] = pool_config.pool_recycle_seconds
    return kwargs


class DatabaseTelemetryState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.query_count_total = 0
        self.query_error_count_total = 0
        self.slow_query_count_total = 0
        self.query_time_ms_total = 0
        self.recent_query_durations_ms: deque[int] = deque(maxlen=DATABASE_RECENT_QUERY_SAMPLE_SIZE)
        self.recent_query_samples: deque[tuple[str | None, int]] = deque(maxlen=DATABASE_RECENT_QUERY_SAMPLE_SIZE)
        self.query_count_by_path_total: Counter[str] = Counter()
        self.current_open_connections = 0
        self.open_connections_high_watermark = 0
        self.total_connect_events = 0
        self.total_close_events = 0
        self.current_checked_out = 0
        self.checked_out_high_watermark = 0
        self.total_checkout_events = 0
        self.total_checkin_events = 0

    def record_query(self, *, path: str | None, duration_ms: int, failed: bool) -> None:
        normalized_path = path or "background"
        with self._lock:
            self.query_count_total += 1
            if failed:
                self.query_error_count_total += 1
            self.query_time_ms_total += duration_ms
            self.recent_query_durations_ms.append(duration_ms)
            self.recent_query_samples.append((normalized_path, duration_ms))
            self.query_count_by_path_total[normalized_path] += 1
            if duration_ms >= DATABASE_SLOW_QUERY_LOG_THRESHOLD_MS:
                self.slow_query_count_total += 1

    def record_connect(self) -> None:
        with self._lock:
            self.total_connect_events += 1
            self.current_open_connections += 1
            self.open_connections_high_watermark = max(
                self.open_connections_high_watermark,
                self.current_open_connections,
            )

    def record_close(self) -> None:
        with self._lock:
            self.total_close_events += 1
            self.current_open_connections = max(self.current_open_connections - 1, 0)

    def record_checkout(self) -> None:
        with self._lock:
            self.total_checkout_events += 1
            self.current_checked_out += 1
            self.checked_out_high_watermark = max(self.checked_out_high_watermark, self.current_checked_out)

    def record_checkin(self) -> None:
        with self._lock:
            self.total_checkin_events += 1
            self.current_checked_out = max(self.current_checked_out - 1, 0)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "query_count_total": self.query_count_total,
                "query_error_count_total": self.query_error_count_total,
                "slow_query_count_total": self.slow_query_count_total,
                "query_time_ms_total": self.query_time_ms_total,
                "recent_query_durations_ms": list(self.recent_query_durations_ms),
                "recent_query_samples": list(self.recent_query_samples),
                "query_count_by_path_total": dict(self.query_count_by_path_total),
                "current_open_connections": self.current_open_connections,
                "open_connections_high_watermark": self.open_connections_high_watermark,
                "total_connect_events": self.total_connect_events,
                "total_close_events": self.total_close_events,
                "current_checked_out": self.current_checked_out,
                "checked_out_high_watermark": self.checked_out_high_watermark,
                "total_checkout_events": self.total_checkout_events,
                "total_checkin_events": self.total_checkin_events,
            }


def _percentile_ms(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(((len(ordered) * percentile + 99) // 100) - 1, 0)
    return ordered[index]


def _recent_latency_summary(values: list[int]) -> dict[str, int | None]:
    if not values:
        return {
            "recent_average_query_ms": None,
            "recent_p95_query_ms": None,
        }
    return {
        "recent_average_query_ms": int(sum(values) / len(values)),
        "recent_p95_query_ms": _percentile_ms(values, 95),
    }


def _pool_stat(method_name: str) -> int | None:
    method = getattr(engine.pool, method_name, None)
    if not callable(method):
        return None
    value = method()
    return value if isinstance(value, int) else None


def _normalize_query_path(path: str | None) -> str:
    return path or "background"


def _sql_operation(statement: str | None) -> str:
    normalized = str(statement or "").lstrip()
    if not normalized:
        return "UNKNOWN"
    return normalized.split(None, 1)[0].upper()


def _pool_snapshot() -> dict[str, object]:
    telemetry_snapshot = _database_telemetry.snapshot()
    configured_pool_size = _pool_stat("size")
    configured_max_overflow = getattr(engine.pool, "_max_overflow", None)
    if not isinstance(configured_max_overflow, int):
        configured_max_overflow = None

    checked_out = _pool_stat("checkedout")
    checked_in = _pool_stat("checkedin")
    current_overflow = _pool_stat("overflow")
    total_capacity = None
    usage_ratio = None
    saturation = "unknown"
    if (
        checked_out is not None
        and configured_pool_size is not None
        and configured_max_overflow is not None
        and configured_max_overflow >= 0
    ):
        total_capacity = configured_pool_size + configured_max_overflow
        if total_capacity > 0:
            usage_ratio = round(checked_out / total_capacity, 3)
            if usage_ratio >= DATABASE_POOL_USAGE_CRITICAL_RATIO:
                saturation = "critical"
            elif usage_ratio >= DATABASE_POOL_USAGE_WARNING_RATIO:
                saturation = "warning"
            else:
                saturation = "normal"
    elif checked_out is not None:
        saturation = "normal"

    return {
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
        "pool_class": type(engine.pool).__name__,
        "status": engine.pool.status() if hasattr(engine.pool, "status") else None,
        "configured_pool_size": configured_pool_size,
        "configured_max_overflow": configured_max_overflow,
        "configured_pool_timeout_seconds": DATABASE_POOL_CONFIG.pool_timeout_seconds,
        "configured_pool_recycle_seconds": DATABASE_POOL_CONFIG.pool_recycle_seconds,
        "pool_pre_ping": DATABASE_POOL_CONFIG.pool_pre_ping,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "current_overflow": current_overflow,
        "total_capacity": total_capacity,
        "usage_ratio": usage_ratio,
        "saturation": saturation,
        "checked_out_high_watermark": telemetry_snapshot["checked_out_high_watermark"],
        "current_open_connections": telemetry_snapshot["current_open_connections"],
        "open_connections_high_watermark": telemetry_snapshot["open_connections_high_watermark"],
        "total_connect_events": telemetry_snapshot["total_connect_events"],
        "total_close_events": telemetry_snapshot["total_close_events"],
        "total_checkout_events": telemetry_snapshot["total_checkout_events"],
        "total_checkin_events": telemetry_snapshot["total_checkin_events"],
    }


def _hot_path_latency_summary(telemetry_snapshot: dict[str, object]) -> list[dict[str, object]]:
    recent_query_samples = telemetry_snapshot["recent_query_samples"]
    total_counts_by_path = telemetry_snapshot["query_count_by_path_total"]
    hot_paths: list[dict[str, object]] = []
    for path in DATABASE_HOT_PATHS:
        recent_values = [duration_ms for sample_path, duration_ms in recent_query_samples if sample_path == path]
        hot_paths.append(
            {
                "path": path,
                "recent_query_count": len(recent_values),
                "recent_average_query_ms": _recent_latency_summary(recent_values)["recent_average_query_ms"],
                "recent_p95_query_ms": _recent_latency_summary(recent_values)["recent_p95_query_ms"],
                "total_query_count": total_counts_by_path.get(path, 0),
            }
        )
    return hot_paths


def _recommended_alert_thresholds() -> dict[str, int | float]:
    return {
        "pool_usage_warning_ratio": DATABASE_POOL_USAGE_WARNING_RATIO,
        "pool_usage_critical_ratio": DATABASE_POOL_USAGE_CRITICAL_RATIO,
        "recent_query_p95_warning_ms": DATABASE_RECENT_QUERY_P95_WARNING_MS,
        "recent_query_p95_critical_ms": DATABASE_RECENT_QUERY_P95_CRITICAL_MS,
        "slow_query_log_threshold_ms": DATABASE_SLOW_QUERY_LOG_THRESHOLD_MS,
        "postgres_active_connections_warning": DATABASE_POSTGRES_ACTIVE_CONNECTIONS_WARNING,
        "postgres_active_connections_critical": DATABASE_POSTGRES_ACTIVE_CONNECTIONS_CRITICAL,
        "postgres_waiting_connections_warning": DATABASE_POSTGRES_WAITING_CONNECTIONS_WARNING,
        "postgres_waiting_connections_critical": DATABASE_POSTGRES_WAITING_CONNECTIONS_CRITICAL,
        "postgres_idle_in_transaction_warning": DATABASE_POSTGRES_IDLE_IN_TRANSACTION_WARNING,
    }


def _server_connection_counts(*, db: Session) -> dict[str, object]:
    if engine.dialect.name != "postgresql":
        return {
            "source": "unsupported",
            "database_connections_total": None,
            "active_database_connections": None,
            "waiting_database_connections": None,
            "idle_in_transaction_connections": None,
            "error": f"unsupported_dialect:{engine.dialect.name}",
        }

    try:
        row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE state = 'active') AS active,
                    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL AND state <> 'idle') AS waiting,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database()
                """
            )
        ).mappings().one()
        return {
            "source": "pg_stat_activity",
            "database_connections_total": int(row["total"]),
            "active_database_connections": int(row["active"]),
            "waiting_database_connections": int(row["waiting"]),
            "idle_in_transaction_connections": int(row["idle_in_transaction"]),
            "error": None,
        }
    except Exception as exc:
        return {
            "source": "pg_stat_activity_error",
            "database_connections_total": None,
            "active_database_connections": None,
            "waiting_database_connections": None,
            "idle_in_transaction_connections": None,
            "error": str(exc)[:300],
        }


def set_database_request_context(*, request_id: str | None, path: str | None) -> tuple[object, object]:
    return (
        _DATABASE_REQUEST_ID.set(request_id),
        _DATABASE_REQUEST_PATH.set(path),
    )


def reset_database_request_context(tokens: tuple[object, object]) -> None:
    request_id_token, request_path_token = tokens
    _DATABASE_REQUEST_ID.reset(request_id_token)
    _DATABASE_REQUEST_PATH.reset(request_path_token)


def get_database_diagnostics(*, db: Session) -> dict[str, object]:
    telemetry_snapshot = _database_telemetry.snapshot()
    recent_values = telemetry_snapshot["recent_query_durations_ms"]
    recent_latency_summary = _recent_latency_summary(recent_values)
    return {
        "generated_at": datetime.now(UTC),
        "pool": _pool_snapshot(),
        "latency": {
            "query_count_total": telemetry_snapshot["query_count_total"],
            "query_error_count_total": telemetry_snapshot["query_error_count_total"],
            "slow_query_count_total": telemetry_snapshot["slow_query_count_total"],
            "query_time_ms_total": telemetry_snapshot["query_time_ms_total"],
            "recent_query_sample_size": len(recent_values),
            "recent_average_query_ms": recent_latency_summary["recent_average_query_ms"],
            "recent_p95_query_ms": recent_latency_summary["recent_p95_query_ms"],
            "hot_paths": _hot_path_latency_summary(telemetry_snapshot),
        },
        "server_connections": _server_connection_counts(db=db),
        "recommended_alert_thresholds": _recommended_alert_thresholds(),
    }


def _log_slow_query(*, duration_ms: int, statement: str | None, rowcount: int | None, failed: bool, error: str | None = None) -> None:
    DATABASE_TELEMETRY_LOGGER.warning(
        json.dumps(
            {
                "database_dialect": engine.dialect.name,
                "error": error,
                "event": "db_query_slow",
                "failed": failed,
                "latency_ms": duration_ms,
                "path": _normalize_query_path(_DATABASE_REQUEST_PATH.get()),
                "request_id": _DATABASE_REQUEST_ID.get(),
                "rowcount": rowcount,
                "sql_operation": _sql_operation(statement),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )


DATABASE_POOL_CONFIG = resolve_database_pool_config(
    database_url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout_seconds=settings.database_pool_timeout_seconds,
    pool_recycle_seconds=settings.database_pool_recycle_seconds,
)
engine = create_engine(
    settings.database_url,
    **build_database_engine_kwargs(DATABASE_POOL_CONFIG),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
_database_telemetry = DatabaseTelemetryState()


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    context._database_telemetry_started_at = perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    started_at = getattr(context, "_database_telemetry_started_at", None)
    if started_at is None:
        return
    duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
    _database_telemetry.record_query(
        path=_DATABASE_REQUEST_PATH.get(),
        duration_ms=duration_ms,
        failed=False,
    )
    if duration_ms >= DATABASE_SLOW_QUERY_LOG_THRESHOLD_MS:
        _log_slow_query(
            duration_ms=duration_ms,
            statement=statement,
            rowcount=getattr(cursor, "rowcount", None),
            failed=False,
        )


@event.listens_for(engine, "handle_error")
def _handle_error(exception_context) -> None:
    execution_context = exception_context.execution_context
    started_at = getattr(execution_context, "_database_telemetry_started_at", None) if execution_context else None
    duration_ms = max(int((perf_counter() - started_at) * 1000), 0) if started_at is not None else 0
    _database_telemetry.record_query(
        path=_DATABASE_REQUEST_PATH.get(),
        duration_ms=duration_ms,
        failed=True,
    )
    if duration_ms >= DATABASE_SLOW_QUERY_LOG_THRESHOLD_MS:
        _log_slow_query(
            duration_ms=duration_ms,
            statement=exception_context.statement,
            rowcount=None,
            failed=True,
            error=str(exception_context.original_exception)[:300],
        )


@event.listens_for(engine, "connect")
def _connect(dbapi_connection, connection_record) -> None:
    _database_telemetry.record_connect()


@event.listens_for(engine, "close")
def _close(dbapi_connection, connection_record) -> None:
    _database_telemetry.record_close()


@event.listens_for(engine, "checkout")
def _checkout(dbapi_connection, connection_record, connection_proxy) -> None:
    _database_telemetry.record_checkout()


@event.listens_for(engine, "checkin")
def _checkin(dbapi_connection, connection_record) -> None:
    _database_telemetry.record_checkin()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
