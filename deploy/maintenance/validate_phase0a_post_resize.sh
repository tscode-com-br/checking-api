#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  validate_phase0a_post_resize.sh <post_evidence_dir> --pre-evidence-dir <dir> [options]

Options:
  --pre-evidence-dir <dir>      Directory containing Phase 0 or pre-resize evidence.
  --stack-dir <dir>             Override docker compose working directory.
  --local-api-url <url>         Override local upstream health URL.
                               Default: http://127.0.0.1:8000/api/health
  --public-api-url <url>        Override public API health URL.
                               Default: https://tscode.com.br/api/health
  --local-curl-config <path>    Optional curl config file for local health.
  --public-curl-config <path>   Optional curl config file for public health.
  --help                        Show this message.

Examples:
  ./validate_phase0a_post_resize.sh /root/checkcheck_incidents/2026-05-04-504-phase0a-resize \
    --pre-evidence-dir /root/checkcheck_incidents/2026-05-04-504-phase0

  ./validate_phase0a_post_resize.sh /root/checkcheck_incidents/2026-05-04-504-phase0a-resize \
    --pre-evidence-dir /root/checkcheck_incidents/2026-05-04-504-phase0a-resize \
    --stack-dir /root/checkcheck
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 64
fi

post_evidence_dir="$1"
shift

pre_evidence_dir=""
stack_dir_override=""
local_api_url="http://127.0.0.1:8000/api/health"
public_api_url="https://tscode.com.br/api/health"
local_curl_config=""
public_curl_config=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pre-evidence-dir)
      pre_evidence_dir="$2"
      shift 2
      ;;
    --stack-dir)
      stack_dir_override="$2"
      shift 2
      ;;
    --local-api-url)
      local_api_url="$2"
      shift 2
      ;;
    --public-api-url)
      public_api_url="$2"
      shift 2
      ;;
    --local-curl-config)
      local_curl_config="$2"
      shift 2
      ;;
    --public-curl-config)
      public_curl_config="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

if [[ -z "$pre_evidence_dir" ]]; then
  printf 'Missing required argument: --pre-evidence-dir <dir>\n' >&2
  usage >&2
  exit 64
fi

if [[ ! -d "$pre_evidence_dir" ]]; then
  printf 'Pre-evidence directory not found: %s\n' "$pre_evidence_dir" >&2
  exit 66
fi

mkdir -p "$post_evidence_dir"

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
  } >"$post_evidence_dir/$filename" 2>&1

  if [[ $status -ne 0 ]]; then
    failed_files+=("$filename:$status")
  fi

  return 0
}

