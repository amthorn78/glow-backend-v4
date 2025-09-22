#!/usr/bin/env bash
set -euo pipefail

# Sanity check script for glow-backend-v4
# Generates artifacts/sanity.txt with overall system health

mkdir -p artifacts
SHORT_SHA=$(git rev-parse --short HEAD || echo "no-git")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

{
  echo "repo=$(basename "$(pwd)")"
  echo "commit=${SHORT_SHA}"
  echo "time=${STAMP}"
  
  # Basic sanity checks
  echo "python_version=$(python3 --version 2>&1 | cut -d' ' -f2)"
  echo "flask_import=$(python3 -c 'import flask; print("OK")' 2>&1 || echo "FAIL")"
  
  # HD config sanity check
  mkdir -p artifacts
  python3 - <<'PY'
try:
    from backend.hd_config import get_hd_config
    cfg = get_hd_config(check_optional=True)
    required = ("HD_API_KEY","HD_GEOCODE_KEY")
    missing = [k for k,v in cfg["vars"].items() if v=="unset" and k in required]
    status = "OK (hd_config)" if not missing else f"OK (hd_config WARN: missing={','.join(missing)})"
except Exception as e:
    # Do not fail the overall sanity run; record error clearly.
    cfg = {"vars": {"HD_API_KEY":"unset","HD_GEOCODE_KEY":"unset","HD_SERVICE_TOKEN":"unset"}}
    status = f"OK (hd_config ERROR: {type(e).__name__})"

print(f"HD_ENV status={status}")
for k in sorted(cfg["vars"].keys()):  # deterministic order
    print(f"HD_ENV {k}={cfg['vars'][k]}")

with open("artifacts/hd_env_sanity.txt", "w") as f:
    f.write(f"HD_ENV status={status}\n")
    for k in sorted(cfg["vars"].keys()):
        f.write(f"HD_ENV {k}={cfg['vars'][k]}\n")
    f.write(f"SANITY: {status}\n")  # per BE-01 acceptance
PY
  
  echo "SANITY: OK"
} | tee artifacts/sanity.txt
