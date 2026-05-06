from __future__ import annotations

import json

from .services.forms_queue import get_forms_worker_health_failure_reason, get_forms_worker_observed_snapshot


def main() -> int:
    snapshot = get_forms_worker_observed_snapshot()
    failure_reason = get_forms_worker_health_failure_reason(snapshot)
    payload = {
        "reason": failure_reason,
        "status": "ok" if failure_reason is None else "unhealthy",
        "worker": {
            "consecutive_error_count": snapshot.get("consecutive_error_count"),
            "heartbeat_age_seconds": snapshot.get("heartbeat_age_seconds"),
            "restart_count": snapshot.get("restart_count"),
            "running": snapshot.get("running"),
            "stale": snapshot.get("stale"),
            "status": snapshot.get("status"),
        },
    }
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0 if failure_reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())