capture_http_response() {
  local output_file="$1"
  local label="$2"
  local url="$3"
  local curl_config_path="$4"
  local status=0

  {
    printf 'LABEL: %s\n' "$label"
    printf 'URL: %s\n' "$url"
    if [[ -n "$curl_config_path" ]]; then
      printf 'CURL_CONFIG: %s\n' "$curl_config_path"
    else
      printf 'CURL_CONFIG: none\n'
    fi
    printf 'COMMAND: curl -i -sS --max-time 20 --connect-timeout 5'
    if [[ -n "$curl_config_path" ]]; then
      printf ' --config %q' "$curl_config_path"
    fi
    printf ' %q\n\n' "$url"

    if [[ -n "$curl_config_path" ]]; then
      curl -i -sS --max-time 20 --connect-timeout 5 --config "$curl_config_path" "$url" || status=$?
    else
      curl -i -sS --max-time 20 --connect-timeout 5 "$url" || status=$?
    fi

    printf '\nCURL_EXIT_CODE: %s\n' "$status"
  } >"$post_evidence_dir/$output_file" 2>&1

  if [[ $status -ne 0 ]]; then
    failed_files+=("$output_file:$status")
  fi
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

resolve_pre_file() {
  local base_dir="$1"
  shift
  local relative_path

  for relative_path in "$@"; do
    if [[ -f "$base_dir/$relative_path" ]]; then
      printf '%s' "$base_dir/$relative_path"
      return 0
    fi
  done

  return 1
}

generate_diff_file() {
  local pre_file="$1"
  local post_file="$2"
  local output_file="$3"

  if [[ -z "$pre_file" || ! -f "$pre_file" ]]; then
    printf 'Baseline file unavailable for comparison.\n' >"$output_file"
    return 3
  fi

  if diff -u "$pre_file" "$post_file" >"$output_file" 2>&1; then
    if [[ ! -s "$output_file" ]]; then
      printf 'No differences detected.\n' >"$output_file"
    fi
    return 0
  fi

  local status=$?
  if [[ $status -eq 1 ]]; then
    return 1
  fi

  printf '\ndiff failed with exit code %s\n' "$status" >>"$output_file"
  return 2
}

extract_command_exit_code() {
  local file_path="$1"
  awk -F': ' '/^(EXIT_CODE|CURL_EXIT_CODE):/ {print $2; exit}' "$file_path" 2>/dev/null || true
}

extract_free_total_mb() {
  local file_path="$1"
  awk '/^Mem:/ {print $2; exit}' "$file_path" 2>/dev/null || true
}

extract_nproc_value() {
  local file_path="$1"
  awk '/^[0-9]+$/ {print $1; exit}' "$file_path" 2>/dev/null || true
}

extract_cpu_model() {
  local file_path="$1"
  sed -n 's/^Model name:[[:space:]]*//p' "$file_path" 2>/dev/null | head -n 1
}

extract_df_root_summary() {
  local file_path="$1"
  awk '
    /^Filesystem[[:space:]]+/ {capture=1; next}
    capture && NF >= 6 {print "filesystem=" $1 ", size=" $2 ", used=" $3 ", avail=" $4 ", use%=" $5 ", mounted_on=" $6; exit}
  ' "$file_path" 2>/dev/null || true
}

extract_http_status() {
  local file_path="$1"
  local status_line

  status_line="$(grep -m 1 -E '^HTTP/' "$file_path" 2>/dev/null || true)"
  if [[ -z "$status_line" ]]; then
    printf 'unavailable'
    return 0
  fi

  printf '%s' "$status_line" | awk '{ print $2 }'
}

body_contains() {
  local file_path="$1"
  local pattern="$2"

  if grep -Eq "$pattern" "$file_path" 2>/dev/null; then
    printf 'true'
  else
    printf 'false'
  fi
}

extract_first_meaningful_line() {
  local file_path="$1"
  awk '
    /^COMMAND:/ {next}
    /^LABEL:/ {next}
    /^URL:/ {next}
    /^CURL_CONFIG:/ {next}
    /^EXIT_CODE:/ {next}
    /^CURL_EXIT_CODE:/ {next}
    NF {print; exit}
  ' "$file_path" 2>/dev/null || true
}

compose_has_service() {
  local file_path="$1"
  local pattern="$2"
  if grep -Eiq "$pattern" "$file_path" 2>/dev/null; then
    return 0
  fi
  return 1
}

compose_has_problem_markers() {
  local file_path="$1"
  if grep -Eiq '\b(restarting|exited|dead|error|unhealthy)\b' "$file_path" 2>/dev/null; then
    return 0
  fi
  return 1
}

classify_numeric_change() {
  local pre_value="$1"
  local post_value="$2"

  if [[ -z "$pre_value" || -z "$post_value" ]]; then
    printf 'comparison unavailable'
    return 0
  fi

  if (( post_value > pre_value )); then
    printf 'increased'
    return 0
  fi

  if (( post_value < pre_value )); then
    printf 'decreased'
    return 0
  fi

  printf 'unchanged'
}

classify_health_effect() {
  local pre_status="$1"
  local pre_ok="$2"
  local post_status="$3"
  local post_ok="$4"
  local label="$5"

  if [[ "$post_status" == "200" && "$post_ok" == "true" ]]; then
    if [[ "$pre_status" == "200" && "$pre_ok" == "true" ]]; then
      printf 'sem efeito aparente em %s' "$label"
      return 0
    fi
    printf 'melhora observada em %s apos o resize' "$label"
    return 0
  fi

  if [[ "$pre_status" == "200" && "$pre_ok" == "true" ]]; then
    printf 'possivel regressao em %s apos o resize' "$label"
    return 0
  fi

  if [[ "$post_status" == "unavailable" ]]; then
    printf 'validacao indisponivel para %s' "$label"
    return 0
  fi

  printf 'estado nao saudavel persiste em %s' "$label"
}

classify_docker_effect() {
  local post_compose_exit="$1"
  local app_present="$2"
  local db_present="$3"
  local problem_markers="$4"
  local compose_diff_state="$5"

  if [[ "$post_compose_exit" != "0" ]]; then
    printf 'possivel efeito colateral em Docker: docker compose ps falhou'
    return 0
  fi

  if [[ "$app_present" != "true" || "$db_present" != "true" ]]; then
    printf 'possivel efeito colateral em Docker: servicos esperados nao apareceram no docker compose ps'
    return 0
  fi

  if [[ "$problem_markers" == "true" ]]; then
    printf 'possivel efeito colateral em Docker: compose reportou estado anormal'
    return 0
  fi

  if [[ "$compose_diff_state" == "changed" ]]; then
    printf 'saida do docker compose ps mudou em relacao ao baseline; inspecionar diff antes de concluir ausencia de efeito'
    return 0
  fi

  printf 'sem efeito colateral obvio em Docker a partir do docker compose ps'
}

classify_nginx_effect() {
  local nginx_active="$1"
  local nginx_test_exit="$2"
  local public_health_status="$3"
  local public_health_ok="$4"

  if [[ "$nginx_active" == "active" && "$nginx_test_exit" == "0" && "$public_health_status" == "200" && "$public_health_ok" == "true" ]]; then
    printf 'sem efeito colateral obvio em Nginx'
    return 0
  fi

  if [[ "$nginx_active" != "active" ]]; then
    printf 'possivel efeito colateral em Nginx: unidade nao esta ativa'
    return 0
  fi

  if [[ "$nginx_test_exit" != "0" ]]; then
    printf 'possivel efeito colateral em Nginx: nginx -t falhou'
    return 0
  fi

  if [[ "$public_health_status" != "200" || "$public_health_ok" != "true" ]]; then
    printf 'possivel efeito colateral em Nginx ou edge: health publico nao voltou saudavel'
    return 0
  fi

  printf 'efeito em Nginx nao conclusivo com as evidencias atuais'
}

classify_mount_effect() {
  local pre_root_df="$1"
  local post_root_df="$2"
  local root_df_diff_state="$3"

  if [[ -z "$post_root_df" ]]; then
    printf 'efeito em mounts nao conclusivo: df -h / nao foi capturado corretamente'
    return 0
  fi

  if [[ -n "$pre_root_df" && "$pre_root_df" == "$post_root_df" ]]; then
    printf 'sem efeito colateral obvio no mount raiz'
    return 0
  fi

  if [[ "$root_df_diff_state" == "changed" ]]; then
    printf 'snapshot do filesystem raiz mudou; inspecionar diff para validar se houve efeito em mounts'
    return 0
  fi

  printf 'efeito em mounts nao conclusivo; o script valida apenas o mount raiz e nao todos os volumes'
}

classify_network_effect() {
  local ip_first_line="$1"
  local local_health_status="$2"
  local local_health_ok="$3"
  local public_health_status="$4"
  local public_health_ok="$5"

  if [[ -n "$ip_first_line" && "$local_health_status" == "200" && "$local_health_ok" == "true" && "$public_health_status" == "200" && "$public_health_ok" == "true" ]]; then
    printf 'sem efeito colateral obvio de rede a partir dos checks locais e publicos'
    return 0
  fi

  if [[ "$local_health_status" == "200" && "$local_health_ok" == "true" && ( "$public_health_status" != "200" || "$public_health_ok" != "true" ) ]]; then
    printf 'possivel efeito colateral de rede ou edge: local responde, publico nao'
    return 0
  fi

  if [[ "$local_health_status" != "200" || "$local_health_ok" != "true" ]]; then
    printf 'possivel efeito colateral de rede interna, runtime ou bind local: health local nao voltou saudavel'
    return 0
  fi

  printf 'efeito de rede nao conclusivo com as evidencias atuais'
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

log "Writing post-resize validation evidence to $post_evidence_dir"

capture_command "80_resize_post_date_utc.txt" date -u
capture_command "81_resize_post_free_m.txt" free -m
capture_command "82_resize_post_nproc.txt" nproc
capture_command "83_resize_post_lscpu.txt" lscpu
capture_command "84_resize_post_df_root.txt" df -h /

if [[ -n "$compose_cmd" && -n "$stack_dir" && -d "$stack_dir" ]]; then
  if [[ "$compose_cmd" == 'docker compose' ]]; then
    capture_command "85_resize_post_docker_compose_ps.txt" bash -lc "cd \"$stack_dir\" && docker compose ps"
  else
    capture_command "85_resize_post_docker_compose_ps.txt" bash -lc "cd \"$stack_dir\" && docker-compose ps"
  fi
else
  {
    printf 'COMMAND: docker compose ps\n\n'
    printf 'Could not resolve a valid compose command or stack directory.\n'
    printf 'Detected stack_dir=%s\n' "${stack_dir:-unknown}"
    printf 'Detected compose_command=%s\n' "${compose_cmd:-unavailable}"
    printf '\nEXIT_CODE: 1\n'
  } >"$post_evidence_dir/85_resize_post_docker_compose_ps.txt"
  failed_files+=("85_resize_post_docker_compose_ps.txt:1")
fi

capture_http_response "86_resize_post_local_health.txt" "post_resize_local_health" "$local_api_url" "$local_curl_config"
capture_http_response "87_resize_post_public_health.txt" "post_resize_public_health" "$public_api_url" "$public_curl_config"
capture_command "88_resize_post_systemctl_is_active_nginx.txt" systemctl is-active nginx
capture_command "89_resize_post_nginx_t.txt" nginx -t
capture_command "90_resize_post_ip_brief_address.txt" ip -brief address

pre_free_file="$(resolve_pre_file "$pre_evidence_dir" 61_resize_pre_free_m.txt 06_free_m.txt || true)"
pre_nproc_file="$(resolve_pre_file "$pre_evidence_dir" 62_resize_pre_nproc.txt 08_nproc.txt || true)"
pre_lscpu_file="$(resolve_pre_file "$pre_evidence_dir" 63_resize_pre_lscpu.txt 09_lscpu.txt || true)"
pre_df_root_file="$(resolve_pre_file "$pre_evidence_dir" 64_resize_pre_df_root.txt 07_df_h.txt || true)"
pre_compose_file="$(resolve_pre_file "$pre_evidence_dir" 65_resize_pre_docker_compose_ps.txt 17_docker_compose_ps.txt || true)"
pre_local_health_file="$(resolve_pre_file "$pre_evidence_dir" 66_resize_pre_local_health.txt 50_local_api_health.txt || true)"
pre_public_health_file="$(resolve_pre_file "$pre_evidence_dir" 67_resize_pre_public_health.txt 51_public_api_health.txt || true)"

free_diff_state="baseline_unavailable"
if generate_diff_file "$pre_free_file" "$post_evidence_dir/81_resize_post_free_m.txt" "$post_evidence_dir/91_resize_diff_free_m.txt"; then
  free_diff_state="same"
else
  case $? in
    1) free_diff_state="changed" ;;
    2) free_diff_state="error"; failed_files+=("91_resize_diff_free_m.txt:diff_failed") ;;
    3) free_diff_state="baseline_unavailable" ;;
  esac
