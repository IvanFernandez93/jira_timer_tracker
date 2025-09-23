"""
Service for handling timezone conversions throughout the application.
"""

import datetime
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('JiraTimeTracker')

class TimezoneService:
    """Handles timezone conversions based on user preferences."""

    def __init__(self, app_settings=None):
        """
        Initialize the timezone service with application settings.
        
        Args:
            app_settings: The AppSettings service to retrieve timezone preferences.
        """
        self.app_settings = app_settings
        self._cached_timezone = None
        self._last_update = None

    def get_user_timezone(self):
        """
        Get the user's preferred timezone from settings.
        
        Returns:
            A timezone object representing the user's preference or the local timezone if not specified.
        """
        # Refresh cache if needed (once per minute)
        current_time = datetime.now()
        if not self._cached_timezone or not self._last_update or (current_time - self._last_update).seconds > 60:
            self._refresh_timezone_cache()
            
        return self._cached_timezone
    
    def _refresh_timezone_cache(self):
        """Refresh the cached timezone object from settings."""
        try:
            # Default to local timezone
            self._cached_timezone = datetime.now().astimezone().tzinfo
            
            if not self.app_settings:
                logger.debug("No app_settings available, using local timezone")
                return
                
            # Get timezone setting
            tz_name = self.app_settings.get_setting("timezone", "local")
            
            if tz_name == "local" or not tz_name:
                # Already set to local timezone
                logger.debug("Using local timezone as configured")
                pass
            elif tz_name == "UTC":
                # UTC timezone
                self._cached_timezone = timezone.utc
                logger.debug("Using UTC timezone as configured")
            else:
                # Named timezone
                try:
                    import pytz
                    self._cached_timezone = pytz.timezone(tz_name)
                    logger.debug(f"Using timezone {tz_name} as configured")
                except ImportError:
                    logger.warning("pytz module not available, falling back to local timezone")
                except Exception as e:
                    logger.error(f"Error setting timezone to {tz_name}: {e}")
            
            self._last_update = datetime.now()
        except Exception as e:
            logger.exception(f"Error in _refresh_timezone_cache: {e}")
            # Default to local timezone on error
            self._cached_timezone = datetime.now().astimezone().tzinfo
    
    def format_datetime(self, dt, format_str="%d/%m/%Y %H:%M:%S"):
        """
        Format a datetime object according to user preferences.
        
        Args:
            dt: The datetime object to format
            format_str: The format string to use
            
        Returns:
            A formatted string representation of the datetime
        """
        try:
            if not dt:
                return ""
                
            # Make sure dt is timezone-aware
            if isinstance(dt, str):
                dt = self.parse_datetime(dt)
                
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
                
            # Convert to the user's preferred timezone
            user_tz = self.get_user_timezone()
            if user_tz:
                dt = dt.astimezone(user_tz)
                
            return dt.strftime(format_str)
        except Exception as e:
            logger.error(f"Error formatting datetime {dt}: {e}")
            return str(dt)
    
    def parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse a datetime string into a timezone-aware datetime object.
        
        Args:
            datetime_str: The datetime string to parse
            
        Returns:
            A timezone-aware datetime object or None if parsing fails
        """
        try:
            if not datetime_str:
                return None
                
            # Try ISO format first
            try:
                if 'T' in datetime_str or 'Z' in datetime_str:
                    # Handle ISO format with Z
                    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    return dt
            except ValueError:
                pass
                
            # Try various formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(datetime_str, fmt)
                    # Assume UTC if no timezone info
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
                    
            # If all attempts fail, try a generic approach with dateutil
            try:
                from dateutil import parser
                dt = parser.parse(datetime_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ImportError, ValueError):
                pass
                
            logger.warning(f"Could not parse datetime string: {datetime_str}")
            return None
        except Exception as e:
            logger.error(f"Error parsing datetime {datetime_str}: {e}")
            return None
    
    def now(self):
        """
        Get the current datetime in the user's preferred timezone.
        
        Returns:
            A timezone-aware datetime object representing the current time
        """
        try:
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)
            
            # Convert to user's preferred timezone
            user_tz = self.get_user_timezone()
            if user_tz:
                return now_utc.astimezone(user_tz)
            else:
                return now_utc
        except Exception as e:
            logger.error(f"Error getting current time: {e}")
            return datetime.now()