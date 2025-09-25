from services.db_service import DatabaseService
import logging

logger = logging.getLogger('JiraTimeTracker')


class AppSettings:
    """
    Provides a simple key-value store for application settings, backed by the database.
    """
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def get_setting(self, key: str, default: str = None) -> str | None:
        """Retrieves a setting value by its key."""
        conn = self.db_service.get_connection()
        if not conn:
            return default

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Value FROM AppSettings WHERE Key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
        except Exception as e:
            logger.exception("Error getting setting '%s': %s", key, e)
            return default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str):
        """Saves or updates a setting."""
        conn = self.db_service.get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            # Use INSERT OR REPLACE to handle both new and existing keys
            cursor.execute("INSERT OR REPLACE INTO AppSettings (Key, Value) VALUES (?, ?)", (key, value))
            conn.commit()
        except Exception as e:
            logger.exception("Error setting setting '%s': %s", key, e)
        finally:
            conn.close()

    def get_autosave_draft_interval(self) -> int:
        """Get the autosave draft interval in seconds (default: 10s)."""
        return int(self.get_setting('autosave_draft_interval', '10'))
    
    def set_autosave_draft_interval(self, interval_seconds: int):
        """Set the autosave draft interval in seconds."""
        self.set_setting('autosave_draft_interval', str(interval_seconds))
    
    def get_autosave_full_interval(self) -> int:
        """Get the autosave full save interval in seconds (default: 30s)."""
        return int(self.get_setting('autosave_full_interval', '30'))
    
    def set_autosave_full_interval(self, interval_seconds: int):
        """Set the autosave full save interval in seconds."""
        self.set_setting('autosave_full_interval', str(interval_seconds))
    
    def get_save_indicator_duration(self) -> int:
        """Get the save indicator display duration in seconds (default: 2s)."""
        return int(self.get_setting('save_indicator_duration', '2'))
    
    def set_save_indicator_duration(self, duration_seconds: int):
        """Set the save indicator display duration in seconds."""
        self.set_setting('save_indicator_duration', str(duration_seconds))
