#!/usr/bin/env bash
# Post-deploy smoke test for GLOW backend
# Usage:
#   BASE_URL=https://... LOGIN_EMAIL=... LOGIN_PASSWORD=... bash scripts/qa_smoke.sh
#   EXPECT_WRITER=1 BASE_URL=... LOGIN_EMAIL=... LOGIN_PASSWORD=... bash scripts/qa_smoke.sh

set -euo pipefail

# --- Configuration ---
BASE_URL=${BASE_URL:?"BASE_URL is required"}
LOGIN_EMAIL=${LOGIN_EMAIL:?"LOGIN_EMAIL is required"}
LOGIN_PASSWORD=${LOGIN_PASSWORD:?"LOGIN_PASSWORD is required"}
EXPECT_WRITER=${EXPECT_WRITER:-0}

COOKIE_JAR=$(mktemp)
CURL_OPTS="-s -i --cookie-jar ${COOKIE_JAR} --cookie ${COOKIE_JAR}"

# --- Helper Functions ---
cleanup() {
  rm -f "${COOKIE_JAR}"
}
trap cleanup EXIT

check_status() {
  local response="$1"
  local expected_status="$2"
  local step="$3"
  local actual_status=$(echo "$response" | head -n 1 | awk '{print $2}')
  if [ "$actual_status" != "$expected_status" ]; then
    echo "FAIL: ${step} - Expected ${expected_status}, got ${actual_status}"
    exit 1
  fi
  echo "PASS: ${step} - Status ${actual_status}"
}

# --- Test Steps ---

# 1. Health-only: Unauthenticated check
echo "
--- Running Health Check ---"
resp_unauth=$(curl ${CURL_OPTS} "${BASE_URL}/api/auth/me")
check_status "$resp_unauth" 401 "Unauthenticated GET /api/auth/me"

# 2. Health-only: Login
login_payload=$(printf '{"email":"%s","password":"%s"}' "$LOGIN_EMAIL" "$LOGIN_PASSWORD")
resp_login=$(curl ${CURL_OPTS} -X POST -H "Content-Type: application/json" -d "$login_payload" "${BASE_URL}/api/auth/login")
check_status "$resp_login" 200 "POST /api/auth/login"

# 3. Health-only: Authenticated check
resp_auth=$(curl ${CURL_OPTS} "${BASE_URL}/api/auth/me")
check_status "$resp_auth" 200 "Authenticated GET /api/auth/me"

if [ "$EXPECT_WRITER" -ne 1 ]; then
  echo "
--- FINAL: PASS (health-only) ---"
  exit 0
fi

# 4. Writer Mode: Extract CSRF token
echo "
--- Running Writer Tests ---"
csrf_token=$(grep 'glow_csrf' "${COOKIE_JAR}" | awk '{print $7}')
if [ -z "$csrf_token" ]; then
  echo "FAIL: CSRF token not found in cookie jar"
  exit 1
fi
echo "PASS: CSRF token extracted"

# 5. Writer Mode: Happy Path
writer_payload='{"preferred_pace":"medium"}'
resp_writer=$(curl ${CURL_OPTS} -X PUT -H "Content-Type: application/json" -H "X-CSRF-Token: ${csrf_token}" -d "$writer_payload" "${BASE_URL}/api/profile/preferences")
writer_status=$(echo "$resp_writer" | head -n 1 | awk '{print $2}')
if [[ "$writer_status" != "200" && "$writer_status" != "204" ]]; then
  echo "FAIL: Writer happy path - Expected 200 or 204, got ${writer_status}"
  exit 1
fi
cache_control=$(echo "$resp_writer" | grep -i 'cache-control' | tr -d '\r')
echo "PASS: Writer happy path - Status ${writer_status} | ${cache_control}"

# 6. Writer Mode: Read-after-write confirmation
resp_confirm=$(curl ${CURL_OPTS} "${BASE_URL}/api/auth/me")
pace_value=$(echo "$resp_confirm" | tail -n 1 | jq -r '.user.preferences.preferred_pace')
if [ "$pace_value" != "medium" ]; then
  echo "FAIL: Read-after-write - Expected preferred_pace to be 'medium', got '${pace_value}'"
  exit 1
fi
echo "PASS: Read-after-write - user.preferences.preferred_pace == 'medium'"

# 7. Writer Mode: Negative Case (No CSRF)
resp_no_csrf=$(curl ${CURL_OPTS} -X PUT -H "Content-Type: application/json" -d "$writer_payload" "${BASE_URL}/api/profile/preferences")
check_status "$resp_no_csrf" 403 "Negative Case: No CSRF"

# 8. Writer Mode: Negative Case (Bad Enum)
bad_enum_payload='{"preferred_pace":"turbo"}'
resp_bad_enum=$(curl ${CURL_OPTS} -X PUT -H "Content-Type: application/json" -H "X-CSRF-Token: ${csrf_token}" -d "$bad_enum_payload" "${BASE_URL}/api/profile/preferences")
check_status "$resp_bad_enum" 400 "Negative Case: Bad Enum"

echo "
--- FINAL: PASS (writer) ---"
