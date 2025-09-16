# G1a_BE_normalize — Code Review Doc

## Summary
- Add minimal normalizer function to handle wrapper/camelCase → snake_case conversion and drop empty-string optionals
- Wire normalizer into existing birth-data writers before BirthDataValidator
- Add structured logging for save attempts and request shape analysis on 400s
- Support partial updates (no required fields check), use central validator, no geocoding

## Files Touched
- `api/normalize.py` (new) - Pure normalizer function, ~40 lines
- `src/app.py` - Minimal integration into 2 POST routes, ~20 lines each

**Note**: The spec mentioned PUT /api/profile/birth-data but this route doesn't exist. This CRD covers the two existing birth-data writers only.

## Proposed Changes

### 1. New file: `api/normalize.py`

```python
"""
Request normalization utilities for birth data writers
Handles wrapper/camelCase → snake_case conversion and empty optional dropping
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

def normalize_birth_data_request(data: Dict[str, Any], route: str) -> Dict[str, Any]:
    """
    Normalize birth data request payload
    
    Args:
        data: Raw request data
        route: Route name for logging
        
    Returns:
        Normalized data dictionary
    """
    # Handle wrapper patterns
    if 'birth_data' in data:
        data = data['birth_data']
    elif 'birthData' in data:
        data = data['birthData']
    
    # Field mapping: camelCase → snake_case + short aliases
    field_mapping = {
        'birthDate': 'birth_date',
        'birthTime': 'birth_time',
        'birthLocation': 'birth_location',
        'date': 'birth_date',
        'time': 'birth_time'
    }
    
    # Optional fields that should be dropped if empty
    optional_fields = {'timezone', 'latitude', 'longitude', 'birth_location'}
    
    normalized = {}
    dropped_empty = []
    alias_detected = False
    wrapper_detected = 'birth_data' in data or 'birthData' in data
    
    for key, value in data.items():
        canonical_key = field_mapping.get(key, key)
        
        # Track if we used an alias
        if key != canonical_key:
            alias_detected = True
        
        # Drop empty optional fields
        if canonical_key in optional_fields and (value == '' or value is None):
            dropped_empty.append(canonical_key)
            continue
            
        normalized[canonical_key] = value
    
    # Log save attempt
    logger.info("save_attempt", extra={
        'route': route,
        'normalized_keys': list(normalized.keys()),
        'dropped_empty': dropped_empty,
        'alias_detected': alias_detected,
        'wrapper_detected': wrapper_detected
    })
    
    return normalized
```

### 2. Update `src/app.py` - POST /api/birth-data route

```python
@app.route('/api/birth-data', methods=['POST'])
@require_auth
@csrf_protect  # CSRF decorator present and ordered after auth
def save_birth_data():
    """Save user's birth data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Normalize request
        from api.normalize import normalize_birth_data_request
        from birth_data_validator import BirthDataValidator, ValidationError
        
        normalized_data = normalize_birth_data_request(data, 'POST /api/birth-data')
        
        # Validate using central validator (validates only provided keys - intrinsic partial mode)
        try:
            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
        except ValidationError as e:
            # Log request shape on validation failure with diagnostics
            logger.info("request_shape_keys", extra={
                'route': 'POST /api/birth-data',
                'keys': list(data.keys()),
                'validation_errors': list(e.details.keys()),
                'alias_detected': 'birthDate' in data or 'birthTime' in data or 'date' in data or 'time' in data,
                'wrapper_detected': 'birth_data' in data or 'birthData' in data
            })
            return jsonify({
                'error': 'validation_error',
                'message': 'One or more fields are invalid',
                'details': e.details
            }), 400
        
        # Get or create birth data record
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            birth_data = BirthData(user_id=request.current_user_id)
            db.session.add(birth_data)
        
        # Update only provided fields
        for field, value in validated_data.items():
            setattr(birth_data, field, value)
        
        # Log successful save
        logger.info("save_attempt", extra={
            'route': 'POST /api/birth-data',
            'accepted_keys': list(validated_data.keys()),
            'status': 'success'
        })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Birth data saved successfully',
            'birth_data': birth_data.to_dict()
        })
    
    except Exception as e:
        # ... existing error handling
```

