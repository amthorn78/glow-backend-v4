# Gx1_put_writer_fix_conditional — Code Review Document

## Title & Summary

Fix PUT /api/profile/birth-data to use shared normalizer+validator pipeline, removing field re-mapping bug that causes 500 errors. Align with working POST writers for consistent behavior.

**Root Cause**: PUT handler incorrectly re-maps normalized fields (`birth_date` → `date`), causing validation to fail on missing keys.

**Solution**: Remove field re-mapping and use normalized_data directly, identical to working POST routes.

## Files to Touch

1. **app.py** (lines ~2910-2935): Remove field re-mapping logic, use normalized_data directly
2. **app.py** (lines ~2935-2940): Add keys-only request_shape_keys logging on validation errors

**Total**: 2 sections in 1 file, ~25 LOC changes

## Proposed Changes (Unified Diffs)

### app.py - Fix PUT Handler Pipeline

```diff
@@ -2888,7 +2888,9 @@ def put_profile_birth_data():
 @app.route('/api/profile/birth-data', methods=['PUT'], strict_slashes=False)
 @require_auth
 @csrf_protect(session_store, validate_auth_session)
 def put_profile_birth_data():
     """Update user's birth data for profile management - S3-A5a strict validation"""
     try:
-        # BE-DECOR-ORDER-06: Diagnostic logging
-        print(f"save.birth.put.start user_id={g.user} has_csrf_header={bool(request.headers.get('X-CSRF-Token'))} has_session_cookie={bool(request.cookies.get('glow_session'))}")
-        
         # Ensure JSON request
         if not request.is_json:
             return jsonify({'error': 'validation_error', 'details': {'content_type': ['must be application/json']}}), 415
         
-        payload = request.get_json() or {}
+        raw = request.get_json(silent=True) or {}
         
         # G2F_1: Normalize wrapper/camelCase to canonical before validation
-        payload = normalize_birth_data_request('PUT /api/profile/birth-data', payload)
+        normalized_data = normalize_birth_data_request(raw, 'PUT /api/profile/birth-data')
         
         # S3-A5a: Apply strict validation
         from birth_data_validator import BirthDataValidator, ValidationError, create_validation_error_response
         
         try:
-            # Map frontend field names to validator field names
-            validator_payload = {}
-            if 'date' in payload:
-                validator_payload['birth_date'] = payload['date']
-            if 'time' in payload:
-                validator_payload['birth_time'] = payload['time']
-            if 'timezone' in payload:
-                validator_payload['timezone'] = payload['timezone']
-            if 'location' in payload:
-                validator_payload['birth_location'] = payload['location']
-            if 'latitude' in payload:
-                validator_payload['latitude'] = payload['latitude']
-            if 'longitude' in payload:
-                validator_payload['longitude'] = payload['longitude']
-            
-            # Validate with strict validator
-            validated_data = BirthDataValidator.validate_birth_data(validator_payload)
+            # Validate using central validator (validates only provided keys - intrinsic partial mode)
+            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
             
         except ValidationError as ve:
-            # Log validation failure
-            failed_fields = list(ve.details.keys())
-            app.logger.info(f"write_validation_fail route='PUT /api/profile/birth-data' fields={failed_fields} reason='validation_error'")
-            # G2F_0: Log request shape keys on validation error
-            log_request_shape_keys('PUT /api/profile/birth-data', payload)
+            # Log request shape on validation failure with diagnostics (keys only)
+            log_request_shape_keys('PUT /api/profile/birth-data', raw)
             return create_validation_error_response(ve)
```

**Key Changes Applied**:
1. **normalize_signature**: Uses exact signature `normalize_birth_data_request(raw, 'PUT /api/profile/birth-data')`
2. **validator_partial_flag**: Uses intrinsic partial mode (validates only provided keys)
3. **typed_error_helper_consistency**: Uses `create_validation_error_response` helper
4. **keys_only_logging_only**: Removed PII print statement, uses `log_request_shape_keys` helper
5. **imports_consistency**: Uses same imports as POST routes (`from birth_data_validator import...`)
6. **decorators_unchanged**: Shows exact decorator order `@require_auth` → `@csrf_protect(session_store, validate_auth_session)`
7. **headers_no_store**: Response already includes `Cache-Control: no-store` (unchanged)

## Contracts & Flags

### CSRF Protection
- ✅ **Decorators**: @require_auth → @csrf_protect (unchanged)
- ✅ **Double-submit**: X-CSRF-Token header validation (unchanged)
- ✅ **Error responses**: 403 CSRF_MISSING/CSRF_INVALID (unchanged)

### Validator Contract
- ✅ **Input**: Normalized payload (birth_date, birth_time, etc.)
- ✅ **Partial mode**: Validates only provided keys (intrinsic)
- ✅ **Output**: Validated data with proper types
- ✅ **Errors**: ValidationError with typed details

### Logging Contract
- ✅ **Keys only**: No PII or values logged
- ✅ **Diagnostics**: alias_detected, wrapper_detected booleans
- ✅ **Route identification**: 'PUT /api/profile/birth-data'
- ✅ **Error context**: validation_errors list
- ✅ **Helper function**: `log_request_shape_keys()` extracts and logs **keys only** and never logs values/PII

### Response Contract
- ✅ **Success**: 200 with canonical birth_data object
- ✅ **Validation error**: 400 with typed details
- ✅ **CSRF error**: 403 with typed reason
- ✅ **Headers**: Cache-Control: no-store, Content-Type: application/json

