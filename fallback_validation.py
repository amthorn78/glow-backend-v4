"""
Fallback validation for birth data without Pydantic dependency
"""
from datetime import date
import calendar

class SimpleBirthData:
    """Simple birth data container without Pydantic"""
    def __init__(self, **kwargs):
        self.year = kwargs.get('year')
        self.month = kwargs.get('month')
        self.day = kwargs.get('day')
        self.hour = kwargs.get('hour')
        self.minute = kwargs.get('minute')
        self.tz = kwargs.get('tz')
        self.lat = kwargs.get('lat')
        self.lng = kwargs.get('lng')
        self.location = kwargs.get('location')
        
    def to_iso_date(self) -> str:
        """Convert to ISO date string (YYYY-MM-DD)"""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def to_iso_time(self) -> str:
        """Convert to ISO time string (HH:MM:SS)"""
        return f"{self.hour:02d}:{self.minute:02d}:00"

def validate_birth_data_fallback(data: dict) -> SimpleBirthData:
    """
    Simple validation without Pydantic dependency
    """
    errors = []
    
    # Required fields
    required_fields = ['year', 'month', 'day', 'hour', 'minute', 'tz', 'lat', 'lng', 'location']
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        raise ValueError(f"Validation failed: {', '.join(errors)}")
    
    # Type and range validation
    try:
        year = int(data['year'])
        month = int(data['month'])
        day = int(data['day'])
        hour = int(data['hour'])
        minute = int(data['minute'])
        lat = float(data['lat'])
        lng = float(data['lng'])
        tz = str(data['tz'])
        location = str(data['location'])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid data types: {e}")
    
    # Range validation
    if not (1880 <= year <= 2100):
        errors.append(f"Year must be between 1880 and 2100, got {year}")
    if not (1 <= month <= 12):
        errors.append(f"Month must be between 1 and 12, got {month}")
    if not (1 <= day <= 31):
        errors.append(f"Day must be between 1 and 31, got {day}")
    if not (0 <= hour <= 23):
        errors.append(f"Hour must be between 0 and 23, got {hour}")
    if not (0 <= minute <= 59):
        errors.append(f"Minute must be between 0 and 59, got {minute}")
    if not (-90 <= lat <= 90):
        errors.append(f"Latitude must be between -90 and 90, got {lat}")
    if not (-180 <= lng <= 180):
        errors.append(f"Longitude must be between -180 and 180, got {lng}")
    if not tz.strip():
        errors.append("Timezone cannot be empty")
    if not location.strip():
        errors.append("Location cannot be empty")
    
    # Validate calendar date
    try:
        date(year, month, day)
    except ValueError:
        errors.append(f"Invalid calendar date: {year}-{month:02d}-{day:02d}")
    
    # Validate day for month/year (leap year handling)
    if 1 <= month <= 12:
        max_day = calendar.monthrange(year, month)[1]
        if day > max_day:
            month_names = [
                '', 'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            errors.append(f"Invalid day {day} for {month_names[month]} {year}")
    
    if errors:
        raise ValueError(f"Validation failed: {', '.join(errors)}")
    
    return SimpleBirthData(
        year=year, month=month, day=day, hour=hour, minute=minute,
        tz=tz, lat=lat, lng=lng, location=location
    )

