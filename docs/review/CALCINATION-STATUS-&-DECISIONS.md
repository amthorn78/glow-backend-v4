# CALCINATION STATUS & DECISIONS

**Date:** September 16, 2025  
**Assignee:** Manus  
**Goal:** Reality-check Calcination progress and propose minimal gates to completion

---

## A) Confirmed Status vs Sprint Items

### S1.1 Authentication & Session Security

| Item | Status | Evidence |
|------|--------|----------|
| **Auth cookies hardened** | ✅ **DONE** | `cookies.py:14-16` - SESSION_SECURE, SESSION_SAMESITE, HttpOnly flags |
| **CSRF protection with rotation** | ✅ **DONE** | `csrf_protection.py:169-202` - `/api/auth/csrf` endpoint with mint-or-return logic |
| **FE CSRF auto-recovery** | ✅ **DONE** | `csrfMutations.ts:183-230` - Double-submit pattern with automatic retry |
| **Login rate limiting** | ✅ **DONE** | `rate_limit.py:22-35` - IP + IP:user buckets, configurable limits |
| **Security headers** | ✅ **DONE** | `app.py:3895-3906` - CSP, HSTS, X-Frame-Options across `/api/*` |
| **Sliding session renewal** | ❌ **MISSING** | Session touch exists (`app.py:1079`) but no idle expiry logic |
| **Structured auth logging** | ⚠️ **PARTIAL** | Ad-hoc logging present, no standardized format |

### S1.2 Profile & Birth Data

| Item | Status | Evidence |
|------|--------|----------|
| **Birth data canonical form** | ✅ **DONE** | `BirthDataFormCanonical.tsx:22-27` - HH:MM format, no seconds |
| **Birth data save/read round-trip** | ✅ **DONE** | `app.py:2247-2290` - `/api/profile/birth-data` PUT/GET working |
| **Profile basic info (name/bio)** | ✅ **DONE** | `app.py:2191-2246` - `/api/profile/basic-info` live |
| **Email read-only enforcement** | ✅ **DONE** | Email excluded from basic-info contract |
| **Time display edge cases** | ⚠️ **PARTIAL** | `formatTimeToHHMM` exists but "Invalid Date" handling unclear |
| **Logout/redirect audit** | ⚠️ **PARTIAL** | `/api/auth/logout` returns JSON but redirect loop not formally verified |

---

## B) Deprecation Recommendations

### `profile_version` - **RECOMMEND REMOVAL**

**Current State:** 
- Defined in User model (`app.py:1398`) with default=1
- Returned in `/api/auth/me` response (`app.py:1140`)
- No write endpoints or client-side usage found

**Rationale:** 
- No evidence of actual versioning logic or client cache invalidation
- Adds complexity without clear benefit
- Not referenced in frontend code

**Removal Steps:**
1. Remove `profile_version` column from User model
2. Create migration to drop column
3. Remove from `/api/auth/me` response
4. Update any tests referencing the field

### Timezone Round-trip in UI - **CONFIRMED DEPRECATED**

**Status:** Already removed from UI contract by design
- Birth data contract uses `birth_date`, `birth_time`, `birth_location` only
- Timezone handling moved to backend HD API integration
- Frontend no longer collects or displays timezone

---

## C) Minimal Gates to Exit Calcination

### Gate 1: Sliding Session Renewal (BE)
**Scope:** ~80 LOC  
**Files:** `app.py` (session validation), `redis_session_store.py`  
**Goal:** Implement idle timeout + rolling refresh logic  
**Acceptance:** Session expires after 30min idle, renews on activity  
**Rollback:** Feature flag to disable renewal logic  
**Estimate:** 30 minutes

### Gate 2: Logout JSON Error Handling (BE)
**Scope:** ~40 LOC  
**Files:** `app.py` (logout endpoint)  
**Goal:** Standardize logout response format and error cases  
**Acceptance:** Returns typed JSON, handles invalid sessions gracefully  
**Rollback:** Revert to current simple implementation  
**Estimate:** 20 minutes

### Gate 3: Time Display Edge Cases (FE)
**Scope:** ~60 LOC  
**Files:** `time.ts`, `BirthDataFormCanonical.tsx`  
**Goal:** Handle "Invalid Date" and missing time gracefully  
**Acceptance:** No "Invalid Date" shown, empty states handled  
**Rollback:** Revert to current formatTimeToHHMM  
**Estimate:** 25 minutes

### Gate 4: Profile Version Removal (BE)
**Scope:** ~50 LOC  
**Files:** `app.py` (model + endpoint), migration file  
**Goal:** Remove unused profile_version field  
**Acceptance:** Field removed, migration applied, tests pass  
**Rollback:** Re-add field with migration  
**Estimate:** 35 minutes

### Gate 5: Human Design sub_type Verification (BE)
**Scope:** ~30 LOC  
**Files:** `hd_data_extractor.py`, `app.py`  
**Goal:** Verify sub_type field populates correctly from HD API  
**Acceptance:** sub_type saves for Manifesting Generators, empty for others  
**Rollback:** No changes if working correctly  
**Estimate:** 20 minutes

---

## D) Updated Exit Criteria

**Calcination Complete When:**

1. **Session Security:** Sessions expire after 30min idle and renew on activity
2. **Error Handling:** `/api/auth/logout` returns consistent JSON format for all cases  
3. **UI Robustness:** Time display never shows "Invalid Date" or crashes on edge cases
4. **Data Cleanup:** `profile_version` field removed from model and API responses
5. **HD Integration:** `sub_type` field verified working for Manifesting Generator detection

**Exit Tests:**
- `curl` test: Session expires after idle timeout
- `curl` test: Logout returns JSON for valid/invalid sessions
- Browser test: Birth time display handles empty/invalid values
- API test: `/api/auth/me` response excludes `profile_version`
- HD test: Manifesting Generator birth data populates `sub_type`

---

## E) Open Questions / Risks

• **Multi-instance rate limiting:** Current in-memory rate limiter won't work across Railway instances → **Later:** Move to Redis-based rate limiting in post-MVP hardening

• **FE cache subtleties:** React Query cache invalidation on profile updates → **Now:** Verify current `queryClient.invalidateQueries` calls are sufficient

• **Session store backend:** Currently filesystem, should be Redis for production → **Later:** Already documented in environment audit, defer to infrastructure phase

• **CSRF enforcement:** Currently shadow mode (`CSRF_ENFORCE=false`) → **Now:** Enable in production deployment

• **Structured logging format:** Ad-hoc auth logging needs standardization → **Later:** Part of observability phase, not blocking for Calcination

---

## Summary

**Ready to Exit Calcination:** 5 small gates totaling ~260 LOC and ~2.2 hours of work. Most security foundations are solid. Primary gaps are session lifecycle management and UI edge case handling.

**Key Decision:** Remove `profile_version` as unused complexity. Focus on core session security and user experience robustness.

