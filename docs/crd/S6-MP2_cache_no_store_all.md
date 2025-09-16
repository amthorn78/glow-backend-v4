# CRD: S6-MP2_cache_no_store_all

## Goal
Enforce `Cache-Control: no-store` and `Pragma: no-cache` on all `/api/*` responses to prevent intermediate/browser caching of sensitive JSON data.

## Problem
Currently only CSRF endpoints have cache prevention. All API responses contain sensitive data and should not be cached.

## Solution
Extend existing `add_security_headers` hook to include cache prevention headers for all `/api/*` paths.

## Files Changed
- `app.py` (1 file, 2 lines added)

## Unified Diff

```diff
@@ -245,10 +245,12 @@ def add_cors_headers(resp):
 @app.after_request
 def add_security_headers(resp):
     """Add standard security headers to all API responses"""
     if request.path.startswith('/api/'):
         # Be authoritative on API responses (override any proxy-set values)
         resp.headers['Strict-Transport-Security'] = 'max-age=15552000; includeSubDomains'
         resp.headers['X-Content-Type-Options'] = 'nosniff'
         resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
         resp.headers['X-Frame-Options'] = 'DENY'
+        # Prevent caching of sensitive API responses
+        resp.headers['Cache-Control'] = 'no-store'
+        resp.headers['Pragma'] = 'no-cache'
     return resp
```

## LOC Impact
- **Total**: 2 lines added (within ≤20 LOC limit)
- **Scope**: Only affects existing `add_security_headers` function
- **Behavior**: Adds cache prevention to all API endpoints

## Headers Added
1. `Cache-Control: no-store` - Prevents any caching
2. `Pragma: no-cache` - HTTP/1.0 compatibility for cache prevention

## Scope Confirmation
✅ **Limited to `/api/*` only** - No impact on static/asset routes  
✅ **No response body changes** - Headers only  
✅ **No status code changes** - Headers only  
✅ **Preserves existing headers** - Security headers unchanged

## Risk Assessment
- **Risk**: Very low - header addition only
- **Impact**: Prevents caching of sensitive API data
- **Rollback**: Single-commit revert removes cache headers

## Test Plan
1. **Health endpoint**: `cache-control: no-store` + `pragma: no-cache`
2. **CSRF endpoint**: Existing `cache-control: no-store` + `pragma: no-cache` 
3. **Auth/Me endpoint**: `cache-control: no-store` + `pragma: no-cache`

## Acceptance Criteria
```bash
# Test A: Health endpoint
curl -sSI https://glowme.io/api/health | grep -iE 'cache-control|pragma'

# Test B: CSRF endpoint  
curl -sSI https://glowme.io/api/auth/csrf | grep -iE 'cache-control|pragma'

# Test C: Auth/Me endpoint (requires login)
curl -sSI -b /tmp/jar https://glowme.io/api/auth/me | grep -iE 'cache-control|pragma'
```

Expected: Both `cache-control: no-store` and `pragma: no-cache` on all API endpoints.

## Header Interaction
- **Flask after_request hooks**: Multiple hooks can set headers on same response
- **Order independence**: Header assignment accumulates regardless of hook order
- **Authoritative assignment**: Direct assignment ensures presence

## Out of Scope
- No changes to non-API routes
- No changes to response bodies or status codes
- No changes to existing security headers

