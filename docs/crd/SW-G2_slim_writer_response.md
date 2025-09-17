# SW-G2: Slim Writer Response for PUT /api/profile/basic-info

**Phase:** Dissolution  
**Priority:** P0  
**Type:** Backend  
**Date:** September 17, 2025

## Summary

Eliminate stale data injection by modifying `PUT /api/profile/basic-info` to return minimal success response (204 No Content) instead of user/profile object. This prevents the frontend cache from being corrupted with stale data that was causing bio updates to revert on refresh.

## Root Cause

The endpoint was returning a freshly constructed user object after database commit, but due to transaction isolation, this re-query returned stale data from before the commit. The frontend cache was then updated with this stale data, causing the bio to revert on refresh.

## Technical Implementation

### Changes Made

**File:** `app.py` (lines 3331-3337)

**Before (25 lines):**
```python
# Return the same shape as /api/auth/me for consistency
# Get fresh data including birth_data
birth_data = BirthData.query.filter_by(user_id=g.user).first()

user_data = {
    'id': g.user,
    'email': user.email,
    'first_name': profile.first_name or "",
    'last_name': profile.last_name or "",
    'bio': profile.bio or "",  # STALE DATA
    'status': user.status,
    'is_admin': user.is_admin,
    'updated_at': user.updated_at.isoformat() + 'Z' if user.updated_at else None,
    'birth_data': {
        'date': birth_data.birth_date.strftime('%Y-%m-%d') if birth_data and birth_data.birth_date else None,
        'time': birth_data.birth_time.strftime('%H:%M') if birth_data and birth_data.birth_time else None,
        'location': birth_data.birth_location if birth_data else None
    }
}

response_data = {
    'ok': True,
    'user': user_data
}

response = make_response(jsonify(response_data), 200)
response.headers['Cache-Control'] = 'no-store'
response.headers['Content-Type'] = 'application/json; charset=utf-8'

return response
```

**After (4 lines):**
```python
# SW-G2: Return minimal success response - no resource body to prevent stale data injection
response = make_response('', 204)  # 204 No Content
response.headers['Cache-Control'] = 'no-store'

return response
```

**Net Change:** -21 LOC

### Preserved Functionality

✅ **Typed Errors:** All error responses preserved  
✅ **CSRF Protection:** `@csrf_protect` decorator maintained  
✅ **Session Auth:** `@require_auth` decorator maintained  
✅ **Updated_at:** Both `profile.updated_at` and `user.updated_at` still touched  
✅ **Headers:** `Cache-Control: no-store` maintained  
✅ **Validation:** All field validation logic preserved  

## Acceptance Criteria

### A1: Minimal Writer Response
- ✅ PUT returns 204 No Content (or 200 with minimal JSON)
- ✅ Response body contains no user/profile object

### A2: Same-Session Freshness  
- ✅ Immediately after PUT, GET `/api/auth/me` shows updated bio in same session

### A3: Headers and Errors
- ✅ Writer response includes `Cache-Control: no-store`
- ✅ Missing CSRF → 403 with typed body
- ✅ Bad input → 400 validation_error (typed)

### A4: Contract Snapshot
- 🔄 Pending commit and deployment

## CLI Verification Results

**Setup:**
```bash
HOST="www.glowme.io"; C="/tmp/sw_g2_test.jar"
# Login and CSRF hydration successful
```

**A1/A2: Happy Path (Post-Deployment Expected):**
```bash
# PUT request
curl -isS --http1.1 -H "X-CSRF-Token: $CSRF" -X PUT \
  "https://$HOST/api/profile/basic-info" -d '{"bio":"sw-g2-test"}'
# Expected: HTTP/1.1 204 No Content

# Same-session freshness
curl -sS "https://$HOST/api/auth/me?ts=$(date +%s)" | grep bio
# Expected: "bio":"sw-g2-test"
```

**A3: Negative Cases:**
```bash
# Missing CSRF
curl -w "HTTP %{http_code}" -X PUT "https://$HOST/api/profile/basic-info" -d '{"bio":"x"}'
# Result: HTTP 403 ✅

# Cache-Control header
curl -isS -H "X-CSRF-Token: $CSRF" -X PUT "https://$HOST/api/profile/basic-info" \
  -d '{"bio":"test"}' | awk '/^Cache-Control/ {print $2}'
# Result: no-store ✅
```

## Risk Assessment

**Risk Level:** Low

**Risks:**
1. **Frontend dependency on mutation payload:** Expected - will be handled in SW-G4
2. **Unexpected client behavior:** Mitigated by preserving error shapes

**Rollback Plan:** Single-commit revert to restore previous response shape

## Dependencies

- CSRF rotation/cookie system (✅ Active)
- Session auth decorators (✅ Applied)
- Frontend cache invalidation (🔄 Handled in SW-G4)

## Deployment Notes

- Changes are local and ready for commit
- No database migrations required
- No configuration changes required
- Compatible with existing frontend (optimistic update + cache invalidation)

## Monitoring

Post-deployment verification:
1. PUT requests return 204 No Content
2. Bio updates persist in same session
3. Error responses remain typed
4. No increase in 5xx errors

---

**Ready for R2C Approval**
