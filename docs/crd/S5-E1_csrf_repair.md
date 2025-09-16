# S5-E1_csrf_repair — Code Review Doc

## Summary

- **E1_login_mint**: Add host-only cookie fallback when domain mismatch occurs during login CSRF minting
- **E2_endpoint_rotate**: Fix `/api/auth/csrf` response format and error handling for idempotent token rotation
- **E3_validator_consistency**: Ensure consistent header/cookie names and add keys-only diagnostic logging

**Root cause**: CSRF cookies set with `.glowme.io` domain are rejected by browsers on `*.railway.app`, breaking the double-submit pattern.

## Files Touched

- `cookies.py` - Add domain fallback logic with mismatch detection and logging
- `csrf_protection.py` - Fix `/api/auth/csrf` response format and improve error handling
- `app.py` - No changes needed (login flow already calls CSRF minting correctly)

## Proposed Changes

### E1_login_mint: CSRF Cookie Domain Fallback (≤30 LOC)

**File: `cookies.py`**

```diff
+def set_csrf_cookie_with_fallback(response, csrf_token, max_age=1800):
+    """
+    Set CSRF cookie with domain fallback logic
+    CSRF cookies must be JS-readable (HttpOnly=false) for double-submit pattern
+    """
+    from flask import request
+    import logging
+    
+    configured_domain = SESSION_COOKIE_DOMAIN
+    host = request.host.split(':')[0]  # Strip port for comparison
+    
+    # Check if configured domain matches request host
+    use_domain = None
+    if configured_domain and configured_domain.startswith('.'):
+        # For .glowme.io, check if request host ends with glowme.io
+        if host.endswith(configured_domain[1:]):
+            use_domain = configured_domain
+        else:
+            # Domain mismatch - use host-only cookie for CSRF only
+            logger = logging.getLogger(__name__)
+            logger.info("csrf_issue stage=mint reason=domain_mismatch")
+    else:
+        use_domain = configured_domain
+    
+    # Set CSRF cookie with specific attributes (HttpOnly=false for JS access)
+    response.set_cookie(
+        'glow_csrf', 
+        csrf_token,
+        max_age=max_age,
+        domain=use_domain,  # None for host-only when domain mismatch
+        path='/',
+        httponly=False,     # CSRF cookies must be JS-readable
+        secure=SESSION_SECURE,
+        samesite=SESSION_SAMESITE
+    )
+    return response
+
 def set_csrf_cookie(response, csrf_token, max_age=1800):
     """
-    Set the CSRF cookie with proper security attributes
-    Note: CSRF cookies must be readable by JavaScript (httponly=False)
+    Set the CSRF cookie with domain fallback
     """
-    return set_cookie(response, 'glow_csrf', csrf_token, max_age=max_age, httponly=False)
+    return set_csrf_cookie_with_fallback(response, csrf_token, max_age)
```

### E2_endpoint_rotate: Fix Response Format and Headers (≤40 LOC)

**File: `csrf_protection.py`**

```diff
+    @app.route('/api/auth/csrf', methods=['GET'])
+    def get_csrf_token():
+        """Endpoint to fetch/rotate CSRF token (session-based auth only)"""
+        logger = app.logger
+        
+        try:
+            # Validate authentication using session-based auth
+            user, error_code = validate_auth_session()
+            if not user:
+                response = jsonify({
+                    'ok': False,
+                    'error': 'Authentication required',
+                    'code': error_code or 'AUTH_REQUIRED'
+                })
+                response.headers['Cache-Control'] = 'no-store'
+                return response, 401
+            
             # Create response with new token
             response_data = {
                 'ok': True,
-               'csrf': csrf_token
+               'csrf_token': csrf_token
             }
             
             response = make_response(jsonify(response_data))
             response.headers['Content-Type'] = 'application/json; charset=utf-8'
             response.headers['Cache-Control'] = 'no-store'
             response.headers['Vary'] = 'Origin'
             
             # Set new CSRF cookie with proper max_age
             set_csrf_cookie(response, csrf_token, max_age=1800)
             
-           logger.info(f"csrf_rotate: user_id={user_id}, session_id={session_id}")
+           logger.info(f"csrf_rotate user_id={user.id} session_id={session_id} status=success")
            
            return response, 200
            
        except Exception as e:
-           logger.error(f"CSRF token rotation error: {e}")
+           logger.info(f"csrf_issue stage=rotate reason=internal_error")
+           response = jsonify({
+               'ok': False,
+               'error': 'CSRF token rotation failed',
+               'code': 'INTERNAL_ERROR'
+           })
+           response.headers['Cache-Control'] = 'no-store'
+           return response, 500
```

