# CRD: S7-FSR-CLOSE — Security Close-Out

## Goal
Add three hardening headers + CSP (Report-Only) on all /api/* responses and land a short “security controls” doc.

## Files Changed
- `app.py` (+20 LOC)
- `docs/security/controls.md` (new, 25 lines)

**Total**: 45 LOC across 2 files

## Implementation Details

### Security Headers (`app.py`)
- **CSP (Report-Only)**: A strict `Content-Security-Policy-Report-Only` header has been added to all `/api/*` responses. This is safe for JSON APIs and provides valuable reporting without blocking.
- **Permissions-Policy**: A `Permissions-Policy` header has been added to lock down powerful browser features that are not used by the API.
- **Cross-Origin Isolation**: `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy` headers have been added to harden against cross-origin attacks.

### Security Controls Documentation (`docs/security/controls.md`)
- A comprehensive summary of all security controls has been created, including:
  - Session management
  - CSRF protection
  - Security headers
  - Rate limiting
  - Password hashing
  - CORS
  - Logging/telemetry

## Unified Diff

### `app.py`
```diff
--- a/app.py
+++ b/app.py
@@ -254,6 +254,26 @@
         # Prevent caching of sensitive API responses
         resp.headers["Cache-Control"] = "no-store"
         resp.headers["Pragma"] = "no-cache"
+        
+        # S7-FSR-CLOSE: Additional hardening headers
+        # CSP (report-only) – safe for JSON; no blocking of app behavior
+        resp.headers["Content-Security-Policy-Report-Only"] = (
+            "default-src 'none'; "
+            "frame-ancestors 'none'; "
+            "base-uri 'none'; "
+            "form-action 'self'; "
+            "connect-src 'self'"
+        )
+        
+        # Lock down powerful features we don't use from API context
+        resp.headers["Permissions-Policy"] = (
+            "geolocation=(), camera=(), microphone=(), payment=(), usb=(), "
+            "accelerometer=(), gyroscope=(), magnetometer=()"
+        )
+        
+        # Cross-origin isolation hardening (safe for API)
+        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
+        resp.headers["Cross-Origin-Resource-Policy"] = "same-site"
     return resp
 
 # OPTIONS catch-all for /api/* (bypasses auth; Railway edge always gets a 204)

```

### `docs/security/controls.md` (new file)
```markdown
# GLOW Security Controls — Snapshot (S7-FSR)

## Sessions
- Cookie: `glow_session` — HttpOnly, Secure, SameSite=Lax
- Rotation on login: Yes (new session created on each login)
- Invalidation on logout: Yes (session cleared from Redis + cookies cleared)

## CSRF
- Double-submit: `glow_csrf` (Secure, SameSite=Lax) + `X-CSRF-Token`
- Idempotent rotate: `GET /api/auth/csrf` (Cache-Control: no-store)
- FE one-shot auto-recover: enabled

## Headers (API-wide)
- HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options
- Cache-Control: no-store, Pragma: no-cache
- NEW: CSP-Report-Only, Permissions-Policy, COOP, CORP

## Rate limiting
- Login: 5 fails / 60s (IP + IP+email) → 429 + Retry-After

## Password hashing
- Algorithm: Argon2id with default parameters (time_cost=2, memory_cost=102400, parallelism=8)
- Pepper/salt handling: Argon2 built-in salt generation (32 bytes random per hash)

## CORS
- Allowlist only; no `*` with credentials

## Logging/telemetry
- Keys-only; no PII/tokens; CSRF telemetry flag OFF by default

_Last updated: Sep 16, 2025 / 75a5c09_
```

## Risk & Rollback
- **Risk**: Very low; headers are additive and safe for JSON APIs.
- **Rollback**: Single-commit revert.

## Test Plan
1. **Verify headers**: `curl -sSI $BASE/api/health` and `curl -sSI -b cookiejar -c cookiejar $BASE/api/auth/csrf` should show the new headers.
2. **Verify session lifecycle**: Confirm session rotation on login and invalidation on logout.

