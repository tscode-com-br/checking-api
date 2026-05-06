#!/usr/bin/env bash

set -euo pipefail

label=""
url=""
contains_text=""
attempts="10"
sleep_seconds="6"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --label)
      label="$2"
      shift 2
      ;;
    --url)
      url="$2"
      shift 2
      ;;
    --contains)
      contains_text="$2"
      shift 2
      ;;
    --attempts)
      attempts="$2"
      shift 2
      ;;
    --sleep-seconds)
      sleep_seconds="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [ -z "$label" ] || [ -z "$url" ]; then
  echo "Missing required arguments for URL validation"
  exit 1
fi

attempt=1
while [ "$attempt" -le "$attempts" ]; do
  if [ -z "$contains_text" ]; then
    if curl -fsS "$url" >/dev/null; then
      exit 0
    fi
  else
    if curl -fsS "$url" | grep -F "$contains_text" >/dev/null; then
      exit 0
    fi
  fi

  sleep "$sleep_seconds"
  attempt=$((attempt + 1))
done

echo "URL validation for $label failed"
curl -i "$url" || true
exit 1