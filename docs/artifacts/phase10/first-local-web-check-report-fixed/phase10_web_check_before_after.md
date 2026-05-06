# Phase 10 before/after report - web-check

## Outcome

- Status: BLOCKED
- Base URL: `http://127.0.0.1:8000`
- Locust exit code: `1`

## Load summary

| Metric | Value |
| --- | ---: |
| Request count | 6 |
| Failure count | 6 |
| Requests/s | 5.85 |
| Failures/s | 5.85 |
| Median latency ms | 11.00 |
| p50 latency ms | 13.00 |
| p95 latency ms | 33.00 |
| p99 latency ms | 33.00 |
| Max latency ms | 32.75 |

## Snapshot comparison

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Health ready | yes | yes | n/a |
| Health overall status | ok | ok | n/a |
| Forms backlog | 7 | 7 | +0 |
| Forms failed count | 0 | 0 | +0 |
| Forms worker running | no | no | n/a |
| Forms worker stale | no | no | n/a |
| DB checked out | 1 | 1 | +0 |
| DB current open connections | 1 | 1 | +0 |
| DB recent p95 query ms | 1 | 1 | +0 |
| Host CPU percent | 8.50 | 12.30 | +3.80 |
| Host memory percent | 81.40 | 84.20 | +2.80 |

## Blocking references

- Locust returned a non-zero exit code. Stop the rollout and re-check the scenario contract in docs/incidents/2026-05-06-504-phase10-load-harness.md.
- HTTP failures were observed during the load run. Stop the rollout and re-check the readiness gates and HTTP runtime baseline in docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md.
- The Forms worker became stale or stopped running under load. Stop the rollout and use the rollback evidence matrix in docs/incidents/2026-05-05-504-phase9-deploy-rollback.md.

## Evidence to preserve

- `phase10_<profile>_stats.csv`
- `phase10_<profile>.html`
- `phase10_<profile>.stdout.log` and `phase10_<profile>.stderr.log`
- `phase10_<profile>.command.txt`
- `phase10_<profile>_before_snapshot.json`
- `phase10_<profile>_after_snapshot.json`
- `phase10_<profile>_before_after.json`
