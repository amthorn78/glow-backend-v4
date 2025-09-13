from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
import calendar

class BirthDataSchema(BaseModel):
    year: int = Field(..., ge=1880, le=2100, description="Birth year")
    month: int = Field(..., ge=1, le=12, description="Birth month (1-12)")
    day: int = Field(..., ge=1, le=31, description="Birth day")
    hour: int = Field(..., ge=0, le=23, description="Birth hour (0-23)")
    minute: int = Field(..., ge=0, le=59, description="Birth minute (0-59)")
    tz: str = Field(..., min_length=1, description="IANA timezone string")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location: str = Field(..., min_length=1, description="Birth location display name")

    @validator('day')
    def validate_day_for_month_year(cls, day, values):
        """Validate that the day is valid for the given month and year"""
        if 'year' in values and 'month' in values:
            year = values['year']
            month = values['month']
            
            # Get the maximum day for this month/year (handles leap years)
            max_day = calendar.monthrange(year, month)[1]
            
            if day > max_day:
                month_names = [
                    '', 'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ]
                raise ValueError(f"Invalid day {day} for {month_names[month]} {year}")
        
        return day

    def to_iso_date(self) -> str:
        """Convert to ISO date string (YYYY-MM-DD)"""
        return f"{self.year}-{self.month:02d}-{self.day:02d}"

    def to_iso_time(self) -> str:
        """Convert to ISO time string (HH:MM:SS)"""
        return f"{self.hour:02d}:{self.minute:02d}:00"

    class Config:
        # Allow extra fields to be ignored (for forward compatibility)
        extra = "ignore"
        
        # Example for documentation
        schema_extra = {
            "example": {
                "year": 1984,
                "month": 11,
                "day": 15,
                "hour": 9,
                "minute": 30,
                "tz": "America/New_York",
                "lat": 40.7128,
                "lng": -74.0060,
                "location": "New York, NY, USA"
            }
        }

def validate_birth_data(data: dict) -> BirthDataSchema:
    """
    Validate birth data and return a validated schema object.
    
    Args:
        data: Raw birth data dictionary from frontend
        
    Returns:
        BirthDataSchema: Validated birth data object
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return BirthDataSchema(**data)
    except Exception as e:
        # Convert Pydantic validation errors to a more user-friendly format
        if hasattr(e, 'errors'):
            error_messages = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'unknown'
                message = error['msg']
                error_messages[field] = message
            
            # Create a custom exception with field-specific errors
            raise ValueError(f"Validation failed: {error_messages}")
        else:
            raise ValueError(f"Validation failed: {str(e)}")

