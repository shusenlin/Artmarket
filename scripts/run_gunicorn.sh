#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export FLASK_ENV="${FLASK_ENV:-development}"
export PYTHONUNBUFFERED=1

gunicorn "app:create_app()" \
  --bind "${ARTMARKET_BIND:-127.0.0.1:5000}" \
  --workers "${ARTMARKET_WORKERS:-2}" \
  --timeout "${ARTMARKET_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
