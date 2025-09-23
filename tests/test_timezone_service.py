import pytest
from services.timezone_service import TimezoneService
from services.app_settings import AppSettings
from datetime import datetime, timezone


class MockAppSettings:
    """Mock AppSettings class for testing."""
    
    def __init__(self):
        self.settings = {}
        
    def get_setting(self, key, default=None):
        """Get a setting or return default if not found."""
        return self.settings.get(key, default)
        
    def set_setting(self, key, value):
        """Set a setting value."""
        self.settings[key] = value


def test_timezone_service_defaults_to_local():
    """Test that timezone service defaults to local timezone without app_settings."""
    # Create service with no app_settings
    tz_service = TimezoneService()
    
    # Default timezone should be local
    tz = tz_service.get_user_timezone()
    assert tz is not None
    
    # Local now and service now should be similar
    local_now = datetime.now()
    service_now = tz_service.now()
    
    # They should be within a second of each other
    diff = abs((local_now - service_now.replace(tzinfo=None)).total_seconds())
    assert diff < 1.0


def test_timezone_service_honors_settings():
    """Test that timezone service uses timezone from settings."""
    app_settings = MockAppSettings()
    
    # Set timezone to UTC
    app_settings.set_setting("timezone", "UTC")
    
    # Create service with app_settings
    tz_service = TimezoneService(app_settings)
    
    # Get a time in UTC
    utc_time = tz_service.now()
    assert utc_time.tzinfo == timezone.utc
    
    # Format it
    formatted = tz_service.format_datetime(utc_time, "%Z")
    assert "UTC" in formatted


def test_timezone_service_parses_dates():
    """Test that timezone service correctly parses dates."""
    tz_service = TimezoneService()
    
    # Test ISO format
    dt = tz_service.parse_datetime("2023-01-01T12:34:56Z")
    assert dt.year == 2023
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    assert dt.tzinfo is not None
    
    # Test different formats
    dt = tz_service.parse_datetime("2023-01-01 12:34:56")
    assert dt.year == 2023
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    
    dt = tz_service.parse_datetime("01/01/2023 12:34:56")
    assert dt.day == 1
    assert dt.month == 1
    assert dt.year == 2023