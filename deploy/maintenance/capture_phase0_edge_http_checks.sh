#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  capture_phase0_edge_http_checks.sh <evidence_dir> [options]

Options:
  --local-api-url <url>         Override local upstream health URL.
                               Default: http://127.0.0.1:8000/api/health
  --public-base-url <url>       Override public base URL.
                               Default: https://tscode.com.br
  --public-user-url <url>       Override public checking user URL.
                               Default: <public-base-url>/checking/user
  --public-admin-url <url>      Override public checking admin URL.
                               Default: <public-base-url>/checking/admin
  --local-curl-config <path>    Optional curl config file for the local request.
  --public-curl-config <path>   Optional curl config file for public requests.
  --help                        Show this message.

Examples:
  ./capture_phase0_edge_http_checks.sh /root/checkcheck_incidents/2026-05-04-504-phase0
  ./capture_phase0_edge_http_checks.sh /root/checkcheck_incidents/2026-05-04-504-phase0 \
    --public-curl-config /root/checkcheck_incidents/public-cookies.curlrc
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

evidence_dir="$1"
shift

local_api_url="http://127.0.0.1:8000/api/health"
public_base_url="https://tscode.com.br"
public_user_url=""
public_admin_url=""
local_curl_config=""
public_curl_config=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local-api-url)
      local_api_url="$2"
      shift 2
      ;;
    --public-base-url)
      public_base_url="$2"
      shift 2
      ;;
    --public-user-url)
      public_user_url="$2"
      shift 2
      ;;
    --public-admin-url)
      public_admin_url="$2"
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

mkdir -p "$evidence_dir"

if [[ -z "$public_user_url" ]]; then
  public_user_url="$public_base_url/checking/user"
fi

if [[ -z "$public_admin_url" ]]; then
  public_admin_url="$public_base_url/checking/admin"
fi

declare -a failed_files=()

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
  } >"$evidence_dir/$output_file" 2>&1

  if [[ $status -ne 0 ]]; then
    failed_files+=("$output_file:$status")
  fi
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

