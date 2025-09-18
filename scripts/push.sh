#!/usr/bin/env bash
set -euo pipefail
bash scripts/guard_procfile.sh
git push "${@:-origin main}"