fi

nproc_diff_state="baseline_unavailable"
if generate_diff_file "$pre_nproc_file" "$post_evidence_dir/82_resize_post_nproc.txt" "$post_evidence_dir/92_resize_diff_nproc.txt"; then
  nproc_diff_state="same"
else
  case $? in
    1) nproc_diff_state="changed" ;;
    2) nproc_diff_state="error"; failed_files+=("92_resize_diff_nproc.txt:diff_failed") ;;
    3) nproc_diff_state="baseline_unavailable" ;;
  esac
fi

lscpu_diff_state="baseline_unavailable"
if generate_diff_file "$pre_lscpu_file" "$post_evidence_dir/83_resize_post_lscpu.txt" "$post_evidence_dir/93_resize_diff_lscpu.txt"; then
  lscpu_diff_state="same"
else
  case $? in
    1) lscpu_diff_state="changed" ;;
    2) lscpu_diff_state="error"; failed_files+=("93_resize_diff_lscpu.txt:diff_failed") ;;
    3) lscpu_diff_state="baseline_unavailable" ;;
  esac
fi

root_df_diff_state="baseline_unavailable"
if generate_diff_file "$pre_df_root_file" "$post_evidence_dir/84_resize_post_df_root.txt" "$post_evidence_dir/94_resize_diff_df_root.txt"; then
  root_df_diff_state="same"
