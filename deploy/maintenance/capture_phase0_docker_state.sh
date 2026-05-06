#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  capture_phase0_docker_state.sh <evidence_dir> [stack_dir]

Examples:
  ./capture_phase0_docker_state.sh /root/checkcheck_incidents/2026-05-04-504-phase0
  ./capture_phase0_docker_state.sh /root/checkcheck_incidents/2026-05-04-504-phase0 /root/checkcheck
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 64
fi

evidence_dir="$1"
stack_dir_override="${2:-}"
mkdir -p "$evidence_dir"

declare -a failed_files=()

capture_command() {
  local filename="$1"
  shift

  local status=0
  {
    printf 'COMMAND:'
    for token in "$@"; do
      printf ' %q' "$token"
    done
    printf '\n\n'
    "$@" || status=$?
    printf '\nEXIT_CODE: %s\n' "$status"
  } >"$evidence_dir/$filename" 2>&1

  if [[ $status -ne 0 ]]; then
    failed_files+=("$filename:$status")
  fi

  return 0
}

choose_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
    return 0
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose'
    return 0
  fi

  return 1
}

detect_stack_dir() {
  local container_name
  local candidate

  for container_name in checkcheck-app-1 checkcheck-db-1; do
    candidate="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$container_name" 2>/dev/null || true)"
    if [[ -n "$candidate" && -d "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done

  return 1
}

extract_state_report() {
  local container_name="$1"
  docker inspect --format '
State.Status={{ .State.Status }}
State.Running={{ .State.Running }}
State.Health.Status={{ if .State.Health }}{{ .State.Health.Status }}{{ else }}n/a{{ end }}
RestartCount={{ .RestartCount }}
StartedAt={{ .State.StartedAt }}
FinishedAt={{ .State.FinishedAt }}
OOMKilled={{ .State.OOMKilled }}
Health.Log:
{{- if .State.Health }}
{{- range .State.Health.Log }}
- Start={{ .Start }} End={{ .End }} ExitCode={{ .ExitCode }} Output={{ printf "%q" .Output }}
{{- end }}
{{- else }}
- n/a
{{- end }}
' "$container_name"
}

classify_app_state() {
  local state_status="$1"
  local health_status="$2"
  local restart_count="$3"

  if [[ "$state_status" == "restarting" ]]; then
    printf 'reiniciando'
    return 0
  fi

  if [[ "$health_status" == "healthy" ]]; then
    printf 'healthy'
    return 0
  fi

  if [[ "$health_status" == "unhealthy" ]]; then
    printf 'unhealthy'
    return 0
  fi

  if [[ "$state_status" == "running" && "$health_status" == "starting" ]]; then
    printf 'apenas vivo sem responder utilmente'
    return 0
  fi

  if [[ "$state_status" == "running" && "$health_status" == "n/a" ]]; then
    printf 'apenas vivo sem responder utilmente'
    return 0
  fi

  if [[ "$state_status" == "running" && "$restart_count" != "0" ]]; then
    printf 'apenas vivo sem responder utilmente'
    return 0
  fi

  printf '%s' "$state_status"
}

compose_cmd="$(choose_compose_cmd || true)"
stack_dir=""

if [[ -n "$stack_dir_override" ]]; then
  stack_dir="$stack_dir_override"
elif stack_dir="$(detect_stack_dir)"; then
  :
else
  stack_dir=""
fi

log "Writing Docker/container evidence to $evidence_dir"

{
  printf 'stack_dir=%s\n' "${stack_dir:-unknown}"
  printf 'compose_command=%s\n' "${compose_cmd:-unavailable}"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >"$evidence_dir/11_stack_directory.txt"

capture_command "12_docker_ps_no_trunc.txt" docker ps --no-trunc
capture_command "13_docker_inspect_checkcheck_app_1.txt" docker inspect checkcheck-app-1
capture_command "14_docker_inspect_checkcheck_db_1.txt" docker inspect checkcheck-db-1
capture_command "15_docker_logs_checkcheck_app_1_tail_500.txt" docker logs --tail 500 checkcheck-app-1
capture_command "16_docker_logs_checkcheck_db_1_tail_200.txt" docker logs --tail 200 checkcheck-db-1

if [[ -n "$compose_cmd" && -n "$stack_dir" && -d "$stack_dir" ]]; then
  if [[ "$compose_cmd" == 'docker compose' ]]; then
    capture_command "17_docker_compose_ps.txt" bash -lc "cd \"$stack_dir\" && docker compose ps"
  else
    capture_command "17_docker_compose_ps.txt" bash -lc "cd \"$stack_dir\" && docker-compose ps"
  fi
else
  {
    printf 'COMMAND: docker compose ps\n\n'
    printf 'Could not resolve a valid compose command or stack directory.\n'
    printf 'Detected stack_dir=%s\n' "${stack_dir:-unknown}"
    printf 'Detected compose_command=%s\n' "${compose_cmd:-unavailable}"
    printf '\nEXIT_CODE: 1\n'
  } >"$evidence_dir/17_docker_compose_ps.txt"
  failed_files+=("17_docker_compose_ps.txt:1")
fi

app_state_report="$(extract_state_report checkcheck-app-1 2>/dev/null || true)"
db_state_report="$(extract_state_report checkcheck-db-1 2>/dev/null || true)"

if [[ -z "$app_state_report" ]]; then
  app_state_report='State.Status=not_found
State.Running=n/a
State.Health.Status=n/a
RestartCount=n/a
StartedAt=n/a
FinishedAt=n/a
OOMKilled=n/a
Health.Log:
- n/a'
fi

if [[ -z "$db_state_report" ]]; then
  db_state_report='State.Status=not_found
State.Running=n/a
State.Health.Status=n/a
RestartCount=n/a
StartedAt=n/a
FinishedAt=n/a
OOMKilled=n/a
Health.Log:
- n/a'
fi

printf '%s\n' "$app_state_report" >"$evidence_dir/18_checkcheck_app_1_state_summary.txt"
printf '%s\n' "$db_state_report" >"$evidence_dir/19_checkcheck_db_1_state_summary.txt"

app_state_status="$(printf '%s\n' "$app_state_report" | awk -F= '/^State.Status=/ {print $2; exit}')"
app_health_status="$(printf '%s\n' "$app_state_report" | awk -F= '/^State.Health.Status=/ {print $2; exit}')"
app_restart_count="$(printf '%s\n' "$app_state_report" | awk -F= '/^RestartCount=/ {print $2; exit}')"
app_started_at="$(printf '%s\n' "$app_state_report" | awk -F= '/^StartedAt=/ {print $2; exit}')"
app_finished_at="$(printf '%s\n' "$app_state_report" | awk -F= '/^FinishedAt=/ {print $2; exit}')"
app_oom_killed="$(printf '%s\n' "$app_state_report" | awk -F= '/^OOMKilled=/ {print $2; exit}')"

db_state_status="$(printf '%s\n' "$db_state_report" | awk -F= '/^State.Status=/ {print $2; exit}')"
db_health_status="$(printf '%s\n' "$db_state_report" | awk -F= '/^State.Health.Status=/ {print $2; exit}')"
db_restart_count="$(printf '%s\n' "$db_state_report" | awk -F= '/^RestartCount=/ {print $2; exit}')"

app_classification="$(classify_app_state "$app_state_status" "$app_health_status" "$app_restart_count")"

{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Stack directory detected: %s\n' "${stack_dir:-unknown}"
  printf 'Compose command detected: %s\n' "${compose_cmd:-unavailable}"
  printf 'App container classification: %s\n' "$app_classification"
  printf 'App State.Status: %s\n' "$app_state_status"
  printf 'App State.Health.Status: %s\n' "$app_health_status"
  printf 'App RestartCount: %s\n' "$app_restart_count"
  printf 'App StartedAt: %s\n' "$app_started_at"
  printf 'App FinishedAt: %s\n' "$app_finished_at"
  printf 'App OOMKilled: %s\n' "$app_oom_killed"
  printf 'DB State.Status: %s\n' "$db_state_status"
  printf 'DB State.Health.Status: %s\n' "$db_health_status"
  printf 'DB RestartCount: %s\n' "$db_restart_count"
  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf 'Commands with non-zero exit code: none\n'
  else
    printf 'Commands with non-zero exit code: %s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
  printf '\nApp Health.Log details:\n'
  printf '%s\n' "$app_state_report" | sed -n '/^Health.Log:/,$p'
  printf '\nDB Health.Log details:\n'
  printf '%s\n' "$db_state_report" | sed -n '/^Health.Log:/,$p'
} >"$evidence_dir/99_docker_summary.txt"

manifest_path="$evidence_dir/10_docker_manifest.txt"
{
  printf 'evidence_dir=%s\n' "$evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '11_stack_directory.txt' \
    '12_docker_ps_no_trunc.txt' \
    '13_docker_inspect_checkcheck_app_1.txt' \
    '14_docker_inspect_checkcheck_db_1.txt' \
    '15_docker_logs_checkcheck_app_1_tail_500.txt' \
    '16_docker_logs_checkcheck_db_1_tail_200.txt' \
    '17_docker_compose_ps.txt' \
    '18_checkcheck_app_1_state_summary.txt' \
    '19_checkcheck_db_1_state_summary.txt' \
    '99_docker_summary.txt'
} >"$manifest_path"

log "Docker/container state capture finished"
log "Return the files listed in $manifest_path"