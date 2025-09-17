# S6-G0 — Baseline Evidence (No-Code)

**Date**: 2025-09-16T18:45:00Z  
**Environment**: https://www.glowme.io  
**Tester**: Manus (CLI)  
**Goal**: Establish baseline evidence for login + CSRF + birth-data save functionality

## Environment Block

```bash
HOST=https://www.glowme.io
EMAIL=admin@glow.app
PASSWORD=admin123
CJ=./cookies.txt
```

## Test Results

### Step 0: Prepare Fresh Cookie Jar
**Command**: `rm -f $CJ`  
**Result**: ✅ PASS - Fresh cookie jar prepared

### Step 1: Login (Expect Set-Cookie: glow_session and glow_csrf)
**Command**:
```bash
curl -i -sS -c $CJ -b $CJ "$HOST/api/auth/login" \
  -H 'Content-Type: application/json' \
  --data "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
```

**Output**:
```
HTTP/2 200 
cache-control: no-store
content-type: application/json; charset=utf-8
set-cookie: glow_session=redis_78d808e1b92e4b049184b0d5d6f80474; Domain=glowme.io; Expires=Tue, 16 Sep 2025 19:15:39 GMT; Max-Age=1800; Secure; HttpOnly; Path=/; SameSite=Lax
set-cookie: glow_csrf=mX6mqlUR1qQps8M-S1epKK2WenjbK3lmMyoAZomOc5I; Expires=Tue, 16 Sep 2025 19:15:39 GMT; Max-Age=1800; Secure; Path=/; SameSite=Lax
set-cookie: flask_session=403f2c9b-cff9-4985-b4fc-462fc9e2a4cc.x3D5yq5dn5Zg74zPRc1fQoYGtqI; Expires=Tue, 16 Sep 2025 19:15:39 GMT; Secure; HttpOnly; Path=/; SameSite=Lax
{"ok":true}
```

**Verdict**: ✅ PASS - Both glow_session (HttpOnly) and glow_csrf (readable) cookies set correctly

### Step 2: CSRF Mint/Rotate (Expect 200 + no-store)
**Command**: `curl -i -sS -c $CJ -b $CJ "$HOST/api/auth/csrf"`

**Output**:
```
HTTP/2 500 
cache-control: no-store
content-type: application/json
{"code":"INTERNAL_ERROR","error":"CSRF token rotation failed","ok":false}
```

**Verdict**: ❌ FAIL - CSRF rotation endpoint returns 500 internal error

**Fallback**: Extracted CSRF from login cookie: `CSRF=mX6mqlUR1qQps8M-S1epKK2WenjbK3lmMyoAZomOc5I`

### Step 3: Happy Write (PUT birth-data with matching header)
**Command**:
```bash
curl -i -sS -c $CJ -b $CJ -X PUT "$HOST/api/profile/birth-data" \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" \
  --data '{"birth_date":"1990-05-15","birth_time":"14:30","birth_location":"NYC"}'
```

**Output**:
```
HTTP/2 200 
cache-control: no-store
content-type: application/json; charset=utf-8
{"birth_data":{"date":"1990-05-15","latitude":40.7127281,"location":"NYC","longitude":-74.0060152,"time":"14:30","timezone":"America/New_York"},"ok":true,"updated_at":"2025-09-16T18:45:55.747836Z"}
```

**Verdict**: ✅ PASS - Birth data save successful with CSRF token from login

### Step 4: Read-back Confirmation
**Command**: `curl -i -sS -c $CJ -b $CJ "$HOST/api/auth/me"`

**Output**:
```
HTTP/2 200 
cache-control: no-store
content-type: application/json; charset=utf-8
{"user":{"birth_data":{"date":"1990-05-15","latitude":40.7127281,"location":"NYC","longitude":-74.0060152,"time":"14:30","timezone":"America/New_York"},...}}
```

**Verdict**: ✅ PASS - Birth data persisted correctly (date: 1990-05-15, time: 14:30 HH:mm format)

### Step 5: Negative Test - Missing CSRF (Expect 403)
**Command**:
```bash
curl -i -sS -c $CJ -b $CJ -X PUT "$HOST/api/profile/birth-data" \
  -H 'Content-Type: application/json' \
  --data '{"birth_date":"1990-05-15","birth_time":"14:30"}'
```

**Output**:
```
HTTP/2 403 
cache-control: no-store
content-type: application/json; charset=utf-8
{"code":"CSRF_MISSING","error":"CSRF token missing","ok":false}
```

**Verdict**: ✅ PASS - Correctly rejects request without CSRF token

### Step 6: Negative Test - Mismatched CSRF (Expect 403)
**Command**:
```bash
curl -i -sS -c $CJ -b $CJ -X PUT "$HOST/api/profile/birth-data" \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: not-the-cookie" \
  --data '{"birth_date":"1990-05-15","birth_time":"14:30"}'
```

**Output**:
```
HTTP/2 403 
cache-control: no-store
content-type: application/json; charset=utf-8
{"code":"CSRF_INVALID","error":"CSRF validation failed","ok":false}
```

**Verdict**: ✅ PASS - Correctly rejects request with invalid CSRF token

## Summary Table

| Test | Status | Details |
|------|--------|---------|
| Login | ✅ PASS | Sets glow_session (HttpOnly) + glow_csrf (readable) |
| CSRF Rotation | ❌ FAIL | Returns 500 "CSRF token rotation failed" |
| Birth Data Save | ✅ PASS | Accepts valid CSRF, saves HH:mm format |
| Read-back | ✅ PASS | Data persisted correctly in /api/auth/me |
| Missing CSRF | ✅ PASS | Returns 403 CSRF_MISSING |
| Invalid CSRF | ✅ PASS | Returns 403 CSRF_INVALID |

**Overall**: 5/6 tests passing

## Headers Observed

- **Cache-Control**: `no-store` (correct for sensitive endpoints)
- **Set-Cookie**: Proper attributes (Secure, SameSite=Lax, HttpOnly where appropriate)
- **CSRF Protection**: Working for write operations
- **Content-Type**: `application/json; charset=utf-8`

## Failing Step Analysis

**Step 2 - CSRF Rotation Failure**:
- **Issue**: GET /api/auth/csrf returns 500 "CSRF token rotation failed"
- **Impact**: Frontend cannot refresh CSRF tokens during long sessions
- **Workaround**: Login-provided CSRF token works for immediate operations

## Proposed Micro-Fix Gate

**S6-G1-csrf-rotation-fix**: Fix the CSRF rotation endpoint returning 500 internal error. Hypothesis: Backend CSRF rotation logic has a bug preventing token refresh, but initial token generation during login works correctly.

