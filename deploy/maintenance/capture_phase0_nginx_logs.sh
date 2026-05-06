#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  capture_phase0_nginx_logs.sh <evidence_dir> [since] [until]

Examples:
  ./capture_phase0_nginx_logs.sh /root/checkcheck_incidents/2026-05-04-504-phase0
  ./capture_phase0_nginx_logs.sh /root/checkcheck_incidents/2026-05-04-504-phase0 '2026-05-04 00:00:00' '2026-05-04 23:59:59'
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage >&2
  exit 64
fi

evidence_dir="$1"
since_arg="${2:-}"
until_arg="${3:-}"
mkdir -p "$evidence_dir"

declare -a failed_files=()
declare -a access_log_paths=()
declare -a error_log_paths=()
declare -a access_logs=()
declare -a error_logs=()

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

note_failure_file() {
  local filename="$1"
  local description="$2"
  local exit_code="$3"

  {
    printf 'COMMAND: %s\n\n' "$description"
    printf '%s\n' "$description"
    printf '\nEXIT_CODE: %s\n' "$exit_code"
  } >"$evidence_dir/$filename"

  failed_files+=("$filename:$exit_code")
}

add_unique_path() {
  local value="$1"
  shift
  local array_name="$1"
  local existing

  eval "for existing in \"\${${array_name}[@]:-}\"; do
    if [[ \"\$existing\" == \"\$value\" ]]; then
      return 0
    fi
  done"

  eval "${array_name}+=(\"\$value\")"
}

sanitize_path() {
  printf '%s' "$1" | sed 's#^/##; s#[/ ]#_#g; s#[^A-Za-z0-9._-]#_#g'
}

discover_log_paths_from_nginx_t() {
  local config_dump="$1"

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    add_unique_path "$path" access_log_paths
  done < <(
    awk '
      $1 == "access_log" {
        path = $2
        sub(/;$/, "", path)
        if (path ~ /^\//) {
          print path
        }
      }
    ' "$config_dump"
  )

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    add_unique_path "$path" error_log_paths
  done < <(
    awk '
      $1 == "error_log" {
        path = $2
        sub(/;$/, "", path)
        if (path ~ /^\//) {
          print path
        }
      }
    ' "$config_dump"
  )
}

fallback_log_paths() {
  if [[ ${#access_log_paths[@]} -eq 0 ]]; then
    add_unique_path "/var/log/nginx/access.log" access_log_paths
  fi

  if [[ ${#error_log_paths[@]} -eq 0 ]]; then
    add_unique_path "/var/log/nginx/error.log" error_log_paths
  fi
}

collect_log_files() {
  local base_path="$1"
  local array_name="$2"
  local candidate

  if [[ -f "$base_path" ]]; then
    add_unique_path "$base_path" "$array_name"
  fi

  for candidate in "$base_path"*; do
    [[ -e "$candidate" ]] || continue
    [[ -f "$candidate" ]] || continue
    add_unique_path "$candidate" "$array_name"
  done
}

capture_match_lines() {
  local output_file="$1"
  local description="$2"
  local mode="$3"
  local pattern="$4"
  shift 4
  local log_files=("$@")
  local matches
  local file

  {
    printf 'DESCRIPTION: %s\n' "$description"
    printf 'MATCH_MODE: %s\n' "$mode"
    printf 'PATTERN: %s\n\n' "$pattern"

    for file in "${log_files[@]}"; do
      printf 'SOURCE_FILE\t%s\n' "$file"
      if [[ "$mode" == 'fixed' ]]; then
        if [[ "$file" == *.gz ]]; then
          if matches="$(gzip -cd -- "$file" 2>/dev/null | grep -nF -- "$pattern" 2>/dev/null || true)"; then
            :
          fi
        else
          if matches="$(grep -nF -- "$pattern" "$file" 2>/dev/null || true)"; then
            :
          fi
        fi
      else
        if [[ "$file" == *.gz ]]; then
          if matches="$(gzip -cd -- "$file" 2>/dev/null | grep -nE -- "$pattern" 2>/dev/null || true)"; then
            :
          fi
        else
          if matches="$(grep -nE -- "$pattern" "$file" 2>/dev/null || true)"; then
            :
          fi
        fi
      fi

      if [[ -n "$matches" ]]; then
        while IFS= read -r line; do
          [[ -n "$line" ]] || continue
          printf 'MATCH\t%s\t%s\n' "$file" "$line"
        done <<<"$matches"
      else
        printf 'MATCH_COUNT\t0\n'
      fi

      printf '\n'
    done
  } >"$evidence_dir/$output_file"
}

capture_tail_file() {
  local output_file="$1"
  local source_file="$2"
  local line_count="$3"

  if [[ -z "$source_file" || ! -f "$source_file" ]]; then
    note_failure_file "$output_file" "No readable current log file available for tail capture." 1
    return 0
  fi

  capture_command "$output_file" tail -n "$line_count" "$source_file"
}

copy_log_files() {
  local manifest_file="$evidence_dir/41_raw_nginx_logs_manifest.txt"
  local raw_dir="$evidence_dir/42_raw_nginx_logs"
  local file
  local safe_name
  local target_path

  mkdir -p "$raw_dir"

  {
    printf 'source\ttarget\tsize_bytes\n'
    for file in "${access_logs[@]}" "${error_logs[@]}"; do
      [[ -n "$file" ]] || continue
      safe_name="$(sanitize_path "$file")"
      target_path="$raw_dir/$safe_name"
      if cp -a -- "$file" "$target_path" 2>/dev/null; then
        printf '%s\t%s\t%s\n' "$file" "$target_path" "$(wc -c <"$target_path" 2>/dev/null || printf 'unknown')"
      else
        printf '%s\tcopy_failed\tunknown\n' "$file"
        failed_files+=("41_raw_nginx_logs_manifest.txt:copy_failed:$file")
      fi
    done
  } >"$manifest_file"
}

normalize_access_matches() {
  local source_file="$1"
  local output_file="$2"

  awk '
    function normalize_route(path) {
      sub(/\?.*$/, "", path)
      if (path ~ /^\/checking\/user(\/|$)/) {
        return "/checking/user"
      }
      if (path ~ /^\/checking\/admin(\/|$)/) {
        return "/checking/admin"
      }
      if (path ~ /^\/api\/web\/check\/state(\/|$)/) {
        return "/api/web/check/state"
      }
      if (path ~ /^\/api\/mobile\/state(\/|$)/) {
        return "/api/mobile/state"
      }
      if (path ~ /^\/api\/admin\/stream(\/|$)/) {
        return "/api/admin/stream"
      }
      if (path ~ /^\/api\/admin\/checkin(\/|$)/) {
        return "/api/admin/checkin"
      }
      if (path ~ /^\/api\/admin\/checkout(\/|$)/) {
        return "/api/admin/checkout"
      }
      if (path ~ /^\/api\/admin\/projects(\/|$)/) {
        return "/api/admin/projects"
      }
      return path
    }

    BEGIN {
      OFS = "\t"
    }

    $1 == "MATCH" {
      source_file = $2
      raw = $0
      sub(/^MATCH\t[^\t]+\t[0-9]+:/, "", raw)

      ip = "unknown"
      status = "unknown"
      route = "unknown"
      route_key = "unknown"
      host = "unknown"
      ua = "unknown"

      split(raw, space_parts, " ")
      if (space_parts[1] != "") {
        ip = space_parts[1]
      }

      split(raw, quote_parts, /"/)
      request = quote_parts[2]
      after_request = quote_parts[3]
      if (quote_parts[6] != "") {
        ua = quote_parts[6]
      }

      split(request, request_parts, " ")
      if (request_parts[2] != "") {
        route = request_parts[2]
        sub(/\?.*$/, "", route)
        route_key = normalize_route(route)
      }

      split(after_request, after_parts, " ")
      for (i in after_parts) {
        if (after_parts[i] ~ /^[0-9][0-9][0-9]$/) {
          status = after_parts[i]
          break
        }
      }

      if (match(raw, /host=([^ ]+)/)) {
        host = substr(raw, RSTART + 5, RLENGTH - 5)
        sub(/[";,]+$/, "", host)
      } else if (match(raw, /vhost=([^ ]+)/)) {
        host = substr(raw, RSTART + 6, RLENGTH - 6)
        sub(/[";,]+$/, "", host)
      } else if (quote_parts[8] != "") {
        host = quote_parts[8]
      }

      if (route_key == "") {
        route_key = "unknown"
      }

      print route_key, route, status, host, ip, ua, source_file
    }
  ' "$evidence_dir/$source_file" >"$evidence_dir/$output_file"
}

normalize_error_matches() {
  local source_file="$1"
  local output_file="$2"

  awk '
    function normalize_route(path) {
      sub(/\?.*$/, "", path)
      if (path ~ /^\/checking\/user(\/|$)/) {
        return "/checking/user"
      }
      if (path ~ /^\/checking\/admin(\/|$)/) {
        return "/checking/admin"
      }
      if (path ~ /^\/api\/web\/check\/state(\/|$)/) {
        return "/api/web/check/state"
      }
      if (path ~ /^\/api\/mobile\/state(\/|$)/) {
        return "/api/mobile/state"
      }
      if (path ~ /^\/api\/admin\/stream(\/|$)/) {
        return "/api/admin/stream"
      }
      if (path ~ /^\/api\/admin\/checkin(\/|$)/) {
        return "/api/admin/checkin"
      }
      if (path ~ /^\/api\/admin\/checkout(\/|$)/) {
        return "/api/admin/checkout"
      }
      if (path ~ /^\/api\/admin\/projects(\/|$)/) {
        return "/api/admin/projects"
      }
      return path
    }

    BEGIN {
      OFS = "\t"
    }

    $1 == "MATCH" {
      source_file = $2
      raw = $0
      sub(/^MATCH\t[^\t]+\t[0-9]+:/, "", raw)

      route = "unknown"
      route_key = "unknown"
      host = "unknown"
      ip = "unknown"

      if (match(raw, /request: "[A-Z]+ [^ ?"]+/)) {
        route = substr(raw, RSTART, RLENGTH)
        sub(/^request: "[A-Z]+ /, "", route)
        route_key = normalize_route(route)
      }

      if (match(raw, /host: "[^"]+"/)) {
        host = substr(raw, RSTART + 7, RLENGTH - 8)
      }

      if (match(raw, /client: [^, ]+/)) {
        ip = substr(raw, RSTART + 8, RLENGTH - 8)
      }

      print route_key, route, "upstream timed out", host, ip, source_file
    }
  ' "$evidence_dir/$source_file" >"$evidence_dir/$output_file"
}

count_rows() {
  local file="$1"
  if [[ -f "$file" ]]; then
    awk 'NF > 0 { count++ } END { print count + 0 }' "$file"
  else
    printf '0'
  fi
}

count_rows_for_route() {
  local file="$1"
  local route_key="$2"
  if [[ -f "$file" ]]; then
    awk -F'\t' -v route_key="$route_key" '$1 == route_key { count++ } END { print count + 0 }' "$file"
  else
    printf '0'
  fi
}

top_values_for_route() {
  local file="$1"
  local field_index="$2"
  local route_key="$3"
  local limit="${4:-3}"

  if [[ ! -f "$file" ]]; then
    printf 'none'
    return 0
  fi

  local rendered
  rendered="$({
    awk -F'\t' -v field_index="$field_index" -v route_key="$route_key" '$1 == route_key && $field_index != "" && $field_index != "unknown" { print $field_index }' "$file" |
      sort |
      uniq -c |
      sort -rn |
      head -n "$limit" |
      awk -v limit="$limit" '{ count = $1; $1 = ""; sub(/^ /, ""); printf "%s (%s)%s", $0, count, (NR < limit ? ", " : "") }'
  } 2>/dev/null || true)"

  if [[ -z "$rendered" ]]; then
    printf 'none'
  else
    printf '%s' "$rendered"
  fi
}

top_error_values_for_route() {
  local file="$1"
  local field_index="$2"
  local route_key="$3"
  local limit="${4:-3}"

  if [[ ! -f "$file" ]]; then
    printf 'none'
    return 0
  fi

  local rendered
  rendered="$({
    awk -F'\t' -v field_index="$field_index" -v route_key="$route_key" '$1 == route_key && $field_index != "" && $field_index != "unknown" { print $field_index }' "$file" |
      sort |
      uniq -c |
      sort -rn |
      head -n "$limit" |
      awk -v limit="$limit" '{ count = $1; $1 = ""; sub(/^ /, ""); printf "%s (%s)%s", $0, count, (NR < limit ? ", " : "") }'
  } 2>/dev/null || true)"

  if [[ -z "$rendered" ]]; then
    printf 'none'
  else
    printf '%s' "$rendered"
  fi
}

capture_command "30_nginx_T_for_log_discovery.txt" nginx -T
discover_log_paths_from_nginx_t "$evidence_dir/30_nginx_T_for_log_discovery.txt"
fallback_log_paths

for path in "${access_log_paths[@]}"; do
  collect_log_files "$path" access_logs
done

for path in "${error_log_paths[@]}"; do
  collect_log_files "$path" error_logs
done

{
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'since_arg=%s\n' "${since_arg:-unspecified}"
  printf 'until_arg=%s\n' "${until_arg:-unspecified}"
  printf 'configured_access_logs:\n'
  for path in "${access_log_paths[@]}"; do
    printf '%s\n' "$path"
  done
  printf 'configured_error_logs:\n'
  for path in "${error_log_paths[@]}"; do
    printf '%s\n' "$path"
  done
  printf 'discovered_access_log_files:\n'
  for path in "${access_logs[@]}"; do
    printf '%s\n' "$path"
  done
  printf 'discovered_error_log_files:\n'
  for path in "${error_logs[@]}"; do
    printf '%s\n' "$path"
  done
} >"$evidence_dir/31_nginx_log_file_inventory.txt"

primary_access_log=""
primary_error_log=""
for path in "${access_log_paths[@]}"; do
  if [[ -f "$path" ]]; then
    primary_access_log="$path"
    break
  fi
done
if [[ -z "$primary_access_log" ]]; then
  for path in "${access_logs[@]}"; do
    if [[ -f "$path" && "$path" != *.gz ]]; then
      primary_access_log="$path"
      break
    fi
  done
fi

for path in "${error_log_paths[@]}"; do
  if [[ -f "$path" ]]; then
    primary_error_log="$path"
    break
  fi
done
if [[ -z "$primary_error_log" ]]; then
  for path in "${error_logs[@]}"; do
    if [[ -f "$path" && "$path" != *.gz ]]; then
      primary_error_log="$path"
      break
    fi
  done
fi

capture_tail_file "32_nginx_access_tail_500.txt" "$primary_access_log" 500
capture_tail_file "33_nginx_error_tail_500.txt" "$primary_error_log" 500

if [[ ${#access_logs[@]} -gt 0 ]]; then
  capture_match_lines "34_nginx_access_504_matches.txt" "Access log lines containing status 504 across current and rotated logs." fixed ' 504 ' "${access_logs[@]}"
  capture_match_lines "37_nginx_priority_route_matches.txt" "Access log lines for the critical routes across current and rotated logs." extended '/checking/user|/checking/admin|/api/web/check/state|/api/mobile/state|/api/admin/stream|/api/admin/checkin|/api/admin/checkout|/api/admin/projects' "${access_logs[@]}"
else
  note_failure_file "34_nginx_access_504_matches.txt" "No access logs were discovered for grep collection." 1
  note_failure_file "37_nginx_priority_route_matches.txt" "No access logs were discovered for critical route collection." 1
fi

if [[ ${#error_logs[@]} -gt 0 ]]; then
  capture_match_lines "35_nginx_error_upstream_timed_out_matches.txt" "Error log lines containing upstream timed out across current and rotated logs." fixed 'upstream timed out' "${error_logs[@]}"
else
  note_failure_file "35_nginx_error_upstream_timed_out_matches.txt" "No error logs were discovered for grep collection." 1
fi

if command -v journalctl >/dev/null 2>&1; then
  if [[ -n "$since_arg" || -n "$until_arg" ]]; then
    journal_cmd=(journalctl -u nginx -u nginx.service --no-pager -o short-iso)
    if [[ -n "$since_arg" ]]; then
      journal_cmd+=(--since "$since_arg")
    fi
    if [[ -n "$until_arg" ]]; then
      journal_cmd+=(--until "$until_arg")
    fi
    capture_command "36_nginx_journalctl_nginx.txt" "${journal_cmd[@]}"
  else
    capture_command "36_nginx_journalctl_nginx.txt" journalctl -u nginx -u nginx.service --no-pager -o short-iso -n 500
  fi
else
  note_failure_file "36_nginx_journalctl_nginx.txt" "journalctl is not available on this host context." 1
fi

copy_log_files

normalize_access_matches "34_nginx_access_504_matches.txt" "38_access_504_normalized.tsv"
normalize_access_matches "37_nginx_priority_route_matches.txt" "39_priority_route_normalized.tsv"
normalize_error_matches "35_nginx_error_upstream_timed_out_matches.txt" "40_error_upstream_timed_out_normalized.tsv"

summary_file="$evidence_dir/99_nginx_edge_logs_summary.txt"
critical_routes=(
  '/checking/user'
  '/checking/admin'
  '/api/web/check/state'
  '/api/mobile/state'
  '/api/admin/stream'
  '/api/admin/checkin'
  '/api/admin/checkout'
  '/api/admin/projects'
)

{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Since filter: %s\n' "${since_arg:-unspecified}"
  printf 'Until filter: %s\n' "${until_arg:-unspecified}"
  printf 'Discovered access log files: %s\n' "${#access_logs[@]}"
  printf 'Discovered error log files: %s\n' "${#error_logs[@]}"
  printf 'Access 504 match rows: %s\n' "$(count_rows "$evidence_dir/38_access_504_normalized.tsv")"
  printf 'Critical route access match rows: %s\n' "$(count_rows "$evidence_dir/39_priority_route_normalized.tsv")"
  printf 'Error upstream timed out match rows: %s\n' "$(count_rows "$evidence_dir/40_error_upstream_timed_out_normalized.tsv")"
  printf '\nCritical route summary:\n'

  for route_key in "${critical_routes[@]}"; do
    printf '\n- Route: %s\n' "$route_key"
    printf '  Access 504 hits: %s\n' "$(count_rows_for_route "$evidence_dir/38_access_504_normalized.tsv" "$route_key")"
    printf '  Access critical-route hits: %s\n' "$(count_rows_for_route "$evidence_dir/39_priority_route_normalized.tsv" "$route_key")"
    printf '  Error upstream timed out hits: %s\n' "$(count_rows_for_route "$evidence_dir/40_error_upstream_timed_out_normalized.tsv" "$route_key")"
    printf '  Top statuses: %s\n' "$(top_values_for_route "$evidence_dir/39_priority_route_normalized.tsv" 3 "$route_key")"
    printf '  Top hosts: %s\n' "$(top_values_for_route "$evidence_dir/39_priority_route_normalized.tsv" 4 "$route_key")"
    printf '  Top IPs: %s\n' "$(top_values_for_route "$evidence_dir/39_priority_route_normalized.tsv" 5 "$route_key")"
    printf '  Top user-agents: %s\n' "$(top_values_for_route "$evidence_dir/39_priority_route_normalized.tsv" 6 "$route_key")"
    printf '  Error hosts: %s\n' "$(top_error_values_for_route "$evidence_dir/40_error_upstream_timed_out_normalized.tsv" 4 "$route_key")"
    printf '  Error IPs: %s\n' "$(top_error_values_for_route "$evidence_dir/40_error_upstream_timed_out_normalized.tsv" 5 "$route_key")"
  done

  printf '\nOverall access 504 grouped counts (route | status | host | ip | user-agent):\n'
  if [[ -s "$evidence_dir/38_access_504_normalized.tsv" ]]; then
    awk -F'\t' '{ printf "%s | %s | %s | %s | %s\n", $1, $3, $4, $5, $6 }' "$evidence_dir/38_access_504_normalized.tsv" |
      sort |
      uniq -c |
      sort -rn |
      head -n 25
  else
    printf 'none\n'
  fi

  printf '\nOverall error upstream timed out grouped counts (route | host | ip):\n'
  if [[ -s "$evidence_dir/40_error_upstream_timed_out_normalized.tsv" ]]; then
    awk -F'\t' '{ printf "%s | %s | %s\n", $1, $4, $5 }' "$evidence_dir/40_error_upstream_timed_out_normalized.tsv" |
      sort |
      uniq -c |
      sort -rn |
      head -n 25
  else
    printf 'none\n'
  fi

  printf '\nRelevant evidence files:\n'
  printf '%s\n' \
    '30_nginx_T_for_log_discovery.txt' \
    '31_nginx_log_file_inventory.txt' \
    '32_nginx_access_tail_500.txt' \
    '33_nginx_error_tail_500.txt' \
    '34_nginx_access_504_matches.txt' \
    '35_nginx_error_upstream_timed_out_matches.txt' \
    '36_nginx_journalctl_nginx.txt' \
    '37_nginx_priority_route_matches.txt' \
    '41_raw_nginx_logs_manifest.txt' \
    '42_raw_nginx_logs/'

  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf '\nCommands with non-zero exit code: none\n'
  else
    printf '\nCommands with non-zero exit code: %s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
} >"$summary_file"

manifest_path="$evidence_dir/29_nginx_edge_logs_manifest.txt"
{
  printf 'evidence_dir=%s\n' "$evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '30_nginx_T_for_log_discovery.txt' \
    '31_nginx_log_file_inventory.txt' \
    '32_nginx_access_tail_500.txt' \
    '33_nginx_error_tail_500.txt' \
    '34_nginx_access_504_matches.txt' \
    '35_nginx_error_upstream_timed_out_matches.txt' \
    '36_nginx_journalctl_nginx.txt' \
    '37_nginx_priority_route_matches.txt' \
    '38_access_504_normalized.tsv' \
    '39_priority_route_normalized.tsv' \
    '40_error_upstream_timed_out_normalized.tsv' \
    '41_raw_nginx_logs_manifest.txt' \
    '42_raw_nginx_logs/' \
    '99_nginx_edge_logs_summary.txt'
} >"$manifest_path"

log "Nginx edge log capture finished"
log "Return the files listed in $manifest_path"