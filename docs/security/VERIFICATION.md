# Security Verification Suite (S7-FSR)

This document contains a copy-pasteable curl suite to verify the security controls of the GLOW Intelligence App. All commands have been tested and their outputs recorded as of Sep 16, 2025.

## Setup
```bash
BASE="https://www.glowme.io"
COOKIES="security_verify.txt"
rm -f "$COOKIES"
```

## 1. Auth & Session

### Login & Cookie Flags
```bash
curl -i -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/auth/login" \
  -d '{"email":"admin@glow.app","password":"admin123"}'
```
**Expected Output:**
- `HTTP/2 200`
- `Set-Cookie` headers for `glow_session` (HttpOnly, Secure, SameSite=Lax) and `glow_csrf` (Secure, SameSite=Lax)

## 2. CSRF Protection

### Get CSRF Token
```bash
curl -i -sS -c "$COOKIES" -b "$COOKIES" "$BASE/api/auth/csrf"
```
**Expected Output:**
- `HTTP/2 200`
- `Cache-Control: no-store`
- JSON body with `csrf_token`

### Missing CSRF Token
```bash
curl -i -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" \
  -X PUT "$BASE/api/profile/birth-data" \
  -d '{"birth_time":"10:10"}'
```
**Expected Output:**
- `HTTP/2 403`
- JSON body with `{"code":"CSRF_MISSING"}`

## 3. Security Headers

### API Health Endpoint
```bash
curl -i -sS "$BASE/api/health"
```
**Expected Output:**
- `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Cache-Control: no-store`

## 4. Rate Limiting

### Trigger Rate Limit
```bash
for i in 1 2 3 4 5 6; do
  curl -sS -w "HTTP %{http_code}\n" \
    -H 'Content-Type: application/json' \
    -X POST "$BASE/api/auth/login" \
    --data '{"email":"ratelimit@test.com","password":"wrong"}' | tail -1
done
```
**Expected Output:**
- Attempts 1-5: `HTTP 401`
- Attempt 6: `HTTP 429`

### Check 429 Response
```bash
curl -i -sS -H 'Content-Type: application/json' \
  -X POST "$BASE/api/auth/login" \
  --data '{"email":"ratelimit@test.com","password":"wrong"}'
```
**Expected Output:**
- `HTTP/2 429`
- `Retry-After` header
- JSON body with `{"code":"RATE_LIMIT_LOGIN"}`

## 5. CORS

### Malicious Origin
```bash
curl -i -sS -H "Origin: https://malicious.com" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/auth/login" \
  -d '{"email":"test@example.com","password":"test"}' | grep -i "access-control"
```
**Expected Output:** No `Access-Control` headers.

### Legitimate Origin
```bash
curl -i -sS -H "Origin: https://www.glowme.io" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/auth/login" \
  -d '{"email":"test@example.com","password":"test"}' | grep -i "access-control"
```
**Expected Output:** `access-control-allow-credentials: true` and `access-control-allow-origin: https://www.glowme.io`

## 6. Data Contracts

### Invalid Time Format
```bash
CSRF=$(awk 'tolower($0) ~ /csrf/ {v=$7} END{print v}' "$COOKIES")
curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
  -X PUT "$BASE/api/profile/birth-data" \
  -d '{"birth_time":"25:99"}'
```
**Expected Output:** `{"details":{"birth_time":["must match HH:mm (24h)"]},"error":"validation_error"}`

