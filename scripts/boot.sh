#!/bin/bash
set -euo pipefail

# Default WSGI_APP if not set
WSGI_APP=${WSGI_APP:-"app:app"}

# Skip prechecks if PRECHECK_SKIP is set to 1
if [ "${PRECHECK_SKIP:-0}" -eq 1 ]; then
  echo "PRECHECK: Skipping preflight checks (PRECHECK_SKIP=1)"
else
  echo "PRECHECK: Running preflight checks..."

  # 1. Compile gate
  echo "PRECHECK: compileall"
  python -m compileall -q .
  if [ $? -ne 0 ]; then
    echo "PRECHECK_FAIL: python -m compileall failed" >&2
    exit 1
  fi

  # 2. Import probe
  echo "PRECHECK: import app"
  # Extract module name from WSGI_APP (e.g., "app:app" -> "app")
  MODULE_NAME=$(echo "$WSGI_APP" | cut -d: -f1)
  python -c "import importlib; importlib.import_module('$MODULE_NAME')"
  if [ $? -ne 0 ]; then
    echo "PRECHECK_FAIL: import probe for '$MODULE_NAME' failed" >&2
    exit 1
  fi
fi

echo "PRECHECK: Starting gunicorn --preload"
exec gunicorn --preload --bind "0.0.0.0:${PORT:-8080}" "$WSGI_APP"

