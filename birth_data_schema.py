from pydantic import BaseModel, Field, ValidationError, model_validator, ConfigDict
from typing import Optional
from datetime import datetime, date
import calendar

class BirthDataSchema(BaseModel):
    # Pydantic v2 configuration
    model_config = ConfigDict(
        populate_by_name=True, 
        extra='ignore',
        json_schema_extra={
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
    )
    
    year: int = Field(..., ge=1880, le=2100, description="Birth year")
    month: int = Field(..., ge=1, le=12, description="Birth month (1-12)")
    day: int = Field(..., ge=1, le=31, description="Birth day")
    hour: int = Field(..., ge=0, le=23, description="Birth hour (0-23)")
    minute: int = Field(..., ge=0, le=59, description="Birth minute (0-59)")
    tz: str = Field(..., min_length=1, description="IANA timezone string")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location: str = Field(..., min_length=1, description="Birth location display name")
    unknown_time: Optional[bool] = Field(False, alias="unknownTime", description="Whether birth time is unknown")

    @model_validator(mode="after")
    def validate_cross_fields(self):
        """Validate cross-field constraints and timezone"""
        # Enforce "time is required" (no unknown time allowed)
        if self.unknown_time:
            raise ValueError("unknownTime is not allowed; birth time is required.")
        
        # Validate real calendar date (handles leap years)
        try:
            date(self.year, self.month, self.day)
        except ValueError:
            raise ValueError(f"Invalid calendar date: {self.year}-{self.month:02d}-{self.day:02d}")
        
        # Validate the timezone exists
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+
            ZoneInfo(self.tz)
        except Exception as e:
            raise ValueError(f"Unknown IANA timezone: {self.tz}. Error: {str(e)}")
        
        return self

    def to_iso_date(self) -> str:
        """Convert to ISO date string (YYYY-MM-DD)"""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def to_iso_time(self) -> str:
        """Convert to ISO time string (HH:MM:SS)"""
        return f"{self.hour:02d}:{self.minute:02d}:00"

def validate_birth_data(data: dict) -> BirthDataSchema:
    """
    Validate birth data and return a validated schema object.
    
    Args:
        data: Raw birth data dictionary from frontend
        
    Returns:
        BirthDataSchema: Validated birth data object
        
    Raises:
        ValidationError: If validation fails with detailed field errors
    """
    try:
        return BirthDataSchema.model_validate(data)
    except ValidationError as e:
        # Re-raise ValidationError to be handled by Flask endpoint
        raise e
    except Exception as e:
        # Convert other errors to ValidationError format
        raise ValidationError.from_exception_data("BirthDataSchema", [
            {
                "type": "value_error",
                "loc": ("__root__",),
                "msg": str(e),
                "input": data
            }
        ])

