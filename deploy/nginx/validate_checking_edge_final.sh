#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  bash deploy/nginx/validate_checking_edge_final.sh \
    --evidence-dir <path> \
    --server-config <path> \
    [--http-config-target <path>] \
    [--repo-root <path>] \
    [--public-base-url <url>] \
    [--local-api-url <url>] \
    [--local-admin-url <url>] \
    [--local-user-url <url>] \
    [--local-transport-url <url>] \
    [--public-curl-config <path>] \
    [--local-curl-config <path>]

Examples:
  bash deploy/nginx/validate_checking_edge_final.sh \
    --evidence-dir /root/checkcheck_incidents/2026-05-05-504-phase7-edge-final \
    --server-config /etc/nginx/sites-enabled/tscode.com.br.conf \
    --http-config-target /etc/nginx/conf.d/checkcheck-edge-http.conf
EOF
}

capture_command() {
  local output_file="$1"
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
  } >"$output_file" 2>&1

  printf '%s' "$status"
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
    printf 'CURL_CONFIG: %s\n' "${curl_config_path:-none}"
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
  } >"$output_file" 2>&1

  printf '%s' "$status"
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

extract_line_presence() {
  local file_path="$1"
  local pattern="$2"

  if grep -Fq "$pattern" "$file_path" 2>/dev/null; then
    printf 'true'
  else
    printf 'false'
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

evidence_dir=""
server_config=""
http_config_target="/etc/nginx/conf.d/checkcheck-edge-http.conf"
repo_root=""
public_base_url="https://tscode.com.br"
local_api_url="http://127.0.0.1:18080/api/health"
local_admin_url="http://127.0.0.1:18081/"
local_user_url="http://127.0.0.1:18082/"
local_transport_url="http://127.0.0.1:18083/"
local_curl_config=""
public_curl_config=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --evidence-dir)
      evidence_dir="$2"
      shift 2
      ;;
    --server-config)
      server_config="$2"
      shift 2
      ;;
    --http-config-target)
      http_config_target="$2"
      shift 2
      ;;
    --repo-root)
      repo_root="$2"
      shift 2
      ;;
    --public-base-url)
      public_base_url="$2"
      shift 2
      ;;
    --local-api-url)
      local_api_url="$2"
      shift 2
      ;;
    --local-admin-url)
      local_admin_url="$2"
      shift 2
      ;;
    --local-user-url)
      local_user_url="$2"
      shift 2
      ;;
    --local-transport-url)
      local_transport_url="$2"
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
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

[[ -n "$evidence_dir" ]] || { usage >&2; exit 64; }
[[ -n "$server_config" ]] || { usage >&2; exit 64; }

if [[ -z "$repo_root" ]]; then
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

mkdir -p "$evidence_dir"

timestamp="$(date -u '+%Y%m%d%H%M%S')"
server_backup="$evidence_dir/01_server_config.backup.$timestamp.conf"
http_backup="$evidence_dir/02_http_config.backup.$timestamp.conf"
reconciliation_dir="$evidence_dir/nginx_reconciliation"
mkdir -p "$reconciliation_dir"

public_api_url="$public_base_url/api/health"
public_admin_url="$public_base_url/checking/admin"
public_user_url="$public_base_url/checking/user"
public_transport_url="$public_base_url/checking/transport"

apply_status="$(capture_command "$evidence_dir/10_apply_cutover.txt" \
  bash "$repo_root/deploy/nginx/manage_checking_edge_cutover.sh" apply \
  --server-config "$server_config" \
  --routes-file "$repo_root/deploy/nginx/checking-edge-routes.conf" \
  --http-config-target "$http_config_target" \
  --http-rules-file "$repo_root/deploy/nginx/checking-edge-http.conf" \
  --backup-file "$server_backup" \
  --http-backup-file "$http_backup" \
  --reload)"

post_nginx_t_status="unavailable"
if [[ "$apply_status" == "0" ]]; then
  post_nginx_t_status="$(capture_command "$evidence_dir/11_post_apply_nginx_t.txt" nginx -t)"
else
  printf 'COMMAND: nginx -t\n\nSkipped because apply failed.\n\nEXIT_CODE: unavailable\n' >"$evidence_dir/11_post_apply_nginx_t.txt"
