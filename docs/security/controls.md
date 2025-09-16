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

