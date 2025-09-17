# GLOW Intelligence App - Security Posture (S7-FSR)

This document provides an authoritative snapshot of the security controls enforced in the GLOW Intelligence App as of Sep 16, 2025. All controls have been verified via CLI and are actively monitored.

## Current Enforced Controls

### 1. Authentication & Session Management
- **Session Cookies**: `glow_session` is issued with `HttpOnly`, `Secure`, and `SameSite=Lax` flags to protect against XSS and CSRF.
- **Typed Errors**: Login failures return typed JSON errors (e.g., `INVALID_CREDENTIALS`) without leaking PII.

### 2. Cross-Site Request Forgery (CSRF) Protection
- **Double-Submit Cookies**: A `glow_csrf` cookie (Secure, SameSite=Lax) is used in conjunction with an `X-CSRF-Token` header for all state-changing requests.
- **Idempotent CSRF Endpoint**: `GET /api/auth/csrf` is idempotent and returns a fresh token with `Cache-Control: no-store`.
- **Strict Validation**: All writer endpoints (PUT, POST, DELETE) reject requests with missing or mismatched CSRF tokens with a 403 error.
- **Frontend Auto-Recovery**: The frontend has a one-shot auto-recovery mechanism for CSRF token expiration.

### 3. Security Headers
- **API-Wide Enforcement**: All `/api/*` endpoints are protected with the following headers:
  - `Strict-Transport-Security`: `max-age=15552000; includeSubDomains` (enforces HTTPS)
  - `X-Content-Type-Options`: `nosniff` (prevents MIME-sniffing)
  - `Referrer-Policy`: `strict-origin-when-cross-origin` (limits referrer information)
  - `X-Frame-Options`: `DENY` (prevents clickjacking)
  - `Cache-Control`: `no-store` and `Pragma: no-cache` (prevents caching of sensitive API responses)

### 4. Rate Limiting
- **Login Brute-Force Protection**: The login endpoint (`POST /api/auth/login`) is protected by a dual-key (IP and IP+email) rate limiter.
- **Threshold**: 5 failed attempts per 60 seconds (configurable via environment variables).
- **Typed 429 Responses**: Returns a typed 429 error with a `Retry-After` header when the limit is exceeded.

### 5. Cross-Origin Resource Sharing (CORS)
- **Restricted Origins**: CORS is not open globally. Only whitelisted origins (e.g., `https://www.glowme.io`) are allowed.
- **No Wildcard with Credentials**: `Access-Control-Allow-Origin` is never `*` when `Access-Control-Allow-Credentials` is `true`.

### 6. Logging & Telemetry
- **Keys-Only Diagnostics**: All logging and telemetry is keys-only by default, with no PII, tokens, or sensitive values logged.
- **Gated Telemetry**: CSRF telemetry is gated by the `NEXT_PUBLIC_GLOW_TELEMETRY_CSRF` flag, which is OFF by default.

### 7. Data Contracts
- **Strict Validation**: API endpoints enforce strict data formats (e.g., `YYYY-MM-DD` for dates, `HH:mm` for times).
- **Typed Validation Errors**: Returns a 400 `validation_error` with detailed field-specific error messages on bad input.

