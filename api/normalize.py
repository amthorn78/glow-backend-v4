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