extract_header_value() {
  local file_path="$1"
  local header_name="$2"

  awk -v header_name="$header_name" '
    BEGIN {
      IGNORECASE = 1
      prefix = header_name ":"
    }
    index(tolower($0), tolower(prefix)) == 1 {
      value = substr($0, length(prefix) + 1)
      sub(/^ /, "", value)
      sub(/\r$/, "", value)
      print value
      exit
    }
  ' "$file_path" 2>/dev/null || true
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

classify_health_difference() {
  local local_status="$1"
  local public_status="$2"
  local local_ok="$3"
  local public_ok="$4"

  if [[ "$local_status" == "200" && "$public_status" == "200" && "$local_ok" == "true" && "$public_ok" == "true" ]]; then
    printf 'local upstream e edge publico parecem saudaveis e coerentes para /api/health'
    return 0
  fi

  if [[ "$local_status" == "200" && "$local_ok" == "true" && ( "$public_status" == "unavailable" || "$public_status" == "000" ) ]]; then
    printf 'upstream local responde, mas a saude publica no edge nao respondeu utilmente'
    return 0
  fi

  if [[ "$local_status" == "200" && "$local_ok" == "true" && "$public_status" != "200" ]]; then
    printf 'upstream local esta saudavel, mas o edge publico respondeu com status diferente para /api/health'
    return 0
  fi

  if [[ "$local_status" != "200" && "$public_status" == "200" && "$public_ok" == "true" ]]; then
    printf 'edge publico responde melhor que o upstream local observado em 127.0.0.1:8000/api/health'
    return 0
  fi

  if [[ "$local_status" == "$public_status" && "$local_ok" == "$public_ok" ]]; then
    printf 'local upstream e edge publico falham ou desviam de forma semelhante para /api/health'
    return 0
  fi

  printf 'ha diferenca material entre a saude local do upstream e a saude publica do edge; inspecionar headers e corpos capturados'
}

capture_http_response "50_local_api_health.txt" "local_api_health" "$local_api_url" "$local_curl_config"
capture_http_response "51_public_api_health.txt" "public_api_health" "$public_base_url/api/health" "$public_curl_config"
capture_http_response "52_public_checking_user.txt" "public_checking_user" "$public_user_url" "$public_curl_config"
capture_http_response "53_public_checking_admin.txt" "public_checking_admin" "$public_admin_url" "$public_curl_config"

local_status="$(extract_http_status "$evidence_dir/50_local_api_health.txt")"
public_api_status="$(extract_http_status "$evidence_dir/51_public_api_health.txt")"
public_user_status="$(extract_http_status "$evidence_dir/52_public_checking_user.txt")"
public_admin_status="$(extract_http_status "$evidence_dir/53_public_checking_admin.txt")"

local_location="$(extract_header_value "$evidence_dir/50_local_api_health.txt" 'Location')"
public_api_location="$(extract_header_value "$evidence_dir/51_public_api_health.txt" 'Location')"
public_user_location="$(extract_header_value "$evidence_dir/52_public_checking_user.txt" 'Location')"
public_admin_location="$(extract_header_value "$evidence_dir/53_public_checking_admin.txt" 'Location')"

local_ok_json="$(body_contains "$evidence_dir/50_local_api_health.txt" '"status"[[:space:]]*:[[:space:]]*"ok"')"
public_ok_json="$(body_contains "$evidence_dir/51_public_api_health.txt" '"status"[[:space:]]*:[[:space:]]*"ok"')"
public_user_checkform="$(body_contains "$evidence_dir/52_public_checking_user.txt" 'id="checkForm"')"
public_admin_marker="$(body_contains "$evidence_dir/53_public_checking_admin.txt" 'Checking Admin|id="adminApp"|data-tab=')"

health_difference="$(classify_health_difference "$local_status" "$public_api_status" "$local_ok_json" "$public_ok_json")"

summary_file="$evidence_dir/55_edge_http_checks_summary.txt"
{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Local API URL: %s\n' "$local_api_url"
  printf 'Public API URL: %s\n' "$public_base_url/api/health"
  printf 'Public user URL: %s\n' "$public_user_url"
  printf 'Public admin URL: %s\n' "$public_admin_url"
  printf 'Local curl config: %s\n' "${local_curl_config:-none}"
  printf 'Public curl config: %s\n' "${public_curl_config:-none}"
  printf '\nResponse summary:\n'
  printf 'Local API status: %s\n' "$local_status"
  printf 'Local API Location header: %s\n' "${local_location:-none}"
  printf 'Local API contains status ok JSON: %s\n' "$local_ok_json"
  printf 'Public API status: %s\n' "$public_api_status"
  printf 'Public API Location header: %s\n' "${public_api_location:-none}"
  printf 'Public API contains status ok JSON: %s\n' "$public_ok_json"
  printf 'Public checking/user status: %s\n' "$public_user_status"
  printf 'Public checking/user Location header: %s\n' "${public_user_location:-none}"
  printf 'Public checking/user contains checkForm marker: %s\n' "$public_user_checkform"
  printf 'Public checking/admin status: %s\n' "$public_admin_status"
  printf 'Public checking/admin Location header: %s\n' "${public_admin_location:-none}"
  printf 'Public checking/admin contains admin marker: %s\n' "$public_admin_marker"
  printf '\nDiferença entre saúde local do upstream e saúde pública no edge:\n'
  printf '%s\n' "$health_difference"
  printf '\nCommands with non-zero exit code: '
  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf 'none\n'
  else
    printf '%s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
} >"$summary_file"

manifest_path="$evidence_dir/49_edge_http_checks_manifest.txt"
{
  printf 'evidence_dir=%s\n' "$evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '50_local_api_health.txt' \
    '51_public_api_health.txt' \
    '52_public_checking_user.txt' \
    '53_public_checking_admin.txt' \
    '55_edge_http_checks_summary.txt'
} >"$manifest_path"

log "Edge/local HTTP check capture finished"
log "Return the files listed in $manifest_path"