else
  case $? in
    1) root_df_diff_state="changed" ;;
    2) root_df_diff_state="error"; failed_files+=("94_resize_diff_df_root.txt:diff_failed") ;;
    3) root_df_diff_state="baseline_unavailable" ;;
  esac
fi

compose_diff_state="baseline_unavailable"
if generate_diff_file "$pre_compose_file" "$post_evidence_dir/85_resize_post_docker_compose_ps.txt" "$post_evidence_dir/95_resize_diff_docker_compose_ps.txt"; then
  compose_diff_state="same"
else
  case $? in
    1) compose_diff_state="changed" ;;
    2) compose_diff_state="error"; failed_files+=("95_resize_diff_docker_compose_ps.txt:diff_failed") ;;
    3) compose_diff_state="baseline_unavailable" ;;
  esac
fi

local_health_diff_state="baseline_unavailable"
if generate_diff_file "$pre_local_health_file" "$post_evidence_dir/86_resize_post_local_health.txt" "$post_evidence_dir/96_resize_diff_local_health.txt"; then
  local_health_diff_state="same"
else
  case $? in
    1) local_health_diff_state="changed" ;;
    2) local_health_diff_state="error"; failed_files+=("96_resize_diff_local_health.txt:diff_failed") ;;
    3) local_health_diff_state="baseline_unavailable" ;;
  esac
