# MR-S5M-save-path — Mini Code Review

## Executive Summary

**Root Cause Identified**: PUT /api/profile/birth-data route **EXISTS** but has implementation bugs causing 500 errors.

**Key Findings**:
1. ✅ **Route exists**: `PUT /api/profile/birth-data` at app.py:2888
2. ✅ **CSRF protection**: Proper decorator order (@require_auth → @csrf_protect)
3. ✅ **G1a normalizer**: Uses normalize_birth_data_request function
4. ❌ **Implementation bug**: Field mapping error causing 500 response
5. ❌ **CSRF rotation**: Still broken (separate issue)

## Full Save Path Analysis

### 1. Frontend → HTTP Request

**HAR Analysis** (from www.glowme.io.har):
```
Method: PUT /api/profile/birth-data
Headers: 
  - x-csrf-token: 0nprBEMjjTwnGq_Xucl2U__hPyoGTlWwTPZI5NGe5K4 ✅
  - content-type: application/json ✅
Payload: {
  "date": "1990-05-15",
  "time": "21:17:00", 
  "timezone": "America/New_York",
  "location": "New York, United States",
  "latitude": 40.7127281,
  "longitude": -74.0060152
}
```

**Status**: ✅ Frontend correctly targets existing endpoint with CSRF header

### 2. HTTP → Backend Route

**Route Definition** (app.py:2888-2891):
```python
@app.route('/api/profile/birth-data', methods=['PUT'], strict_slashes=False)
@require_auth
@csrf_protect(session_store, validate_auth_session)
def put_profile_birth_data():
```

**Status**: ✅ Route exists with proper decorators

### 3. Backend Processing

**Request Flow** (app.py:2904-2920):
```python
# Step 1: Normalize request (G1a)
payload = normalize_birth_data_request('PUT /api/profile/birth-data', payload)

# Step 2: Field mapping (ISSUE HERE)
validator_payload = {}
if 'date' in payload:
    validator_payload['birth_date'] = payload['date']  # ❌ BUG
if 'time' in payload:
    validator_payload['birth_time'] = payload['time']  # ❌ BUG
```

**Root Cause**: Field mapping logic error in PUT handler

**Normalizer Analysis** (api/normalize.py:24-29):
```python
field_mapping = {
    'birthDate': 'birth_date',
    'birthTime': 'birth_time', 
    'birthLocation': 'birth_location',
    'date': 'birth_date',        # ✅ Maps 'date' → 'birth_date'
    'time': 'birth_time'         # ✅ Maps 'time' → 'birth_time'
}
```

**Issue**: PUT handler expects 'date'/'time' in payload AFTER normalization, but normalizer converts them to 'birth_date'/'birth_time'

### 4. Database Write Path

**Upsert Logic** (app.py:2954-2970):
```python
birth_data = BirthData.query.get(g.user)
if not birth_data:
    birth_data = BirthData(user_id=g.user)
    db.session.add(birth_data)

# Partial updates
if birth_date is not None:
    birth_data.birth_date = birth_date
# ... etc
```

**Status**: ✅ Database logic correct (when reached)

### 5. Response Path

**Response Format** (app.py:2975-2990):
```python
response_data = {
    'ok': True,
    'birth_data': {
        'date': birth_data.birth_date.isoformat() if birth_data.birth_date else None,
        'time': format_birth_time_strict(birth_data.birth_time) if birth_data.birth_time else None,
        # ... etc
    }
}
```

**Status**: ✅ Response format correct (when reached)

## Comparison with Working Routes

### POST /api/birth-data (Working)
```python
# Uses normalized_data directly from normalizer
validated_data = BirthDataValidator.validate_birth_data(normalized_data)
```

### POST /api/profile/update-birth-data (Working)  
```python
# Uses normalized_data directly from normalizer
validated_data = BirthDataValidator.validate_birth_data(normalized_data)
```

### PUT /api/profile/birth-data (Broken)
```python
# Incorrectly re-maps already normalized data
validator_payload = {}
if 'date' in payload:  # ❌ Should be 'birth_date'
    validator_payload['birth_date'] = payload['date']
```

## Infrastructure Analysis

### CSRF System
- **Login mint**: ✅ Working (sets glow_csrf cookie)
- **Validation**: ✅ Working (proper 403 responses)
- **Rotation**: ❌ Broken (GET /api/auth/csrf → 500)

### Cookie Attributes
- **glow_csrf**: HttpOnly=false, SameSite=Lax, Secure=true ✅
- **glow_session**: HttpOnly=true, Domain=glowme.io ✅

### CORS
- **Access-Control-Allow-Credentials**: true ✅
- **Access-Control-Allow-Origin**: https://www.glowme.io ✅

## Root Causes Summary

1. **Primary Issue**: PUT handler field mapping bug
   - **File**: app.py:2910-2920
   - **Fix**: Use normalized_data directly like other routes
   - **LOC**: ~15 lines

2. **Secondary Issue**: CSRF rotation endpoint
   - **File**: csrf_protection.py:155-174
   - **Fix**: Debug session handling in mint-or-return logic
   - **LOC**: ~20 lines

## Concrete Fix List

### Gx1_put_writer_fix (Priority 1)
- **File**: app.py
- **Lines**: 2910-2920
- **Change**: Remove field re-mapping, use normalized_data directly
- **LOC**: ~15 (removal + simplification)
- **Risk**: Very low (align with working routes)

### Gx2_csrf_integrity (Priority 2)  
- **File**: csrf_protection.py
- **Lines**: 155-174
- **Change**: Debug and fix session handling in rotation endpoint
- **LOC**: ~20
- **Risk**: Low (isolated to rotation endpoint)

## Expected Outcomes

**After Gx1_put_writer_fix**:
- PUT /api/profile/birth-data → 200 (instead of 500)
- Frontend saves work end-to-end
- No more save→revert issue

**After Gx2_csrf_integrity**:
- GET /api/auth/csrf → 200 (instead of 500)
- CLI workflows fully functional
- Token refresh capability restored

## Files Referenced

- `app.py:2888-3020` - PUT /api/profile/birth-data handler
- `app.py:2572-2650` - POST /api/birth-data handler (working reference)
- `app.py:3175-3250` - POST /api/profile/update-birth-data handler (working reference)
- `api/normalize.py:1-69` - Request normalizer (working correctly)
- `csrf_protection.py:155-174` - CSRF rotation endpoint (broken)
- HAR file evidence of frontend request/response