fi

local_api_status="$(capture_http_response "$evidence_dir/20_local_api_health.txt" local_api_health "$local_api_url" "$local_curl_config")"
local_admin_status="$(capture_http_response "$evidence_dir/21_local_checking_admin.txt" local_checking_admin "$local_admin_url" "$local_curl_config")"
local_user_status="$(capture_http_response "$evidence_dir/22_local_checking_user.txt" local_checking_user "$local_user_url" "$local_curl_config")"
local_transport_status="$(capture_http_response "$evidence_dir/23_local_checking_transport.txt" local_checking_transport "$local_transport_url" "$local_curl_config")"

public_api_status="$(capture_http_response "$evidence_dir/30_public_api_health.txt" public_api_health "$public_api_url" "$public_curl_config")"
public_admin_status="$(capture_http_response "$evidence_dir/31_public_checking_admin.txt" public_checking_admin "$public_admin_url" "$public_curl_config")"
public_user_status="$(capture_http_response "$evidence_dir/32_public_checking_user.txt" public_checking_user "$public_user_url" "$public_curl_config")"
public_transport_status="$(capture_http_response "$evidence_dir/33_public_checking_transport.txt" public_checking_transport "$public_transport_url" "$public_curl_config")"

verify_local_status="$(capture_command "$evidence_dir/40_verify_local.txt" \
  bash "$repo_root/deploy/nginx/verify_checking_edge_cutover.sh" \
  --mode local \
  --nginx-test \
  --api-local-url "$local_api_url" \
  --admin-local-url "$local_admin_url" \
  --user-local-url "$local_user_url" \
  --transport-local-url "$local_transport_url")"

verify_full_status="$(capture_command "$evidence_dir/41_verify_full.txt" \
  bash "$repo_root/deploy/nginx/verify_checking_edge_cutover.sh" \
  --mode full \
  --api-local-url "$local_api_url" \
  --admin-local-url "$local_admin_url" \
  --user-local-url "$local_user_url" \
  --transport-local-url "$local_transport_url" \
  --public-base-url "$public_base_url")"

reconciliation_status="$(capture_command "$evidence_dir/50_reconcile_active_config.txt" \
  bash "$repo_root/deploy/maintenance/capture_phase0_nginx_config.sh" "$reconciliation_dir" "$repo_root")"

server_block_drift="unavailable"
if [[ -f "$reconciliation_dir/99_nginx_summary.txt" ]]; then
  if grep -Eq '^- (crítica|importante|cosmética):' "$reconciliation_dir/99_nginx_summary.txt"; then
    server_block_drift='detected'
  else
    server_block_drift='not-detected'
  fi
fi

http_auth_zone_present='unavailable'
http_stream_zone_present='unavailable'
if [[ -f "$reconciliation_dir/20_nginx_T.txt" ]]; then
  http_auth_zone_present="$(extract_line_presence "$reconciliation_dir/20_nginx_T.txt" 'limit_req_zone $binary_remote_addr zone=checkcheck_edge_auth:10m rate=15r/s;')"
  http_stream_zone_present="$(extract_line_presence "$reconciliation_dir/20_nginx_T.txt" 'limit_req_zone $binary_remote_addr zone=checkcheck_edge_stream:10m rate=5r/s;')"
fi

final_status='approved'
if [[ "$apply_status" != "0" || "$post_nginx_t_status" != "0" || "$verify_local_status" != "0" || "$verify_full_status" != "0" || "$reconciliation_status" != "0" ]]; then
  final_status='failed-checks'
fi

if [[ "$server_block_drift" != 'not-detected' || "$http_auth_zone_present" != 'true' || "$http_stream_zone_present" != 'true' ]]; then
  final_status='drift-or-config-mismatch'
fi

