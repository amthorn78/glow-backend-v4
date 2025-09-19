#!/bin/bash
# --- setup
set -euo pipefail
BASE=https://www.glowme.io
EMAIL='admin@glow.app'      # replace
PASS='admin123'             # replace
rm -f cookies.txt

echo "=== BE-1 Round-Trip Test ==="

# 0) unauth health (expect 401)
echo "0) Unauth health check:"
curl -sS -i "$BASE/api/auth/me" | sed -n '1p'

# 1) login (captures session cookie)
echo "1) Login:"
curl -sS -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/auth/login" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" -o /dev/null

# 2) warm read to set CSRF cookie
echo "2) Warm read for CSRF:"
curl -sS -c cookies.txt -b cookies.txt "$BASE/api/auth/me" -o /dev/null

# 3) extract CSRF token from cookie jar
CSRF=$(awk 'tolower($0) ~ /glow_csrf/ {print $7}' cookies.txt); echo "3) CSRF=$CSRF"

# 4) HAPPY PATH WRITE (expect: HTTP 204 + Cache-Control: no-store)
echo "4) Happy path write:"
curl -sS -i -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -X PUT "$BASE/api/profile/preferences" \
  -d '{"preferred_pace":"medium"}' | sed -n '1p;/^[Cc]ache-[Cc]ontrol:/p'

# 5) READ-BACK (expect: "medium")
echo "5) Read-back check:"
curl -sS -c cookies.txt -b cookies.txt "$BASE/api/auth/me" | \
  grep -o '"preferred_pace":"[^"]*"' || echo "No preferred_pace found"

echo ""
echo "=== Negatives ==="

# N1) Missing CSRF (expect 403)
echo "N1) Missing CSRF:"
curl -sS -i -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -X PUT "$BASE/api/profile/preferences" \
  -d '{"preferred_pace":"medium"}' | sed -n '1p'

# N2) Bad enum (expect 400 validation_error)
echo "N2) Bad enum:"
curl -sS -i -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -X PUT "$BASE/api/profile/preferences" \
  -d '{"preferred_pace":"turbo"}' | sed -n '1p;$p'

# N3) Unknown key (expect 400 validation_error with unknown_keys)
echo "N3) Unknown key:"
curl -sS -i -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -X PUT "$BASE/api/profile/preferences" \
  -d '{"preferred_pace":"medium","extra":"nope"}' | sed -n '1p;$p'

echo ""
echo "=== Test Complete ==="
