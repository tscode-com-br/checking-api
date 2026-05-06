#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  capture_phase0_baseline.sh [evidence_dir]

Examples:
  ./capture_phase0_baseline.sh
  ./capture_phase0_baseline.sh /root/checkcheck_incidents/2026-05-04-504-phase0
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 64
fi

default_base="/root/checkcheck_incidents"
if ! mkdir -p "$default_base" 2>/dev/null; then
  default_base="${HOME}/checkcheck_incidents"
  mkdir -p "$default_base"
fi

default_dir="$default_base/$(date -u '+%Y-%m-%d-504-phase0-%H%M%SZ')"
evidence_dir="${1:-$default_dir}"
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
}

log "Writing baseline evidence to $evidence_dir"

capture_command "01_date_u.txt" date -u
capture_command "02_timedatectl.txt" timedatectl
capture_command "03_uptime.txt" uptime
capture_command "04_hostnamectl.txt" hostnamectl
capture_command "05_uname_a.txt" uname -a
capture_command "06_free_m.txt" free -m
capture_command "07_df_h.txt" df -h
capture_command "08_nproc.txt" nproc
capture_command "09_lscpu.txt" lscpu
capture_command "10_os_release.txt" cat /etc/os-release

timezone="$(timedatectl show --property=Timezone --value 2>/dev/null || true)"
if [[ -z "$timezone" && -f /etc/timezone ]]; then
  timezone="$(tr -d '\n' </etc/timezone)"
fi
if [[ -z "$timezone" ]]; then
  timezone="unknown"
fi

boot_time="$(uptime -s 2>/dev/null || true)"
if [[ -z "$boot_time" ]]; then
  boot_time="unknown"
fi

memory_total_mb="$(free -m 2>/dev/null | awk '/^Mem:/ { print $2 }' || true)"
if [[ -z "$memory_total_mb" ]]; then
  memory_total_mb="unknown"
fi

cpu_total="$(nproc 2>/dev/null || true)"
if [[ -z "$cpu_total" ]]; then
  cpu_total="unknown"
fi

cpu_model="$(lscpu 2>/dev/null | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1 || true)"
if [[ -z "$cpu_model" ]]; then
  cpu_model="unknown"
fi

root_disk_summary="$(df -h / 2>/dev/null | awk 'NR == 2 { print "size=" $2 ", used=" $3 ", avail=" $4 ", use%=" $5 }' || true)"
if [[ -z "$root_disk_summary" ]]; then
  root_disk_summary="unknown"
fi

manifest_path="$evidence_dir/00_manifest.txt"
summary_path="$evidence_dir/99_summary.txt"

{
  printf 'evidence_dir=%s\n' "$evidence_dir"
  printf 'generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'files:\n'
  printf '%s\n' \
    '01_date_u.txt' \
    '02_timedatectl.txt' \
    '03_uptime.txt' \
    '04_hostnamectl.txt' \
    '05_uname_a.txt' \
    '06_free_m.txt' \
    '07_df_h.txt' \
    '08_nproc.txt' \
    '09_lscpu.txt' \
    '10_os_release.txt' \
    '99_summary.txt'
} >"$manifest_path"

{
  printf 'Evidence directory: %s\n' "$evidence_dir"
  printf 'Generated at UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'Timezone active: %s\n' "$timezone"
  printf 'Boot time: %s\n' "$boot_time"
  printf 'Total memory: %s MiB\n' "$memory_total_mb"
  printf 'CPU total (nproc): %s\n' "$cpu_total"
  printf 'CPU model: %s\n' "$cpu_model"
  printf 'Root disk: %s\n' "$root_disk_summary"
  if [[ ${#failed_files[@]} -eq 0 ]]; then
    printf 'Commands with non-zero exit code: none\n'
  else
    printf 'Commands with non-zero exit code: %s\n' "$(IFS=', '; echo "${failed_files[*]}")"
  fi
} >"$summary_path"

log "Baseline capture finished"
log "Return the files listed in $manifest_path"