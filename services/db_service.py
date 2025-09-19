import sqlite3
import os
from PyQt6.QtCore import QStandardPaths
from datetime import datetime

class DatabaseService:
    """
    Manages the local SQLite database connection and schema.
    Fulfills requirement 4.4.
    """
    def __init__(self, db_name="jira_tracker.db"):
        data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.db_path = os.path.join(data_dir, db_name)
        self.conn = None
        self._credential_service = None
        
    @property
    def credential_service(self):
        """
        Lazy loading of the credential service to avoid circular imports.
        """
        if self._credential_service is None:
            from services.credential_service import CredentialService
            self._credential_service = CredentialService()
        return self._credential_service

    def get_connection(self):
        """Returns a new database connection."""
        try:
            # Using check_same_thread=False is suitable for PyQt apps where different
            # parts of the UI might indirectly access the DB from the main thread.
            # For more complex, multi-threaded scenarios, a connection pool would be better.
            return sqlite3.connect(self.db_path, check_same_thread=False)
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None

    def initialize_db(self):
        """
        Creates all necessary tables if they don't exist, as per requirement 6.5.
        """
        # ... (code for creating tables is unchanged)
        print(f"Initializing database at: {self.db_path}")
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cursor = conn.cursor()
            # AppSettings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AppSettings (
                    Key TEXT PRIMARY KEY NOT NULL,
                    Value TEXT
                );
            """)
            # FavoriteJiras Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FavoriteJiras (
                    JiraKey TEXT PRIMARY KEY NOT NULL
                );
            """)
            # Annotations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Annotations (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    JiraKey TEXT NOT NULL,
                    Title TEXT NOT NULL,
                    Content TEXT,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # SyncQueue Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SyncQueue (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    OperationType TEXT NOT NULL,
                    Payload TEXT NOT NULL,
                    Status TEXT NOT NULL DEFAULT 'Pending',
                    Attempts INTEGER NOT NULL DEFAULT 0,
                    ErrorMessage TEXT,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # LocalTimeLog Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS LocalTimeLog (
                    JiraKey TEXT PRIMARY KEY NOT NULL,
                    SecondsTracked INTEGER NOT NULL DEFAULT 0,
                    StartTime DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Add StartTime column if not exists
            try:
                cursor.execute("SELECT StartTime FROM LocalTimeLog LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding StartTime column to LocalTimeLog table")
                cursor.execute("ALTER TABLE LocalTimeLog ADD COLUMN StartTime DATETIME DEFAULT CURRENT_TIMESTAMP")
                
            # LocalWorklogHistory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS LocalWorklogHistory (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    JiraKey TEXT NOT NULL,
                    StartTime DATETIME NOT NULL,
                    DurationSeconds INTEGER NOT NULL,
                    Comment TEXT,
                    SyncStatus TEXT NOT NULL DEFAULT 'Pending',
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Add Task column to LocalWorklogHistory if not exists
            try:
                cursor.execute("SELECT Task FROM LocalWorklogHistory LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding Task column to LocalWorklogHistory table")
                cursor.execute("ALTER TABLE LocalWorklogHistory ADD COLUMN Task TEXT DEFAULT 'compito'")
            
            # ViewHistory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ViewHistory (
                    JiraKey TEXT PRIMARY KEY NOT NULL,
                    LastViewedAt DATETIME NOT NULL
                );
            """)
            
            # StatusColorMappings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StatusColorMappings (
                    StatusName TEXT PRIMARY KEY NOT NULL,
                    ColorHex TEXT NOT NULL
                );
            """)
            
            # Insert default status color mapping if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO StatusColorMappings (StatusName, ColorHex) VALUES ('Collaudo Negativo', '#E74C3C')
            """)
            
            # JQLHistory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS JQLHistory (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Query TEXT NOT NULL,
                    LastUsedAt DATETIME NOT NULL
                );
            """)
            
            # FavoriteJQLs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FavoriteJQLs (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    Query TEXT NOT NULL
                );
            """)
            
            # NotificationSubscriptions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS NotificationSubscriptions (
                    JiraKey TEXT PRIMARY KEY NOT NULL,
                    LastCheckedTimestamp DATETIME NOT NULL,
                    LastKnownCommentId TEXT,
                    last_comment_date TEXT,
                    is_read INTEGER DEFAULT 1
                );
            """)
            conn.commit()
            print("Database initialized successfully.")
        except sqlite3.Error as e:
            print(f"Error initializing database schema: {e}")
        finally:
            conn.close()

    # --- Favorite Management ---

    def add_favorite(self, jira_key: str):
        """Adds a Jira issue key to the favorites table."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO FavoriteJiras (JiraKey) VALUES (?)", (jira_key,))
            conn.commit()
        finally:
            conn.close()

    def remove_favorite(self, jira_key: str):
        """Removes a Jira issue key from the favorites table."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM FavoriteJiras WHERE JiraKey = ?", (jira_key,))
            conn.commit()
        finally:
            conn.close()

    def get_all_favorites(self) -> list[str]:
        """Returns a list of all favorite Jira issue keys."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT JiraKey FROM FavoriteJiras")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
            
    def is_favorite(self, jira_key: str) -> bool:
        """Checks if a Jira issue key is in favorites."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM FavoriteJiras WHERE JiraKey = ?", (jira_key,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    # --- Annotation Management ---

    def save_annotation(self, jira_key: str, title: str, content: str):
        """Saves or updates an annotation based on Jira key and title."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Id FROM Annotations WHERE JiraKey = ? AND Title = ?", (jira_key, title))
            result = cursor.fetchone()
            if result:
                cursor.execute(
                    "UPDATE Annotations SET Content = ?, UpdatedAt = CURRENT_TIMESTAMP WHERE Id = ?",
                    (content, result[0])
                )
            else:
                cursor.execute(
                    "INSERT INTO Annotations (JiraKey, Title, Content) VALUES (?, ?, ?)",
                    (jira_key, title, content)
                )
            conn.commit()
        finally:
            conn.close()

    def get_annotations(self, jira_key: str) -> list:
        """Retrieves all annotations for a given Jira key."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT Title, Content FROM Annotations WHERE JiraKey = ? ORDER BY Title', (jira_key,))
            return cursor.fetchall()
        finally:
            conn.close()

    def delete_annotation(self, jira_key: str, title: str):
        """Deletes a specific annotation."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Annotations WHERE JiraKey = ? AND Title = ?", (jira_key, title))
            conn.commit()
        finally:
            conn.close()

    def rename_annotation(self, jira_key: str, old_title: str, new_title: str):
        """Renames an annotation title."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Annotations SET Title = ? WHERE JiraKey = ? AND Title = ?",
                (new_title, jira_key, old_title)
            )
            conn.commit()
        finally:
            conn.close()

    # --- Local Time Log Methods ---
    def get_local_time(self, jira_key: str) -> int:
        """Gets the locally tracked seconds for a specific Jira issue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT SecondsTracked FROM LocalTimeLog WHERE JiraKey = ?', (jira_key,))
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()

    def get_start_time(self, jira_key: str):
        """Gets the start time for a specific Jira issue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT StartTime FROM LocalTimeLog WHERE JiraKey = ?', (jira_key,))
            result = cursor.fetchone()
            return datetime.fromisoformat(result[0]) if result and result[0] else None
        finally:
            conn.close()

    def get_all_local_times(self) -> dict[str, int]:
        """Gets all locally tracked times as a dictionary."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT JiraKey, SecondsTracked FROM LocalTimeLog')
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

    def update_local_time(self, jira_key: str, seconds: int, start_time):
        """Updates the tracked time for a Jira issue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO LocalTimeLog (JiraKey, SecondsTracked, StartTime) VALUES (?, ?, ?)',
                (jira_key, seconds, start_time)
            )
            conn.commit()
        finally:
            conn.close()

    def reset_local_time(self, jira_key: str):
        """Resets the tracked time for a Jira issue to 0."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE LocalTimeLog SET SecondsTracked = 0 WHERE JiraKey = ?', (jira_key,))
            conn.commit()
        finally:
            conn.close()

    # --- Sync Queue Methods ---
    def add_to_sync_queue(self, operation_type: str, payload: str):
        """Adds a new operation to the synchronization queue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO SyncQueue (OperationType, Payload) VALUES (?, ?)',
                (operation_type, payload)
            )
            conn.commit()
        finally:
            conn.close()

    # --- Local Worklog History Methods ---
    def add_local_worklog(self, jira_key: str, start_time: datetime, duration_seconds: int, comment: str = None, task: str = None):
        """Adds a new worklog entry to the local history."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO LocalWorklogHistory (JiraKey, StartTime, DurationSeconds, Comment, Task) VALUES (?, ?, ?, ?, ?)',
                (jira_key, start_time.isoformat(), duration_seconds, comment, task or 'compito')
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_local_worklogs(self, jira_key: str) -> list:
        """Gets all local worklog entries for a specific Jira issue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT Id, StartTime, DurationSeconds, Comment, SyncStatus, Task FROM LocalWorklogHistory WHERE JiraKey = ? ORDER BY StartTime DESC',
                (jira_key,)
            )
            return cursor.fetchall()
        finally:
            conn.close()
    
    def update_worklog_sync_status(self, worklog_id: int, status: str, error_message: str = None):
        """Updates the sync status of a worklog entry."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if error_message:
                cursor.execute(
                    'UPDATE LocalWorklogHistory SET SyncStatus = ?, ErrorMessage = ? WHERE Id = ?',
                    (status, error_message, worklog_id)
                )
            else:
                cursor.execute(
                    'UPDATE LocalWorklogHistory SET SyncStatus = ? WHERE Id = ?',
                    (status, worklog_id)
                )
            conn.commit()
        finally:
            conn.close()
    
    def update_worklog_comment(self, worklog_id: int, comment: str):
        """Updates the comment of a worklog entry."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE LocalWorklogHistory SET Comment = ? WHERE Id = ?',
                (comment, worklog_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_worklog_duration(self, worklog_id: int, duration_seconds: int):
        """Updates the duration of a worklog entry."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE LocalWorklogHistory SET DurationSeconds = ? WHERE Id = ?',
                (duration_seconds, worklog_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    # --- View History Methods ---
    def add_view_history(self, jira_key: str):
        """Records that a Jira issue has been viewed."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO ViewHistory (JiraKey, LastViewedAt) VALUES (?, CURRENT_TIMESTAMP)',
                (jira_key,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_view_history(self, limit: int = 100) -> list:
        """Gets the view history ordered by most recent first."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT JiraKey, LastViewedAt FROM ViewHistory ORDER BY LastViewedAt DESC LIMIT ?',
                (limit,)
            )
            return cursor.fetchall()
        finally:
            conn.close()
    
    # --- Status Color Mapping Methods ---
    def get_status_color(self, status_name: str) -> str:
        """Gets the color for a specific status."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT ColorHex FROM StatusColorMappings WHERE StatusName = ?',
                (status_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def set_status_color(self, status_name: str, color_hex: str):
        """Sets the color for a specific status."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO StatusColorMappings (StatusName, ColorHex) VALUES (?, ?)',
                (status_name, color_hex)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_all_status_colors(self) -> list:
        """Gets all status color mappings."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT StatusName, ColorHex FROM StatusColorMappings')
            return cursor.fetchall()
        finally:
            conn.close()
    
    def delete_status_color(self, status_name: str):
        """Removes a status color mapping."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM StatusColorMappings WHERE StatusName = ?', (status_name,))
            conn.commit()
        finally:
            conn.close()
    
    # --- JQL History Methods ---
    def add_jql_history(self, query: str):
        """Adds a JQL query to the history."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Check if query already exists
            cursor.execute('SELECT Id FROM JQLHistory WHERE Query = ?', (query,))
            result = cursor.fetchone()
            
            if result:
                # Update existing entry
                cursor.execute(
                    'UPDATE JQLHistory SET LastUsedAt = CURRENT_TIMESTAMP WHERE Id = ?',
                    (result[0],)
                )
            else:
                # Add new entry
                cursor.execute(
                    'INSERT INTO JQLHistory (Query, LastUsedAt) VALUES (?, CURRENT_TIMESTAMP)',
                    (query,)
                )
            
            # Keep only the last 20 entries
            cursor.execute('''
                DELETE FROM JQLHistory 
                WHERE Id NOT IN (
                    SELECT Id FROM JQLHistory 
                    ORDER BY LastUsedAt DESC 
                    LIMIT 20
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def get_jql_history(self) -> list:
        """Gets the JQL history."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT Query, LastUsedAt FROM JQLHistory ORDER BY LastUsedAt DESC')
            return cursor.fetchall()
        finally:
            conn.close()
    
    # --- Favorite JQL Methods ---
    def add_favorite_jql(self, name: str, query: str) -> int:
        """Adds a JQL query to favorites."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO FavoriteJQLs (Name, Query) VALUES (?, ?)',
                (name, query)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_favorite_jqls(self) -> list:
        """Gets all favorite JQL queries."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT Id, Name, Query FROM FavoriteJQLs ORDER BY Name')
            return cursor.fetchall()
        finally:
            conn.close()
    
    def delete_favorite_jql(self, jql_id: int):
        """Removes a favorite JQL query."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM FavoriteJQLs WHERE Id = ?', (jql_id,))
            conn.commit()
        finally:
            conn.close()
            
    # --- Notification Subscription Methods ---
    def add_notification_subscription(self, jira_key: str):
        """Adds a subscription to receive notifications for new comments."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # First, make sure the NotificationSubscriptions table is updated with the needed fields
            try:
                cursor.execute('''
                    ALTER TABLE NotificationSubscriptions 
                    ADD COLUMN last_comment_date TEXT DEFAULT NULL
                ''')
                cursor.execute('''
                    ALTER TABLE NotificationSubscriptions 
                    ADD COLUMN is_read INTEGER DEFAULT 1
                ''')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists, ignore
                pass

            cursor.execute(
                'INSERT OR REPLACE INTO NotificationSubscriptions (JiraKey, LastCheckedTimestamp, last_comment_date, is_read) VALUES (?, CURRENT_TIMESTAMP, NULL, 1)',
                (jira_key,)
            )
            conn.commit()
        finally:
            conn.close()
            
    def delete_notification_subscription(self, jira_key: str):
        """Removes a notification subscription."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM NotificationSubscriptions WHERE JiraKey = ?', (jira_key,))
            conn.commit()
        finally:
            conn.close()
            
    def get_all_notification_subscriptions(self) -> list:
        """Gets all notification subscriptions."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # First, make sure the table has the required columns
            try:
                cursor.execute('SELECT JiraKey, last_comment_date, is_read FROM NotificationSubscriptions')
            except sqlite3.OperationalError:
                # Missing columns, add them
                try:
                    cursor.execute('ALTER TABLE NotificationSubscriptions ADD COLUMN last_comment_date TEXT DEFAULT NULL')
                    cursor.execute('ALTER TABLE NotificationSubscriptions ADD COLUMN is_read INTEGER DEFAULT 1')
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
                
            cursor.execute('SELECT JiraKey, last_comment_date, is_read FROM NotificationSubscriptions')
            results = cursor.fetchall()
            
            # Convert to list of dictionaries for easier access
            subscriptions = []
            for row in results:
                subscriptions.append({
                    'issue_key': row[0],
                    'last_comment_date': row[1],
                    'is_read': bool(row[2])
                })
            return subscriptions
        finally:
            conn.close()
    
    def get_notification_subscription(self, jira_key: str) -> dict:
        """Gets a single notification subscription."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT JiraKey, last_comment_date, is_read FROM NotificationSubscriptions WHERE JiraKey = ?', (jira_key,))
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'issue_key': row[0],
                'last_comment_date': row[1],
                'is_read': bool(row[2])
            }
        finally:
            conn.close()
            
    def update_notification_subscription(self, jira_key: str, data: dict):
        """Updates a notification subscription with new data."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Build the update query based on provided data
            updates = []
            params = []
            
            if 'last_comment_date' in data:
                updates.append('last_comment_date = ?')
                params.append(data['last_comment_date'])
                
            if 'is_read' in data:
                updates.append('is_read = ?')
                params.append(1 if data['is_read'] else 0)
                
            if not updates:
                return
                
            # Add jira_key to params
            params.append(jira_key)
            
            # Execute update
            query = f"UPDATE NotificationSubscriptions SET {', '.join(updates)} WHERE JiraKey = ?"
            cursor.execute(query, params)
            conn.commit()
        finally:
            conn.close()
    
    def get_unread_notifications_count(self) -> int:
        """Gets the count of unread notifications."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM NotificationSubscriptions WHERE is_read = 0')
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
            
    def mark_all_notifications_read(self):
        """Marks all notifications as read."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE NotificationSubscriptions SET is_read = 1')
            conn.commit()
        finally:
            conn.close()
    
    def is_subscribed(self, jira_key: str) -> bool:
        """Checks if the user is subscribed to notifications for the given Jira issue."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM NotificationSubscriptions WHERE JiraKey = ?', (jira_key,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    # --- Sync Queue Additional Methods ---
    def get_pending_sync_operations(self) -> list:
        """Gets all pending sync operations."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT Id, OperationType, Payload, Attempts FROM SyncQueue WHERE Status = "Pending" ORDER BY CreatedAt'
            )
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_failed_sync_operations(self) -> list:
        """Gets all failed sync operations."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT Id, OperationType, Payload, Attempts, ErrorMessage FROM SyncQueue WHERE Status = "Failed" ORDER BY CreatedAt'
            )
            return cursor.fetchall()
        finally:
            conn.close()
    
    def update_sync_operation_status(self, operation_id: int, status: str, error_message: str = None):
        """Updates the status of a sync operation."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if status == "Failed" and error_message:
                cursor.execute(
                    'UPDATE SyncQueue SET Status = ?, ErrorMessage = ?, Attempts = Attempts + 1 WHERE Id = ?',
                    (status, error_message, operation_id)
                )
            else:
                cursor.execute(
                    'UPDATE SyncQueue SET Status = ? WHERE Id = ?',
                    (status, operation_id)
                )
            conn.commit()
        finally:
            conn.close()
    
    def close(self):
        if self.conn:
            self.conn.close()
