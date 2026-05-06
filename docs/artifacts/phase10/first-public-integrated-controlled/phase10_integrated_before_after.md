# Phase 10 before/after report - integrated

## Outcome

- Status: BLOCKED
- Base URL: `https://tscode.com.br`
- Locust exit code: `1`

## Load summary

| Metric | Value |
| --- | ---: |
| Request count | 657 |
| Failure count | 101 |
| Requests/s | 4.89 |
| Failures/s | 0.75 |
| Median latency ms | 350.00 |
| p50 latency ms | 350.00 |
| p95 latency ms | 60000.00 |
| p99 latency ms | 60000.00 |
| Max latency ms | 60203.34 |

## Snapshot comparison

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Health ready | n/a | n/a | n/a |
| Health overall status | n/a | n/a | n/a |
| Forms backlog | n/a | n/a | n/a |
| Forms failed count | n/a | n/a | n/a |
| Forms worker running | n/a | n/a | n/a |
| Forms worker stale | n/a | n/a | n/a |
| DB checked out | n/a | n/a | n/a |
| DB current open connections | n/a | n/a | n/a |
| DB recent p95 query ms | n/a | n/a | n/a |
| Host CPU percent | n/a | n/a | n/a |
| Host memory percent | n/a | n/a | n/a |

## Capture notes

- Host CPU and memory capture only runs automatically for local targets.

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
