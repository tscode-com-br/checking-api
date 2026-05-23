#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  capture_phase0_nginx_config.sh <evidence_dir> [repo_root_or_repo_config_path]

Examples:
  ./capture_phase0_nginx_config.sh /root/checkcheck_incidents/2026-05-04-504-phase0
  ./capture_phase0_nginx_config.sh /root/checkcheck_incidents/2026-05-04-504-phase0 /root/checkcheck
  ./capture_phase0_nginx_config.sh /root/checkcheck_incidents/2026-05-04-504-phase0 /root/checkcheck/deploy/nginx/checking-edge-routes.conf
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
repo_hint="${2:-}"
mkdir -p "$evidence_dir"

declare -a failed_files=()
declare -a drifts=()

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

resolve_repo_config_path() {
  local hint="$1"
  local script_source="${BASH_SOURCE[0]:-}"
  local script_dir=""
  local stack_dir="${2:-}"
  local candidate=""

  if [[ -n "$hint" ]]; then
    if [[ -f "$hint" ]]; then
      printf '%s' "$hint"
      return 0
    fi

    candidate="$hint/deploy/nginx/checking-edge-routes.conf"
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  fi

  if [[ -n "$script_source" && -f "$script_source" ]]; then
    script_dir="$(cd "$(dirname "$script_source")" && pwd)"
    candidate="$script_dir/../nginx/checking-edge-routes.conf"
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  fi

  if [[ -n "$stack_dir" ]]; then
    candidate="$stack_dir/deploy/nginx/checking-edge-routes.conf"
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  fi

  candidate="$(pwd)/deploy/nginx/checking-edge-routes.conf"
  if [[ -f "$candidate" ]]; then
    printf '%s' "$candidate"
    return 0
  fi

  return 1
}