summary_file="$evidence_dir/99_edge_final_validation_summary.txt"
{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Generated at UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'Repo root: %s\n' "$repo_root"
  printf 'Server config: %s\n' "$server_config"
  printf 'HTTP config target: %s\n' "$http_config_target"
  printf 'Server backup: %s\n' "$server_backup"
  printf 'HTTP backup: %s\n' "$http_backup"
  printf '\nCommand exit codes:\n'
  printf 'apply_cutover=%s\n' "$apply_status"
  printf 'post_apply_nginx_t=%s\n' "$post_nginx_t_status"
  printf 'verify_local=%s\n' "$verify_local_status"
  printf 'verify_full=%s\n' "$verify_full_status"
  printf 'reconciliation_capture=%s\n' "$reconciliation_status"
  printf '\nCurl exit codes:\n'
  printf 'local_api=%s\n' "$local_api_status"
  printf 'local_admin=%s\n' "$local_admin_status"
  printf 'local_user=%s\n' "$local_user_status"
  printf 'local_transport=%s\n' "$local_transport_status"
  printf 'public_api=%s\n' "$public_api_status"
  printf 'public_admin=%s\n' "$public_admin_status"
  printf 'public_user=%s\n' "$public_user_status"
  printf 'public_transport=%s\n' "$public_transport_status"
  printf '\nHTTP status summary:\n'
  printf 'local_api_status=%s\n' "$(extract_http_status "$evidence_dir/20_local_api_health.txt")"
  printf 'local_admin_status=%s\n' "$(extract_http_status "$evidence_dir/21_local_checking_admin.txt")"
  printf 'local_user_status=%s\n' "$(extract_http_status "$evidence_dir/22_local_checking_user.txt")"
  printf 'local_transport_status=%s\n' "$(extract_http_status "$evidence_dir/23_local_checking_transport.txt")"
  printf 'public_api_status=%s\n' "$(extract_http_status "$evidence_dir/30_public_api_health.txt")"
  printf 'public_admin_status=%s\n' "$(extract_http_status "$evidence_dir/31_public_checking_admin.txt")"
  printf 'public_user_status=%s\n' "$(extract_http_status "$evidence_dir/32_public_checking_user.txt")"
  printf 'public_transport_status=%s\n' "$(extract_http_status "$evidence_dir/33_public_checking_transport.txt")"
  printf '\nActive config versus repo:\n'
  printf 'server_block_drift=%s\n' "$server_block_drift"
  printf 'http_auth_zone_present=%s\n' "$http_auth_zone_present"
  printf 'http_stream_zone_present=%s\n' "$http_stream_zone_present"
  printf 'routing_answer=%s\n' "$(grep -m 1 '^Routing answer:' "$reconciliation_dir/99_nginx_summary.txt" 2>/dev/null | sed 's/^Routing answer: //')"
  printf '\nRemaining manual dependencies treated as debt:\n'
  printf -- '- acesso SSH/operacional ao droplet continua fora deste script e deve vir de credencial externa ao repo\n'
  printf -- '- o caminho real do server config HTTPS do dominio ainda precisa ser informado por --server-config\n'
  printf -- '- o caminho de include http do host ainda precisa ser informado ou aceito como /etc/nginx/conf.d/checkcheck-edge-http.conf\n'
  printf -- '- qualquer cookie ou autenticacao adicional necessaria para curls publicos segue fora do repo e deve ser injetada por --local-curl-config/--public-curl-config quando necessario\n'
  printf '\nFinal status: %s\n' "$final_status"
  printf '\nKey evidence files:\n'
  printf -- '- 10_apply_cutover.txt\n'
  printf -- '- 11_post_apply_nginx_t.txt\n'
  printf -- '- 20_local_api_health.txt\n'
  printf -- '- 21_local_checking_admin.txt\n'
  printf -- '- 22_local_checking_user.txt\n'
  printf -- '- 23_local_checking_transport.txt\n'
  printf -- '- 30_public_api_health.txt\n'
  printf -- '- 31_public_checking_admin.txt\n'
  printf -- '- 32_public_checking_user.txt\n'
  printf -- '- 33_public_checking_transport.txt\n'
  printf -- '- 40_verify_local.txt\n'
  printf -- '- 41_verify_full.txt\n'
  printf -- '- nginx_reconciliation/99_nginx_summary.txt\n'
} >"$summary_file"

if [[ "$final_status" != 'approved' ]]; then
  log "Edge final validation finished with status: $final_status"
  log "Inspect $summary_file"
  exit 1
fi

log "Edge final validation completed successfully"
log "Summary: $summary_file"