fi

public_health_diff_state="baseline_unavailable"
if generate_diff_file "$pre_public_health_file" "$post_evidence_dir/87_resize_post_public_health.txt" "$post_evidence_dir/97_resize_diff_public_health.txt"; then
  public_health_diff_state="same"
else
  case $? in
    1) public_health_diff_state="changed" ;;
    2) public_health_diff_state="error"; failed_files+=("97_resize_diff_public_health.txt:diff_failed") ;;
    3) public_health_diff_state="baseline_unavailable" ;;
  esac
fi

pre_memory_total_mb="$(extract_free_total_mb "$pre_free_file")"
post_memory_total_mb="$(extract_free_total_mb "$post_evidence_dir/81_resize_post_free_m.txt")"
pre_nproc_value="$(extract_nproc_value "$pre_nproc_file")"
post_nproc_value="$(extract_nproc_value "$post_evidence_dir/82_resize_post_nproc.txt")"
pre_cpu_model="$(extract_cpu_model "$pre_lscpu_file")"
post_cpu_model="$(extract_cpu_model "$post_evidence_dir/83_resize_post_lscpu.txt")"
pre_root_df_summary="$(extract_df_root_summary "$pre_df_root_file")"
post_root_df_summary="$(extract_df_root_summary "$post_evidence_dir/84_resize_post_df_root.txt")"

pre_local_health_status="$(extract_http_status "$pre_local_health_file")"
post_local_health_status="$(extract_http_status "$post_evidence_dir/86_resize_post_local_health.txt")"
pre_local_health_ok="$(body_contains "$pre_local_health_file" '"status"[[:space:]]*:[[:space:]]*"ok"')"
post_local_health_ok="$(body_contains "$post_evidence_dir/86_resize_post_local_health.txt" '"status"[[:space:]]*:[[:space:]]*"ok"')"

pre_public_health_status="$(extract_http_status "$pre_public_health_file")"
post_public_health_status="$(extract_http_status "$post_evidence_dir/87_resize_post_public_health.txt")"
pre_public_health_ok="$(body_contains "$pre_public_health_file" '"status"[[:space:]]*:[[:space:]]*"ok"')"
post_public_health_ok="$(body_contains "$post_evidence_dir/87_resize_post_public_health.txt" '"status"[[:space:]]*:[[:space:]]*"ok"')"