extract_tscode_server_blocks() {
  local source_file="$1"
  local output_file="$2"

  awk '
    function flush() {
      if (buffer != "" && relevant) {
        print buffer >> out
        print "" >> out
        found = 1
      }
      buffer = ""
      relevant = 0
      in_server = 0
      depth = 0
    }

    BEGIN {
      out = ARGV[2]
      ARGV[2] = ""
      found = 0
      in_server = 0
      depth = 0
      buffer = ""
      relevant = 0
    }

    {
      line = $0
      if (!in_server && line ~ /^[[:space:]]*server[[:space:]]*\{[[:space:]]*$/) {
        in_server = 1
        depth = 0
        buffer = ""
        relevant = 0
      }

      if (in_server) {
        buffer = buffer line ORS
        if (line ~ /server_name[[:space:]].*tscode\.com\.br/) {
          relevant = 1
        }
        opens = gsub(/\{/, "{", line)
        closes = gsub(/\}/, "}", line)
        depth += opens - closes
        if (depth == 0) {
          flush()
        }
      }
    }

    END {
      if (in_server) {
        flush()
      }
      if (!found) {
        print "# No server block for tscode.com.br was found." >> out
      }
    }
  ' "$source_file" "$output_file"
}

extract_relevant_location_blocks() {
  local source_file="$1"
  local output_file="$2"

  awk '
    function is_relevant_header(header_line) {
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/api\/?[[:space:]]*\{/) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/api\/health[[:space:]]*\{/) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/api\/health\/ready[[:space:]]*\{/) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/checking\/admin\/?[[:space:]]*\{/) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/checking\/user\/?[[:space:]]*\{/) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location([[:space:]]+=)?[[:space:]]*\/checking\/transport\/?[[:space:]]*\{/) {
        return 1
      }
      if (index(header_line, "location ~ ^/api/(admin/stream|transport/stream|web/transport/stream)$") > 0) {
        return 1
      }
      if (index(header_line, "location ~ ^/api/(admin|transport|web)/auth/") > 0) {
        return 1
      }
      if (header_line ~ /^[[:space:]]*location[[:space:]]+\/checking\/?[[:space:]]*\{/) {
        return 1
      }
      return 0
    }

    function flush() {
      if (buffer != "" && relevant) {
        print buffer >> out
        print "" >> out
        found = 1
      }
      buffer = ""
      relevant = 0
      in_location = 0
      depth = 0
    }

    BEGIN {
      out = ARGV[2]
      ARGV[2] = ""
      found = 0
      in_location = 0
      depth = 0
      buffer = ""
      relevant = 0
    }

    {
      line = $0
      if (!in_location && line ~ /^[[:space:]]*location[[:space:]]/) {
        in_location = 1
        depth = 0
        buffer = ""
        relevant = is_relevant_header(line)
      }

      if (in_location) {
        buffer = buffer line ORS
        opens = gsub(/\{/, "{", line)
        closes = gsub(/\}/, "}", line)
        depth += opens - closes
        if (depth == 0) {
          flush()
        }
      }
    }

    END {
      if (in_location) {
        flush()
      }
      if (!found) {
        print "# No relevant location block was found." >> out
      }
    }
  ' "$source_file" "$output_file"
}

write_location_index() {
  local source_file="$1"
  local output_file="$2"

  : > "$output_file"

  awk '
    function flush() {
      if (header != "") {
        print header "|||" target >> out
      }
      header = ""
      target = ""
      in_location = 0
      depth = 0
    }

    BEGIN {
      out = ARGV[2]
      ARGV[2] = ""
      in_location = 0
      depth = 0
      header = ""
      target = ""
    }

    {
      line = $0
      if (!in_location && line ~ /^[[:space:]]*location[[:space:]]/) {
        in_location = 1
        depth = 0
        header = line
        target = ""
      }

      if (in_location) {
        if (match(line, /proxy_pass[[:space:]]+http:\/\/127\.0\.0\.1:[0-9]+(\/api\/|\/)?/)) {
          target = substr(line, RSTART, RLENGTH)
          gsub(/^proxy_pass[[:space:]]+http:\/\//, "", target)
          gsub(/;$/, "", target)
        }
        opens = gsub(/\{/, "{", line)
        closes = gsub(/\}/, "}", line)
        depth += opens - closes
        if (depth == 0) {
          flush()
        }
      }
    }

    END {
      if (in_location) {
        flush()
      }
    }
  ' "$source_file" "$output_file"
}

targets_for_pattern() {
  local source_file="$1"
  local pattern="$2"

  awk -F'[|][|][|]' -v pattern="$pattern" '
    $1 ~ pattern && $2 != "" { print $2 }
  ' "$source_file" | sort -u | paste -sd',' -
}

has_header_pattern() {
  local source_file="$1"
  local pattern="$2"

  awk -F'[|][|][|]' -v pattern="$pattern" '
    $1 ~ pattern { found = 1 }
    END { exit(found ? 0 : 1) }
  ' "$source_file"
}

has_line_pattern() {
  local source_file="$1"
  local pattern="$2"

  grep -Eq "$pattern" "$source_file"
}

stack_dir="$(detect_stack_dir 2>/dev/null || true)"
repo_config_path="$(resolve_repo_config_path "$repo_hint" "$stack_dir" 2>/dev/null || true)"

log "Writing Nginx evidence to $evidence_dir"

capture_command "20_nginx_T.txt" nginx -T

extract_tscode_server_blocks "$evidence_dir/20_nginx_T.txt" "$evidence_dir/21_active_tscode_server_blocks.txt"
extract_relevant_location_blocks "$evidence_dir/21_active_tscode_server_blocks.txt" "$evidence_dir/22_active_relevant_location_blocks.txt"
write_location_index "$evidence_dir/22_active_relevant_location_blocks.txt" "$evidence_dir/23_active_location_targets.tsv"

if [[ -n "$repo_config_path" && -f "$repo_config_path" ]]; then
  cp "$repo_config_path" "$evidence_dir/24_repo_checking_edge_routes.conf"
  extract_relevant_location_blocks "$evidence_dir/24_repo_checking_edge_routes.conf" "$evidence_dir/25_repo_relevant_location_blocks.txt"
  write_location_index "$evidence_dir/25_repo_relevant_location_blocks.txt" "$evidence_dir/26_repo_location_targets.tsv"
  capture_command "27_nginx_relevant_diff.txt" bash -lc "diff -u \"$evidence_dir/25_repo_relevant_location_blocks.txt\" \"$evidence_dir/22_active_relevant_location_blocks.txt\" || true"
else
  repo_config_path=""
  note_failure_file "24_repo_checking_edge_routes.conf" "Could not resolve deploy/nginx/checking-edge-routes.conf from the host context. Provide repo root or config path as the second argument." 1
  printf '# Repo reference unavailable.\n' >"$evidence_dir/25_repo_relevant_location_blocks.txt"
  printf '# Repo reference unavailable.\n' >"$evidence_dir/26_repo_location_targets.tsv"
  printf 'COMMAND: diff -u repo active\n\nRepo reference unavailable, diff not generated.\n\nEXIT_CODE: 1\n' >"$evidence_dir/27_nginx_relevant_diff.txt"
fi

api_targets="$(targets_for_pattern "$evidence_dir/23_active_location_targets.tsv" '\\/api\\/?')"
user_targets="$(targets_for_pattern "$evidence_dir/23_active_location_targets.tsv" '\\/checking\\/user')"
transport_targets="$(targets_for_pattern "$evidence_dir/23_active_location_targets.tsv" '\\/checking\\/transport')"
generic_checking_targets="$(awk -F'[|][|][|]' '$1 ~ /^[[:space:]]*location[[:space:]]+\/checking\/?[[:space:]]*\{/ && $2 != "" { print $2 }' "$evidence_dir/23_active_location_targets.tsv" | sort -u | paste -sd',' -)"

has_8000=0
has_split=0
if has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:8000'; then
  has_8000=1
fi
if has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:18080' \
  && has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:18082' \
  && has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:18083'; then
  has_split=1
fi

routing_answer='inconclusivo'
if [[ $has_8000 -eq 1 ]] && has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:1808[0-3]'; then
  routing_answer='ambos em configurações diferentes'
elif [[ $has_8000 -eq 1 ]]; then
  routing_answer='127.0.0.1:8000'
elif [[ $has_split -eq 1 ]]; then
  routing_answer='18080/18082/18083'
elif has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:1808[0-3]'; then
  routing_answer='split parcial ou inconclusivo'
fi

if ! grep -q 'tscode\.com\.br' "$evidence_dir/21_active_tscode_server_blocks.txt"; then
  drifts+=("crítica: nenhum server block ativo para tscode.com.br foi encontrado no nginx -T capturado")
fi

if [[ $has_8000 -eq 1 ]] && has_line_pattern "$evidence_dir/22_active_relevant_location_blocks.txt" '127\.0\.0\.1:1808[0-3]'; then
  drifts+=("crítica: o edge ativo mistura upstream monolítico em 127.0.0.1:8000 com upstreams split 18080/18082/18083")
fi

if [[ -n "$generic_checking_targets" ]] && [[ "$generic_checking_targets" == *'127.0.0.1:8000'* ]]; then
  drifts+=("crítica: existe location genérica /checking/ apontando para 127.0.0.1:8000, o que pode sobrepor ou conflitar com o cutover split de user/admin/transport")
fi

if [[ -n "$repo_config_path" ]]; then
  expected_api='127.0.0.1:18080'
  expected_user='127.0.0.1:18082/'
  expected_transport='127.0.0.1:18083/'

  if [[ -z "$api_targets" ]]; then
    drifts+=("crítica: nenhum upstream ativo foi encontrado para /api/")
  elif [[ ",$api_targets," != *",$expected_api,"* ]]; then
    drifts+=("crítica: /api/ não aponta para $expected_api; ativos observados: ${api_targets:-nenhum}")
  fi

  if [[ -z "$user_targets" ]]; then
    drifts+=("crítica: nenhum upstream ativo foi encontrado para /checking/user")
  elif [[ ",$user_targets," != *",$expected_user,"* ]]; then
    drifts+=("crítica: /checking/user não aponta para $expected_user; ativos observados: ${user_targets:-nenhum}")
  fi

  if [[ -z "$transport_targets" ]]; then
    drifts+=("crítica: nenhum upstream ativo foi encontrado para /checking/transport")
  elif [[ ",$transport_targets," != *",$expected_transport,"* ]]; then
    drifts+=("crítica: /checking/transport não aponta para $expected_transport; ativos observados: ${transport_targets:-nenhum}")
  fi

  if grep -Eq '^[+-][^+-]' "$evidence_dir/27_nginx_relevant_diff.txt"; then
    drifts+=("importante: os blocos relevantes do edge ativo divergem do arquivo versionado; conferir 27_nginx_relevant_diff.txt")
  fi


  if ! has_header_pattern "$evidence_dir/23_active_location_targets.tsv" '\\/checking\\/user\\/[[:space:]]*\\{'; then
    drifts+=("importante: bloco explícito para /checking/user/ não foi encontrado no edge ativo")
  fi

  if ! has_header_pattern "$evidence_dir/23_active_location_targets.tsv" '\\/checking\\/transport\\/[[:space:]]*\\{'; then
    drifts+=("importante: bloco explícito para /checking/transport/ não foi encontrado no edge ativo")
  fi
else
  drifts+=("importante: o arquivo versionado deploy/nginx/checking-edge-routes.conf não foi localizado no host; a comparação ficou parcialmente bloqueada")
fi

if [[ ${#drifts[@]} -eq 0 ]]; then
  drifts+=("nenhum drift direcionado foi detectado nesta coleta; conferir o diff bruto e o nginx -T completo")
fi

summary_file="$evidence_dir/99_nginx_summary.txt"
{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Stack directory detected: %s\n' "${stack_dir:-unknown}"
  printf 'Repo config path: %s\n' "${repo_config_path:-unavailable}"
  printf 'Routing answer: %s\n' "$routing_answer"
  printf 'Upstreams observed for /api/: %s\n' "${api_targets:-nenhum}"
  printf 'Upstreams observed for /checking/user: %s\n' "${user_targets:-nenhum}"
  printf 'Upstreams observed for /checking/transport: %s\n' "${transport_targets:-nenhum}"
  printf 'Upstreams observed for generic /checking/: %s\n' "${generic_checking_targets:-nenhum}"
  printf '\nDrifts found:\n'
  for drift in "${drifts[@]}"; do
    printf -- '- %s\n' "$drift"
  done
  printf '\nRelevant evidence files:\n'
  printf -- '- 20_nginx_T.txt\n'
  printf -- '- 21_active_tscode_server_blocks.txt\n'
  printf -- '- 22_active_relevant_location_blocks.txt\n'
  printf -- '- 24_repo_checking_edge_routes.conf\n'
  printf -- '- 25_repo_relevant_location_blocks.txt\n'
  printf -- '- 27_nginx_relevant_diff.txt\n'
  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf '\nCommands with non-zero exit code: none\n'
  else
    printf '\nCommands with non-zero exit code: %s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
} >"$summary_file"

manifest_path="$evidence_dir/20_nginx_manifest.txt"
{
  printf 'evidence_dir=%s\n' "$evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '20_nginx_T.txt' \
    '21_active_tscode_server_blocks.txt' \
    '22_active_relevant_location_blocks.txt' \
    '23_active_location_targets.tsv' \
    '24_repo_checking_edge_routes.conf' \
    '25_repo_relevant_location_blocks.txt' \
    '26_repo_location_targets.tsv' \
    '27_nginx_relevant_diff.txt' \
    '99_nginx_summary.txt'
} >"$manifest_path"

log "Nginx configuration capture finished"
log "Return the files listed in $manifest_path"