### E3_validator_consistency: Keys-Only Diagnostic Logging (≤20 LOC)

**File: `csrf_protection.py`**

```diff
    # Enhanced diagnostics logging (keys-only)
-   logger.info(f"csrf_validate sid_from_cookie={session_id} header_present={header_present} cookie_present={cookie_present} store_present={store_present} header_eq_cookie={header_eq_cookie} header_eq_store={header_eq_store} cookie_eq_store={cookie_eq_store} status={'valid' if is_valid else 'invalid'}")
+   if not is_valid:
+       if not csrf_header:
+           reason = 'missing'
+       elif not csrf_cookie:
+           reason = 'absent_cookie'
+       else:
+           reason = 'mismatch'
+       logger.info(f"csrf_issue stage=verify reason={reason}")
+   
    # Return appropriate error
    if not csrf_header:
        return False, 'CSRF_MISSING', 'CSRF token missing'
    if not csrf_cookie:
        return False, 'CSRF_COOKIE_MISSING', 'CSRF cookie missing'
    if not header_eq_cookie:
        return False, 'CSRF_INVALID', 'CSRF validation failed'
```

## Contracts & Flags

### CSRF Contract

| Component | Specification |
|-----------|---------------|
| **Cookie** | `glow_csrf` (HttpOnly=false, SameSite=Lax, Secure=true on HTTPS, Path=/, Domain=.glowme.io or host-only on mismatch) |
| **Header** | `X-CSRF-Token` (must equal glow_csrf cookie value for double-submit validation) |
| **Endpoint** | `GET /api/auth/csrf` (requires @require_auth, returns {"csrf_token": "..."}, 401 when unauthenticated) |
| **Writers** | `POST /api/birth-data`, `POST /api/profile/update-birth-data` (decorator order: @require_auth → @csrf_protect) |

### Environment Variables
- `SESSION_COOKIE_DOMAIN=.glowme.io` (with host-only fallback on domain mismatch)
- `SESSION_SECURE=true` (HTTPS in production)
- `SESSION_SAMESITE=Lax`

## Risk & Rollback

- **Risk**: Low - only affects CSRF cookie domain logic and response format
- **Rollback**: Single-commit revert (`git revert <sha>`)
- **No effect**: Non-auth routes unchanged; existing session cookies unaffected

## CLI Test Plan

```bash
# 1. Login and check for CSRF cookie
curl -c cookies.txt -H "Content-Type: application/json" \
  -X POST "https://glowme.io/api/auth/login" \
  -d '{"email":"admin@glow.app","password":"admin123"}'
# Expected: 200 {"ok":true} + Set-Cookie: glow_csrf=... (host-only)

# 2. Get CSRF token via endpoint
curl -b cookies.txt "https://glowme.io/api/auth/csrf"
# Expected: 200 {"csrf_token":"..."} + Set-Cookie: glow_csrf=...

# 3. Happy path - valid CSRF token
CSRF_TOKEN=$(curl -s -b cookies.txt "https://glowme.io/api/auth/csrf" | grep -o '"csrf_token":"[^"]*"' | cut -d'"' -f4)
curl -b cookies.txt -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF_TOKEN" \
  -X POST "https://glowme.io/api/birth-data" \
  -d '{"birth_time":"21:17","timezone":""}'
# Expected: 200 (normalizer processes empty timezone)

# 4. Negative - missing header
curl -b cookies.txt -H "Content-Type: application/json" \
  -X POST "https://glowme.io/api/birth-data" \
  -d '{"birth_time":"21:17"}'
# Expected: 403 {"code":"CSRF_MISSING"}

# 5. Negative - mismatched header
curl -b cookies.txt -H "Content-Type: application/json" -H "X-CSRF-Token: invalid" \
  -X POST "https://glowme.io/api/birth-data" \
  -d '{"birth_time":"21:17"}'
# Expected: 403 {"code":"CSRF_INVALID"}
```

**Expected logs**:
- Happy path: No `csrf_issue` entries
- Domain mismatch: `csrf_issue stage=mint reason=domain_mismatch`
- Missing/invalid: `csrf_issue stage=verify reason=missing|absent_cookie|mismatch`
- Rotation errors: `csrf_issue stage=rotate reason=internal_error`

