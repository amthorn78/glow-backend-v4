# CRD: S6-MP3_cookie_flags

## Goal
Harden auth/CSRF cookies by guaranteeing secure attributes on both `glow_session` and `glow_csrf` cookies.

## Problem
Current cookie implementation uses environment variables and generic helpers that may not consistently apply proper security flags.

## Solution
Update cookie setters to use hardcoded secure attributes, ensuring consistent security posture.

## Files Changed
- `cookies.py` (1 file, 2 functions modified)

## Unified Diff

```diff
@@ -71,7 +71,18 @@ def clear_cookie(response, name):
 def set_session_cookie(response, session_id, max_age=1800):
     """
     Set the main session cookie with proper security attributes
     
     Args:
         response: Flask response object
         session_id (str): Session identifier
         max_age (int): Cookie max age in seconds (default: 30 minutes)
     
     Returns:
         Flask response object with session cookie set
     """
-    return set_cookie(response, 'glow_session', session_id, max_age=max_age)
+    # Session cookies must be HttpOnly for security
+    response.set_cookie(
+        'glow_session',
+        session_id,
+        max_age=max_age,
+        domain=SESSION_COOKIE_DOMAIN,
+        path='/',
+        httponly=True,      # Prevent JS access to session cookie
+        secure=True,        # HTTPS only (always true in prod)
+        samesite='Lax'      # CSRF protection while allowing navigation
+    )
+    return response

@@ -120,8 +131,8 @@ def set_csrf_cookie_with_fallback(response, csrf_token, max_age=1800):
     # Set CSRF cookie with specific attributes (HttpOnly=false for JS access)
     response.set_cookie(
         'glow_csrf', 
         csrf_token,
         max_age=max_age,
         domain=use_domain,  # None for host-only when domain mismatch
         path='/',
         httponly=False,     # CSRF cookies must be JS-readable
-        secure=SESSION_SECURE,
-        samesite=SESSION_SAMESITE
+        secure=True,        # HTTPS only (always true in prod)
+        samesite='Lax'      # CSRF protection while allowing navigation
     )
     return response
```

## LOC Impact
- **Total**: 15 lines modified across 2 functions (within ≤40 LOC limit)
- **Scope**: Only affects cookie setter functions
- **Behavior**: Hardens cookie security attributes

## Cookie Security Attributes

### Session Cookie (`glow_session`)
- `HttpOnly=True` - Prevents JS access to session cookie
- `Secure=True` - HTTPS only (always true in prod)
- `SameSite=Lax` - CSRF protection while allowing navigation
- `Path=/` - Available site-wide
- `Domain=SESSION_COOKIE_DOMAIN` - Configured domain

### CSRF Cookie (`glow_csrf`)
- `HttpOnly=False` - Must be JS-readable for double-submit pattern
- `Secure=True` - HTTPS only (always true in prod)
- `SameSite=Lax` - CSRF protection while allowing navigation
- `Path=/` - Available site-wide
- `Domain=use_domain` - With fallback logic for domain mismatch

## Risk Assessment
- **Risk**: Low - cookie header changes only
- **Impact**: Improved security posture for authentication
- **Rollback**: Single-commit revert restores environment-based flags

## Test Plan
1. **Login response**: Both cookies with proper flags
2. **CSRF rotation**: CSRF cookie with proper flags
3. **Save functionality**: No regressions in birth data saves

## Acceptance Criteria
```bash
# Test A: Login response
curl -i -sS -c /tmp/glow.jar -H 'Content-Type: application/json' \
  -d '{"email":"admin@glow.app","password":"admin123"}' \
  https://glowme.io/api/auth/login | grep -i '^set-cookie'

# Expected:
# Set-Cookie: glow_session=...; Path=/; HttpOnly; Secure; SameSite=Lax
# Set-Cookie: glow_csrf=...; Path=/; Secure; SameSite=Lax

# Test B: CSRF rotation
curl -i -sS -b /tmp/glow.jar -c /tmp/glow.jar \
  https://glowme.io/api/auth/csrf | grep -i '^set-cookie'

# Expected:
# Set-Cookie: glow_csrf=...; Path=/; Secure; SameSite=Lax

# Test C: Save functionality
TOKEN=$(curl -sS -b /tmp/glow.jar https://glowme.io/api/auth/csrf | \
  sed -n 's/.*"csrf_token":"\([^"]*\)".*/\1/p')
curl -i -sS -b /tmp/glow.jar -H "X-CSRF-Token: $TOKEN" \
  -H 'Content-Type: application/json' -X PUT \
  https://glowme.io/api/profile/birth-data \
  -d '{"birth_date":"1990-05-15","birth_time":"21:17","birth_location":"New York, United States"}' \
  | head -n 1

# Expected: HTTP/2 200
```

## Preserved Functionality
- Domain fallback logic maintained
- Max-Age/Expires behavior unchanged
- Existing security headers preserved
- Cache-Control: no-store unchanged

## Out of Scope
- No changes to payloads, routes, or validation
- No CORS or CSP adjustments
- No changes to domain fallback rules