memory_change="$(classify_numeric_change "${pre_memory_total_mb:-}" "${post_memory_total_mb:-}")"
nproc_change="$(classify_numeric_change "${pre_nproc_value:-}" "${post_nproc_value:-}")"

post_compose_exit="$(extract_command_exit_code "$post_evidence_dir/85_resize_post_docker_compose_ps.txt")"
app_present="false"
db_present="false"
compose_problems="false"
if compose_has_service "$post_evidence_dir/85_resize_post_docker_compose_ps.txt" 'checkcheck-app-1|(^|[[:space:]])app([[:space:]]|$)'; then
  app_present="true"
fi
if compose_has_service "$post_evidence_dir/85_resize_post_docker_compose_ps.txt" 'checkcheck-db-1|(^|[[:space:]])db([[:space:]]|$)'; then
  db_present="true"
fi
if compose_has_problem_markers "$post_evidence_dir/85_resize_post_docker_compose_ps.txt"; then
  compose_problems="true"
fi

nginx_active="$(extract_first_meaningful_line "$post_evidence_dir/88_resize_post_systemctl_is_active_nginx.txt")"
nginx_test_exit="$(extract_command_exit_code "$post_evidence_dir/89_resize_post_nginx_t.txt")"
ip_first_line="$(extract_first_meaningful_line "$post_evidence_dir/90_resize_post_ip_brief_address.txt")"

docker_effect="$(classify_docker_effect "${post_compose_exit:-unavailable}" "$app_present" "$db_present" "$compose_problems" "$compose_diff_state")"
nginx_effect="$(classify_nginx_effect "${nginx_active:-unknown}" "${nginx_test_exit:-unavailable}" "$post_public_health_status" "$post_public_health_ok")"
mount_effect="$(classify_mount_effect "$pre_root_df_summary" "$post_root_df_summary" "$root_df_diff_state")"
network_effect="$(classify_network_effect "$ip_first_line" "$post_local_health_status" "$post_local_health_ok" "$post_public_health_status" "$post_public_health_ok")"
local_health_effect="$(classify_health_effect "$pre_local_health_status" "$pre_local_health_ok" "$post_local_health_status" "$post_local_health_ok" 'health local')"
public_health_effect="$(classify_health_effect "$pre_public_health_status" "$pre_public_health_ok" "$post_public_health_status" "$post_public_health_ok" 'health publico')"

