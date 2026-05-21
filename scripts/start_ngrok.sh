#!/usr/bin/env bash
set -euo pipefail

PORT="${ARTMARKET_PORT:-5000}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is not installed. Install it first, then run this script again." >&2
  exit 1
fi

ngrok http "$PORT"