### 3. Update `src/app.py` - POST /api/profile/update-birth-data route

```python
@app.route('/api/profile/update-birth-data', methods=['POST'])
@require_auth
@csrf_protect  # CSRF decorator present and ordered after auth
def update_birth_data():
    """Update user birth data with enhanced location support and recalculate compatibility"""
    try:
        data = request.get_json()
        
        # Normalize request
        from api.normalize import normalize_birth_data_request
        from birth_data_validator import BirthDataValidator, ValidationError
        
        normalized_data = normalize_birth_data_request(data, 'POST /api/profile/update-birth-data')
        
        # Validate using central validator (validates only provided keys - intrinsic partial mode)
        try:
            validated_data = BirthDataValidator.validate_birth_data(normalized_data)
        except ValidationError as e:
            # Log request shape on validation failure with diagnostics
            logger.info("request_shape_keys", extra={
                'route': 'POST /api/profile/update-birth-data',
                'keys': list(data.keys()),
                'validation_errors': list(e.details.keys()),
                'alias_detected': 'birthDate' in data or 'birthTime' in data or 'date' in data or 'time' in data,
                'wrapper_detected': 'birth_data' in data or 'birthData' in data
            })
            return jsonify({
                'error': 'validation_error',
                'message': 'One or more fields are invalid',
                'details': e.details
            }), 400
        
        # Get or create birth data record
        birth_data = BirthData.query.get(request.current_user_id)
        if not birth_data:
            birth_data = BirthData(user_id=request.current_user_id)
            db.session.add(birth_data)
        
        # Update only provided fields
        for field, value in validated_data.items():
            setattr(birth_data, field, value)
        
        # Log successful save
        logger.info("save_attempt", extra={
            'route': 'POST /api/profile/update-birth-data',
            'accepted_keys': list(validated_data.keys()),
            'status': 'success'
        })
        
        # ... rest of existing logic (HD API calls, etc.)
```

## Contracts & Flags
- No API contract changes - response shapes remain identical
- No feature flags introduced in this gate
- Logging format: structured JSON with keys-only policy
- CSRF decorators remain intact and unchanged

## Risk & Rollback
- **Risk**: Minimal - pure normalizer with central validator integration
- **Rollback**: Single commit revert restores previous behavior
- **Safety**: Partial updates supported, empty optionals dropped before BirthDataValidator
- **Compatibility**: Handles both current request formats and new normalized formats
- **LOC**: ~80 lines total (40 normalizer + 20 per route integration)

## CLI Test Plan

### Setup
```bash
HOST="glowme.io"
COOKIES="cookies.txt"

# Login and get CSRF
curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" \
  -X POST "https://$HOST/api/auth/login" \
  -d '{"email":"admin@glow.app","password":"admin123"}'

CSRF=$(awk 'tolower($0) ~ /csrf/ {v=$7} END{print v}' "$COOKIES")
```

### Test Cases

#### 1. Empty optional dropped (partial update)
```bash
curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
  -X POST "https://$HOST/api/birth-data" \
  -d '{"birth_time":"21:17","timezone":""}'
```
**Expected**: HTTP 200, logs show `dropped_empty:['timezone']`, only birth_time updated

#### 2. CamelCase wrapper normalization
```bash
curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
  -X POST "https://$HOST/api/profile/update-birth-data" \
  -d '{"birthData":{"birthTime":"14:30"}}'
```
**Expected**: HTTP 200, partial update successful

#### 3. Invalid time rejected with typed error
```bash
curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
  -X POST "https://$HOST/api/profile/update-birth-data" \
  -d '{"birthData":{"birthTime":"21:17:30"}}'
```
**Expected**: HTTP 400 with `error: validation_error, details: {birth_time: [...]}`, logs show request_shape_keys

#### 4. Verify /api/auth/me reflects changes
```bash
curl -sS -c "$COOKIES" -b "$COOKIES" "https://$HOST/api/auth/me" | jq '.user.birth_data'
```
**Expected**: Shows updated values from successful partial saves above

