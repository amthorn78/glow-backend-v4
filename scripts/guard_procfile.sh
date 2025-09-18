#!/usr/bin/env bash
set -euo pipefail
expected='web: bash scripts/boot.sh'
actual="$(tr -d '\r' < Procfile | sed -n '1p')"
if [ "$actual" != "$expected" ]; then
  echo "ERROR: Procfile mismatch."
  echo "Expected: [$expected]"
  echo "Actual:   [$actual]"
  exit 1
fi
echo "Procfile OK."
