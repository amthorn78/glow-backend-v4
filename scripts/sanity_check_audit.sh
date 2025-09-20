#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts
SHORT_SHA=$(git rev-parse --short HEAD || echo "no-git")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
PD_LAST=$(tail -n1 artifacts/predeploy.txt 2>/dev/null || echo "no-predeploy")
{
  echo "repo=$(basename "$(pwd)")"
  echo "commit=${SHORT_SHA}"
  echo "time=${STAMP}"
  echo "predeploy=${PD_LAST}"
  echo "SANITY: $([[ "$PD_LAST" == *ok* || "$PD_LAST" == *OK* ]] && echo OK || echo FAIL)"
} | tee artifacts/sanity.txt
