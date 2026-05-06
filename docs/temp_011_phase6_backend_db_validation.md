# Temp 011 - Phase 6 backend/database validation

Source data: `docs/temp_011_phase6_backend_db_validation_report.json`

## Scope

- Benchmark target: `docker-compose.api.yml` in WSL Ubuntu via `docker compose`
- Baseline: `HEAD` at `2c7b322c6c5c636a098b1905262c7bfddb0b9919`
- Candidate: current working tree
- Measured routes:
  - `GET /api/web/check/state`
  - `GET /api/mobile/state`
  - `POST /api/admin/checkin`
  - `POST /api/admin/checkout`
  - `GET /api/admin/projects`
- Load profile:
  - 40 measured requests per route
  - 3 warmup requests per route
  - concurrency 6
  - 60 seeded admin users per state bucket

## Latency results

| Route | Before p50 | After p50 | Delta | Before p95 | After p95 | Delta | Before p99 | After p99 | Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/api/web/check/state` | 85.32 ms | 12.95 ms | -72.37 ms | 111.95 ms | 36.51 ms | -75.44 ms | 117.63 ms | 44.45 ms | -73.18 ms |
| `/api/mobile/state` | 102.15 ms | 12.78 ms | -89.37 ms | 133.01 ms | 22.69 ms | -110.32 ms | 152.85 ms | 23.73 ms | -129.12 ms |
| `/api/admin/checkin` | 7486.56 ms | 220.38 ms | -7266.18 ms | 11662.35 ms | 257.67 ms | -11404.68 ms | 11752.24 ms | 269.29 ms | -11482.95 ms |
| `/api/admin/checkout` | 8194.28 ms | 215.44 ms | -7978.84 ms | 16200.72 ms | 255.99 ms | -15944.73 ms | 16851.83 ms | 352.83 ms | -16499.00 ms |
| `/api/admin/projects` | 26.39 ms | 23.54 ms | -2.85 ms | 41.01 ms | 35.97 ms | -5.04 ms | 56.88 ms | 37.76 ms | -19.12 ms |

Result: every measured hot route improved. No route showed a p50, p95, or p99 regression in this run.

## Database connection usage

### Pool configuration

| Variant | Pool size | Max overflow | Pool timeout | Pool recycle |
| --- | ---: | ---: | ---: | ---: |
| `before_head` | 5 | 10 | 30 s | disabled (`-1`) |
| `after_worktree` | 6 | 2 | 5 s | 1800 s |

### Server-side connections from `pg_stat_activity`

| Variant | Before suite total | After suite total | Active after suite | Waiting after suite |
| --- | ---: | ---: | ---: | ---: |
| `before_head` | 1 | 5 | 0 | 0 |
| `after_worktree` | 7 | 15 | 0 | 0 |

### In-process diagnostics available only in `after_worktree`

The current worktree exposes `GET /api/admin/diagnostics/database`, so it can report pool internals that do not exist in `before_head`.

| Metric | Before suite | After suite |
| --- | ---: | ---: |
| `current_open_connections` | 1 | 6 |
| `open_connections_high_watermark` | 1 | 8 |
| `checked_out_high_watermark` | 1 | 7 |
| `total_connect_events` | 1 | 12 |

Observed behavior:

- Outside the diagnostics request itself, `pg_stat_activity.active_database_connections` returned to `0` after the suite in both variants.
- In the current worktree diagnostics snapshots, `checked_out=1` is expected because the diagnostics endpoint includes its own request while sampling the pool.
- The current worktree kept more PostgreSQL connections open after the suite than `before_head`, even with the tighter pool ceiling.

## Route-level query usage in `after_worktree`

The diagnostics route lets the current worktree estimate per-request query counts during the run.

| Route | Queries per request |
| --- | ---: |
| `/api/web/check/state` | 2.0 |
| `/api/mobile/state` | 1.5 |
| `/api/admin/checkin` | 6.0 |
| `/api/admin/checkout` | 6.0 |
| `/api/admin/projects` | 2.0 |

`before_head` cannot provide the same breakdown because it does not expose the diagnostics endpoint used by the harness.

## Tradeoff summary

- No latency tradeoff was observed between the measured hot routes. All five routes improved on p50, p95, and p99.
- A database footprint tradeoff was observed: the current worktree finished the suite with a higher observed PostgreSQL connection count (`15` total in `pg_stat_activity`) than `before_head` (`5` total), while still keeping `active` and `waiting` counts at `0` after the load stopped.
- Interpreting that tradeoff: the optimization pass removed large route latencies, especially on admin check-in and check-out, but the tuned runtime now retains more pooled connections resident on the server under this benchmark profile.

## Conclusion

Phase 6 produced clear latency wins across all measured hot routes, with the largest gains on `admin_checkin` and `admin_checkout`. The remaining caution is not route regression; it is connection residency. Any rollout decision should preserve the latency improvements and separately confirm that the higher steady-state Postgres connection footprint is acceptable for the production deployment budget.