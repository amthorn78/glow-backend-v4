"""
S3-A5a: Strict birth data validation module
Enforces HH:mm time format and YYYY-MM-DD date format with typed 400 errors
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class ValidationError(Exception):
    """Custom exception for validation errors with field details"""
    def __init__(self, details: Dict[str, List[str]]):
        self.details = details
        super().__init__(f"Validation failed: {details}")


class BirthDataValidator:
    """Strict validator for birth data with Rev A compliance (HH:mm, YYYY-MM-DD)"""
    
    # HH:mm 24h format regex - no seconds allowed
    TIME_REGEX = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    
    # Banned literal strings (case-insensitive)
    BANNED_LITERALS = ['invalid date']
    
    @classmethod
    def validate_birth_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate birth data payload and return normalized values
        
        Args:
            data: Raw request data dictionary
            
        Returns:
            Normalized data dictionary
            
        Raises:
            ValidationError: If validation fails with field details
        """
        errors = {}
        normalized = {}
        
        # Validate birth_time if present
        if 'birth_time' in data:
            birth_time = data['birth_time']
            if birth_time is not None:
                try:
                    normalized_time = cls._validate_time(birth_time)
                    normalized['birth_time'] = normalized_time
                except ValueError as e:
                    errors['birth_time'] = [str(e)]
            else:
                normalized['birth_time'] = None
        
        # Validate birth_date if present
        if 'birth_date' in data:
            birth_date = data['birth_date']
            if birth_date is not None:
                try:
                    normalized_date = cls._validate_date(birth_date)
                    normalized['birth_date'] = normalized_date
                except ValueError as e:
                    errors['birth_date'] = [str(e)]
            else:
                normalized['birth_date'] = None
        
        # Validate coordinates if present
        if 'latitude' in data:
            latitude = data['latitude']
            if latitude is not None:
                try:
                    normalized_lat = cls._validate_latitude(latitude)
                    normalized['latitude'] = normalized_lat
                except ValueError as e:
                    errors['latitude'] = [str(e)]
            else:
                normalized['latitude'] = None
        
        if 'longitude' in data:
            longitude = data['longitude']
            if longitude is not None:
                try:
                    normalized_lng = cls._validate_longitude(longitude)
                    normalized['longitude'] = normalized_lng
                except ValueError as e:
                    errors['longitude'] = [str(e)]
            else:
                normalized['longitude'] = None
        
        # Validate timezone if present
        if 'timezone' in data:
            timezone = data['timezone']
            if timezone is not None:
                try:
                    normalized_tz = cls._validate_timezone(timezone)
                    normalized['timezone'] = normalized_tz
                except ValueError as e:
                    errors['timezone'] = [str(e)]
            else:
                normalized['timezone'] = None
        
        # Pass through birth_location without validation (string field)
        if 'birth_location' in data:
            normalized['birth_location'] = data['birth_location']
        
        # Raise validation error if any field failed
        if errors:
            raise ValidationError(errors)
        
        return normalized
    
    @classmethod
    def _validate_time(cls, time_str: str) -> str:
        """Validate time string as HH:mm format"""
        if not isinstance(time_str, str):
            raise ValueError("must be a string")
        
        # Trim whitespace
        time_str = time_str.strip()
        
        # Check for banned literals
        if time_str.lower() in cls.BANNED_LITERALS:
            raise ValueError("invalid literal value")
        
        # Validate HH:mm format
        if not cls.TIME_REGEX.match(time_str):
            raise ValueError("must match HH:mm (24h)")
        
        return time_str
    
    @classmethod
    def _validate_date(cls, date_str: str) -> str:
        """Validate date string as YYYY-MM-DD format"""
        if not isinstance(date_str, str):
            raise ValueError("must be a string")
        
        # Trim whitespace
        date_str = date_str.strip()
        
        # Check for banned literals
        if date_str.lower() in cls.BANNED_LITERALS:
            raise ValueError("invalid literal value")
        
        # Validate YYYY-MM-DD format and real calendar date
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            # Ensure the parsed date matches the input (catches invalid dates like 1990-02-30)
            if parsed_date.strftime('%Y-%m-%d') != date_str:
                raise ValueError("must be YYYY-MM-DD")
        except ValueError:
            raise ValueError("must be YYYY-MM-DD")
        
        return date_str
    
    @classmethod
    def _validate_latitude(cls, lat: float) -> float:
        """Validate latitude is within valid range"""
        if not isinstance(lat, (int, float)):
            raise ValueError("must be a number")
        
        if not (-90 <= lat <= 90):
            raise ValueError("must be between -90 and 90")
        
        return float(lat)
    
    @classmethod
    def _validate_longitude(cls, lng: float) -> float:
        """Validate longitude is within valid range"""
        if not isinstance(lng, (int, float)):
            raise ValueError("must be a number")
        
        if not (-180 <= lng <= 180):
            raise ValueError("must be between -180 and 180")
        
        return float(lng)
    
    @classmethod
    def _validate_timezone(cls, tz_str: str) -> str:
        """Validate timezone is non-empty string"""
        if not isinstance(tz_str, str):
            raise ValueError("must be a string")
        
        # Trim whitespace
        tz_str = tz_str.strip()
        
        if not tz_str:
            raise ValueError("must be non-empty")
        
        return tz_str


def create_validation_error_response(validation_error: ValidationError) -> Tuple[Dict[str, Any], int]:
    """Create typed 400 error response from ValidationError"""
    return {
        'error': 'validation_error',
        'details': validation_error.details
    }, 400