## Risk & Rollback

### Risk Assessment
- **Risk Level**: Very Low
- **Scope**: Single function field mapping logic
- **Impact**: Fixes 500 errors, enables frontend saves
- **Dependencies**: None (uses existing shared utilities)

### Rollback Plan
- **Method**: Single-commit revert
- **Command**: `git revert <commit_sha>`
- **Verification**: PUT returns to 500 behavior
- **Recovery time**: < 5 minutes

### Safety Measures
- ✅ **Shared utilities**: Uses same normalizer+validator as working routes
- ✅ **Decorator order**: Unchanged CSRF protection
- ✅ **Database logic**: Unchanged upsert behavior
- ✅ **Response format**: Unchanged canonical structure

## CLI Test Plan

### Setup
```bash
export HOST="www.glowme.io"  # If not resolving, set HOST="glowme.io"
export COOKIES="cookies_gx1_test.txt"
rm -f "$COOKIES"
```

### 1. Login and Get CSRF Token
```bash
# Login
curl -i -c "$COOKIES" -X POST "https://$HOST/api/auth/login" \
  -H "Content-Type: application/json" \
  --data '{"email":"admin@glow.app","password":"admin123"}'
# Expected: 200 + Set-Cookie: glow_csrf

# Extract CSRF token
CSRF_TOKEN=$(grep glow_csrf "$COOKIES" | tail -n1 | awk '{print $7}')
echo "CSRF Token: $CSRF_TOKEN"
```

### 2. Happy Path - Valid PUT
```bash
curl -i -b "$COOKIES" -H "X-CSRF-Token: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT "https://$HOST/api/profile/birth-data" \
  --data '{"birth_date":"1990-05-15","birth_time":"21:17","timezone":"America/New_York"}'
# Expected: 200 + birth_data object
```

### 3. Verify Persistence
```bash
curl -i -b "$COOKIES" "https://$HOST/api/auth/me"
# Expected: birth_time: "21:17", birth_date: "1990-05-15"
```

### 4. Negative Test - Invalid Time Format
```bash
curl -i -b "$COOKIES" -H "X-CSRF-Token: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT "https://$HOST/api/profile/birth-data" \
  --data '{"birth_date":"1990-05-15","birth_time":"21:17:00"}'
# Expected: 400 + validation details (seconds not allowed)
```

### 5. Negative Test - Invalid Time Value
```bash
curl -i -b "$COOKIES" -H "X-CSRF-Token: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT "https://$HOST/api/profile/birth-data" \
  --data '{"birth_date":"1990-05-15","birth_time":"25:99"}'
# Expected: 400 + validation details (invalid time)
```

### 6. Negative Test - Missing CSRF
```bash
curl -i -b "$COOKIES" -H "Content-Type: application/json" \
  -X PUT "https://$HOST/api/profile/birth-data" \
  --data '{"birth_date":"1990-05-15","birth_time":"21:17"}'
# Expected: 403 + CSRF_MISSING
```

### 7. Negative Test - Invalid CSRF
```bash
curl -i -b "$COOKIES" -H "X-CSRF-Token: WRONG_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT "https://$HOST/api/profile/birth-data" \
  --data '{"birth_date":"1990-05-15","birth_time":"21:17"}'
# Expected: 403 + CSRF_INVALID
```

## Expected Outcomes

### Before Fix
- PUT /api/profile/birth-data → 500 Internal Server Error
- Frontend saves fail completely
- Users cannot update birth data via UI

### After Fix
- PUT /api/profile/birth-data → 200 with birth_data object
- Frontend saves succeed end-to-end
- /api/auth/me reflects updated values immediately
- No save→revert behavior
- Proper validation errors (400) for invalid inputs
- Proper CSRF errors (403) for missing/invalid tokens

## Implementation Notes

### Alignment with POST Routes
This change makes PUT /api/profile/birth-data identical to working POST routes:
- POST /api/birth-data (lines 2572-2650)
- POST /api/profile/update-birth-data (lines 3175-3250)

### Normalizer Behavior
The normalize_birth_data_request function correctly handles:
- Wrapper removal: `{birthData: {...}}` → `{...}`
- camelCase conversion: `birthDate` → `birth_date`
- Alias mapping: `date` → `birth_date`, `time` → `birth_time`
- Empty optional dropping: `timezone: ""` → removed

### Validator Behavior
BirthDataValidator.validate_birth_data provides:
- HH:mm time format validation (no seconds)
- YYYY-MM-DD date format validation
- Partial update support (validates only provided keys)
- Typed error details for frontend consumption

## LOC Summary

- **Removed**: ~18 lines (field re-mapping logic)
- **Added**: ~3 lines (variable renaming and direct validator call)
- **Net change**: ~15 lines reduction
- **Total impact**: ~20 LOC across 1 file
- **Within limits**: ✅ (≤120 LOC, ≤4 files)

## Key Improvements

### Pipeline Alignment
- **Before**: raw → normalize → re-map → validate (BUG: re-mapping after normalization)
- **After**: raw → normalize → validate (identical to working POST routes)

### Error Handling Consistency
- **Before**: Mixed ad-hoc jsonify and helper patterns
- **After**: Uses create_validation_error_response helper like POST routes

### Logging Consistency  
- **Before**: Mixed app.logger.info patterns
- **After**: Uses log_request_shape_keys helper (keys-only, no PII)

### Variable Flow Clarity
- **Before**: payload overloaded (raw → normalized)
- **After**: raw → normalized_data → validated_data (clear data flow)

