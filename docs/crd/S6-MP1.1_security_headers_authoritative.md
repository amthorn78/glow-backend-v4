# CRD: S6-MP1.1_security_headers_authoritative

## Goal
Make backend authoritative for security headers to ensure all 4 headers reliably appear on every `/api/*` response in production.

## Problem
Current implementation uses `setdefault()` which only sets headers when absent. Reverse proxies may normalize/seed headers causing our headers to be skipped.

## Solution
Replace conditional `setdefault()` with explicit assignment to guarantee presence and consistent values.

## Files Changed
- `app.py` (1 file, 8 lines modified)

## Unified Diff

```diff
@@ -245,10 +245,10 @@ def add_cors_headers(resp):
 @app.after_request
 def add_security_headers(resp):
     """Add standard security headers to all API responses"""
     if request.path.startswith('/api/'):
-        # Add security headers (do not overwrite existing headers)
-        resp.headers.setdefault('Strict-Transport-Security', 'max-age=15552000; includeSubDomains')
-        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
-        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
-        resp.headers.setdefault('X-Frame-Options', 'DENY')
+        # Be authoritative on API responses (override any proxy-set values)
+        resp.headers['Strict-Transport-Security'] = 'max-age=15552000; includeSubDomains'
+        resp.headers['X-Content-Type-Options'] = 'nosniff'
+        resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
+        resp.headers['X-Frame-Options'] = 'DENY'
     return resp
```

## LOC Impact
- **Total**: 8 lines modified (within ≤15 LOC limit)
- **Scope**: Only affects existing `add_security_headers` function
- **Behavior**: Changes from conditional to authoritative header setting

## Headers Guaranteed
1. `Strict-Transport-Security: max-age=15552000; includeSubDomains`
2. `X-Content-Type-Options: nosniff`
3. `Referrer-Policy: strict-origin-when-cross-origin`
4. `X-Frame-Options: DENY`

## Risk Assessment
- **Risk**: Very low - header assignment only
- **Impact**: No functional changes, only header reliability
- **Rollback**: Single-commit revert restores `setdefault()` behavior

## Test Plan
1. **Health endpoint**: All 4 headers present
2. **CSRF endpoint**: `Cache-Control: no-store` + all 4 security headers
3. **No duplication**: Each header appears exactly once

## Acceptance Criteria
```bash
# Test A: Health endpoint
curl -sSI https://glowme.io/api/health | grep -E 'Strict-Transport-Security|X-Content-Type-Options|Referrer-Policy|X-Frame-Options'

# Test B: CSRF endpoint  
curl -sSI https://glowme.io/api/auth/csrf | grep -E 'Cache-Control|Strict-Transport-Security|X-Content-Type-Options|Referrer-Policy|X-Frame-Options'
```

Expected: All 4 security headers present on both endpoints, with `Cache-Control: no-store` preserved on CSRF.

## Out of Scope
- No changes to CORS or Cache-Control behavior
- No CSP/Permissions-Policy additions (future gates)
- No changes outside `/api/*` paths