summary_path="$post_evidence_dir/99_resize_post_validation_summary.txt"
{
  printf 'Post evidence directory: %s\n' "$post_evidence_dir"
  printf 'Pre-evidence directory: %s\n' "$pre_evidence_dir"
  printf 'Generated at UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'Detected stack directory: %s\n' "${stack_dir:-unknown}"
  printf 'Detected compose command: %s\n' "${compose_cmd:-unavailable}"
  printf '\nResolved baseline files:\n'
  printf 'free -m baseline: %s\n' "${pre_free_file:-missing}"
  printf 'nproc baseline: %s\n' "${pre_nproc_file:-missing}"
  printf 'lscpu baseline: %s\n' "${pre_lscpu_file:-missing}"
  printf 'df -h / baseline: %s\n' "${pre_df_root_file:-missing}"
  printf 'docker compose ps baseline: %s\n' "${pre_compose_file:-missing}"
  printf 'local health baseline: %s\n' "${pre_local_health_file:-missing}"
  printf 'public health baseline: %s\n' "${pre_public_health_file:-missing}"
  printf '\nCapacity comparison against Phase 0 or pre-resize evidence:\n'
  printf 'Memory total MiB: pre=%s post=%s change=%s\n' "${pre_memory_total_mb:-unavailable}" "${post_memory_total_mb:-unavailable}" "$memory_change"
  printf 'nproc: pre=%s post=%s change=%s\n' "${pre_nproc_value:-unavailable}" "${post_nproc_value:-unavailable}" "$nproc_change"
  printf 'CPU model: pre=%s\n' "${pre_cpu_model:-unavailable}"
  printf 'CPU model: post=%s\n' "${post_cpu_model:-unavailable}"
  printf 'free -m diff state: %s\n' "$free_diff_state"
  printf 'nproc diff state: %s\n' "$nproc_diff_state"
  printf 'lscpu diff state: %s\n' "$lscpu_diff_state"
  printf '\nFilesystem and mount snapshot:\n'
  printf 'Root filesystem pre: %s\n' "${pre_root_df_summary:-unavailable}"
  printf 'Root filesystem post: %s\n' "${post_root_df_summary:-unavailable}"
  printf 'df -h / diff state: %s\n' "$root_df_diff_state"
  printf '\nDocker comparison:\n'
  printf 'docker compose ps exit code: %s\n' "${post_compose_exit:-unavailable}"
  printf 'docker compose ps diff state: %s\n' "$compose_diff_state"
  printf 'App service present in post output: %s\n' "$app_present"
  printf 'DB service present in post output: %s\n' "$db_present"
  printf 'Problem markers in post output: %s\n' "$compose_problems"
  printf '\nHealth comparison:\n'
  printf 'Local health pre status: %s\n' "$pre_local_health_status"
  printf 'Local health pre contains status ok JSON: %s\n' "$pre_local_health_ok"
  printf 'Local health post status: %s\n' "$post_local_health_status"
  printf 'Local health post contains status ok JSON: %s\n' "$post_local_health_ok"
  printf 'Local health diff state: %s\n' "$local_health_diff_state"
  printf 'Public health pre status: %s\n' "$pre_public_health_status"
  printf 'Public health pre contains status ok JSON: %s\n' "$pre_public_health_ok"
  printf 'Public health post status: %s\n' "$post_public_health_status"
  printf 'Public health post contains status ok JSON: %s\n' "$post_public_health_ok"
  printf 'Public health diff state: %s\n' "$public_health_diff_state"
  printf '\nSupplemental checks:\n'
  printf 'systemctl is-active nginx: %s\n' "${nginx_active:-unavailable}"
  printf 'nginx -t exit code: %s\n' "${nginx_test_exit:-unavailable}"
  printf 'First ip -brief address line: %s\n' "${ip_first_line:-unavailable}"
  printf '\nExplicit effect assessment:\n'
  printf 'Docker: %s\n' "$docker_effect"
  printf 'Nginx: %s\n' "$nginx_effect"
  printf 'Mounts: %s\n' "$mount_effect"
  printf 'Network: %s\n' "$network_effect"
  printf 'Healthchecks (local): %s\n' "$local_health_effect"
  printf 'Healthchecks (public): %s\n' "$public_health_effect"
  printf '\nLimitations:\n'
  printf '- Mount validation is limited to the root filesystem snapshot and does not fully validate every Docker volume mount.\n'
  printf '- Network validation is inferred from local/public health plus current interface snapshot, not a full packet or route audit.\n'
  printf '- If the baseline directory points to Phase 0A pre-resize evidence instead of the original Phase 0 directory, the comparison still works, but the resolved baseline files will differ.\n'
  printf '\nCommands with non-zero exit code: '
  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf 'none\n'
  else
    printf '%s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
} >"$summary_path"

manifest_path="$post_evidence_dir/79_resize_post_validation_manifest.txt"
{
  printf 'post_evidence_dir=%s\n' "$post_evidence_dir"
  printf 'pre_evidence_dir=%s\n' "$pre_evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '80_resize_post_date_utc.txt' \
    '81_resize_post_free_m.txt' \
    '82_resize_post_nproc.txt' \
    '83_resize_post_lscpu.txt' \
    '84_resize_post_df_root.txt' \
    '85_resize_post_docker_compose_ps.txt' \
    '86_resize_post_local_health.txt' \
    '87_resize_post_public_health.txt' \
    '88_resize_post_systemctl_is_active_nginx.txt' \
    '89_resize_post_nginx_t.txt' \
    '90_resize_post_ip_brief_address.txt' \
    '91_resize_diff_free_m.txt' \
    '92_resize_diff_nproc.txt' \
    '93_resize_diff_lscpu.txt' \
    '94_resize_diff_df_root.txt' \
    '95_resize_diff_docker_compose_ps.txt' \
    '96_resize_diff_local_health.txt' \
    '97_resize_diff_public_health.txt' \
    '99_resize_post_validation_summary.txt'
} >"$manifest_path"

log "Post-resize validation capture finished"
log "Return the files listed in $manifest_path"