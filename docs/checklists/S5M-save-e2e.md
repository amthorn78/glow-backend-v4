# S5M-save-e2e — End-to-End Save Checklist

## Current Status (Pre-Fix)

### Frontend Request
- ✅ **Method**: PUT /api/profile/birth-data
- ✅ **CSRF Header**: x-csrf-token present
- ✅ **Content-Type**: application/json
- ✅ **Payload Format**: Valid JSON with date/time/timezone/location/coordinates
- ✅ **Credentials**: Cookies included

### Backend Route
- ✅ **Route Exists**: PUT /api/profile/birth-data defined
- ✅ **Decorators**: @require_auth → @csrf_protect (correct order)
- ✅ **CSRF Validation**: Passes (no 403 errors)
- ✅ **Auth Validation**: Passes (no 401 errors)

### Request Processing
- ✅ **JSON Parsing**: request.get_json() works
- ✅ **Normalizer Call**: normalize_birth_data_request() executes
- ❌ **Field Mapping**: Incorrect re-mapping after normalization
- ❌ **Validation**: Never reached due to field mapping bug
- ❌ **Database Write**: Never reached
- ❌ **Response**: 500 error returned

### Response
- ❌ **Status**: 500 Internal Server Error
- ✅ **Headers**: Cache-Control: no-store present
- ❌ **Body**: {"error":"server_error","message":"Failed to update birth data"}

## Expected Status (Post-Fix)

### Gx1_put_writer_fix Applied
- ✅ **Field Mapping**: Use normalized_data directly
- ✅ **Validation**: BirthDataValidator.validate_birth_data() succeeds
- ✅ **Database Write**: Upsert to BirthData table
- ✅ **Response**: 200 with birth_data object

### End-to-End Flow
1. **FE Submit** → ✅ PUT with CSRF header
2. **BE Auth** → ✅ Session validation passes
3. **BE CSRF** → ✅ Double-submit validation passes  
4. **BE Normalize** → ✅ date/time → birth_date/birth_time
5. **BE Validate** → ✅ HH:mm and YYYY-MM-DD format checks
6. **BE Persist** → ✅ Upsert to database with seconds=00
7. **BE Response** → ✅ 200 with canonical birth_data
8. **FE Update** → ✅ Cache refresh shows persisted values

## Test Matrix

### Happy Path
```bash
# Login
curl -c cookies.txt -X POST https://www.glowme.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@glow.app","password":"admin123"}'
# Expected: 200 + Set-Cookie: glow_csrf

# Save birth data  
TOKEN=$(grep glow_csrf cookies.txt | awk '{print $7}')
curl -b cookies.txt -H "X-CSRF-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT https://www.glowme.io/api/profile/birth-data \
  -d '{"date":"1990-05-15","time":"21:17","timezone":"America/New_York"}'
# Expected: 200 + birth_data object

# Verify persistence
curl -b cookies.txt https://www.glowme.io/api/auth/me
# Expected: birth_time: "21:17", birth_date: "1990-05-15"
```

### Negative Cases
```bash
# Invalid time format
curl -b cookies.txt -H "X-CSRF-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT https://www.glowme.io/api/profile/birth-data \
  -d '{"date":"1990-05-15","time":"25:99"}'
# Expected: 400 + validation details

# Missing CSRF
curl -b cookies.txt -H "Content-Type: application/json" \
  -X PUT https://www.glowme.io/api/profile/birth-data \
  -d '{"date":"1990-05-15","time":"21:17"}'
# Expected: 403 + CSRF_MISSING

# Invalid CSRF
curl -b cookies.txt -H "X-CSRF-Token: WRONG" \
  -H "Content-Type: application/json" \
  -X PUT https://www.glowme.io/api/profile/birth-data \
  -d '{"date":"1990-05-15","time":"21:17"}'
# Expected: 403 + CSRF_INVALID
```

## Verification Checklist

### Pre-Fix (Current State)
- [ ] PUT /api/profile/birth-data → 500
- [ ] Frontend saves fail
- [ ] Users cannot update birth data
- [ ] GET /api/auth/csrf → 500

### Post Gx1_put_writer_fix
- [ ] PUT /api/profile/birth-data → 200
- [ ] Frontend saves succeed  
- [ ] /api/auth/me reflects new values
- [ ] No save→revert behavior
- [ ] Validation errors return 400 with details
- [ ] CSRF enforcement returns 403 with codes

### Post Gx2_csrf_integrity  
- [ ] GET /api/auth/csrf → 200
- [ ] Token refresh works
- [ ] CLI workflows functional
- [ ] Cache-Control: no-store on all paths

## Risk Assessment

### Gx1_put_writer_fix
- **Risk**: Very Low
- **Scope**: Single function field mapping
- **Rollback**: Single commit revert
- **Validation**: Align with working POST routes

### Gx2_csrf_integrity
- **Risk**: Low  
- **Scope**: CSRF rotation endpoint only
- **Rollback**: Single commit revert
- **Validation**: Login mint and validation unchanged

