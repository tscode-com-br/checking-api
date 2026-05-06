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
| Requests/s | 5.87 |
| Failures/s | 5.87 |
| Median latency ms | 10.00 |
| p50 latency ms | 11.00 |
| p95 latency ms | 120.00 |
| p99 latency ms | 120.00 |
| Max latency ms | 120.83 |

## Snapshot comparison

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Health ready | yes | yes | n/a |
| Health overall status | ok | ok | n/a |
| Forms backlog | n/a | n/a | n/a |
| Forms failed count | n/a | n/a | n/a |
| Forms worker stale | n/a | n/a | n/a |
| DB checked out | n/a | n/a | n/a |
| DB current open connections | n/a | n/a | n/a |
| DB recent p95 query ms | n/a | n/a | n/a |
| Host CPU percent | 17.10 | 18.50 | +1.40 |
| Host memory percent | 84.30 | 86.90 | +2.60 |

## Blocking references

- Locust returned a non-zero exit code. Stop the rollout and re-check the scenario contract in docs/incidents/2026-05-06-504-phase10-load-harness.md.
- HTTP failures were observed during the load run. Stop the rollout and re-check the readiness gates and HTTP runtime baseline in docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md.

## Evidence to preserve

- `phase10_<profile>_stats.csv`
- `phase10_<profile>.html`
- `phase10_<profile>.stdout.log` and `phase10_<profile>.stderr.log`
- `phase10_<profile>.command.txt`
- `phase10_<profile>_before_snapshot.json`
- `phase10_<profile>_after_snapshot.json`
- `phase10_<profile>_before_after.json`
