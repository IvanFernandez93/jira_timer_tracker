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
            # PriorityUpdates Table for local priority changes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PriorityUpdates (
                    JiraKey TEXT PRIMARY KEY NOT NULL,
                    PriorityId TEXT NOT NULL,
                    PriorityName TEXT,
                    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    SyncStatus TEXT DEFAULT 'pending',
                    SyncedAt DATETIME
                );
            """)
            
            # Add SyncedAt column if it doesn't exist
            try:
                cursor.execute("SELECT SyncedAt FROM PriorityUpdates LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding SyncedAt column to PriorityUpdates table")
                cursor.execute("ALTER TABLE PriorityUpdates ADD COLUMN SyncedAt DATETIME")
            
            # PriorityConfig Table for priority customizations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PriorityConfig (
                    PriorityId TEXT PRIMARY KEY,
                    ColorCode TEXT NOT NULL,
                    CustomLabel TEXT
                );
            """)
            # Annotations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Annotations (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    JiraKey TEXT,
                    Title TEXT NOT NULL,
                    Content TEXT,
                    Tags TEXT,
                    IsDeleted INTEGER NOT NULL DEFAULT 0,
                    DeletedAt DATETIME,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Annotations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Annotations (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    JiraKey TEXT,
                    Title TEXT NOT NULL,
                    Content TEXT,
                    Tags TEXT,
                    IsDeleted INTEGER NOT NULL DEFAULT 0,
                    DeletedAt DATETIME,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Add new columns to Annotations table if they don't exist
            try:
                cursor.execute("SELECT Tags FROM Annotations LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding Tags column to Annotations table")
                cursor.execute("ALTER TABLE Annotations ADD COLUMN Tags TEXT")
            
            try:
                cursor.execute("SELECT IsDeleted FROM Annotations LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding IsDeleted column to Annotations table")
                cursor.execute("ALTER TABLE Annotations ADD COLUMN IsDeleted INTEGER NOT NULL DEFAULT 0")
                
            try:
                cursor.execute("SELECT DeletedAt FROM Annotations LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding DeletedAt column to Annotations table")
                cursor.execute("ALTER TABLE Annotations ADD COLUMN DeletedAt DATETIME")
            
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
            
            # FileAttachments Table - Tracks downloaded files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FileAttachments (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    JiraKey TEXT NOT NULL,
                    AttachmentId TEXT NOT NULL,
                    FileName TEXT NOT NULL,
                    FilePath TEXT NOT NULL,
                    FileHash TEXT NOT NULL,
                    FileSize INTEGER NOT NULL,
                    MimeType TEXT,
                    DownloadedAt DATETIME NOT NULL,
                    LastCheckedAt DATETIME NOT NULL,
                    UNIQUE(JiraKey, AttachmentId)
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

    def create_note(self, jira_key: str = None, title: str = "", content: str = "", tags: str = "") -> int:
        """Creates a new note and returns its ID."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO Annotations (JiraKey, Title, Content, Tags, IsDeleted) VALUES (?, ?, ?, ?, 0)',
                (jira_key, title, content, tags)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_note_by_id(self, note_id: int) -> dict:
        """Gets a note by its ID."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE Id = ?',
                (note_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'jira_key': row[1],
                'title': row[2],
                'content': row[3],
                'tags': row[4] or '',
                'is_deleted': bool(row[5]),
                'deleted_at': row[6],
                'created_at': row[7],
                'updated_at': row[8]
            }
        finally:
            conn.close()

    def update_note(self, note_id: int, jira_key: str = None, title: str = None, content: str = None, tags: str = None):
        """Updates a note with the provided fields."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Build the update query based on provided data
            updates = []
            params = []
            
            if jira_key is not None:
                updates.append('JiraKey = ?')
                params.append(jira_key)
                
            if title is not None:
                updates.append('Title = ?')
                params.append(title)
                
            if content is not None:
                updates.append('Content = ?')
                params.append(content)
                
            if tags is not None:
                updates.append('Tags = ?')
                params.append(tags)
            
            if not updates:
                return
            
            # Always update UpdatedAt with explicit timestamp in UTC format
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            updates.append('UpdatedAt = ?')
            params.append(current_time)
            
            # Add note_id to params
            params.append(note_id)
            
            # Execute update
            query = f"UPDATE Annotations SET {', '.join(updates)} WHERE Id = ?"
            cursor.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def delete_note_soft(self, note_id: int):
        """Soft deletes a note (marks as deleted)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            cursor.execute(
                'UPDATE Annotations SET IsDeleted = 1, DeletedAt = ? WHERE Id = ?',
                (current_time, note_id)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_note_hard(self, note_id: int):
        """Hard deletes a note (permanently removes it)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM Annotations WHERE Id = ?', (note_id,))
            conn.commit()
        finally:
            conn.close()

    def restore_note(self, note_id: int):
        """Restores a soft-deleted note."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE Annotations SET IsDeleted = 0, DeletedAt = NULL WHERE Id = ?',
                (note_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_notes(self, include_deleted: bool = False) -> list:
        """Gets all notes, optionally including deleted ones."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if include_deleted:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations ORDER BY UpdatedAt DESC'
                )
            else:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE IsDeleted = 0 ORDER BY UpdatedAt DESC'
                )
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'jira_key': row[1],
                    'title': row[2],
                    'content': row[3],
                    'tags': row[4] or '',
                    'is_deleted': bool(row[5]),
                    'deleted_at': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            return notes
        finally:
            conn.close()

    def get_notes_by_jira_key(self, jira_key: str, include_deleted: bool = False) -> list:
        """Gets all notes for a specific Jira key."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if include_deleted:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE JiraKey = ? ORDER BY UpdatedAt DESC',
                    (jira_key,)
                )
            else:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE JiraKey = ? AND IsDeleted = 0 ORDER BY UpdatedAt DESC',
                    (jira_key,)
                )
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'jira_key': row[1],
                    'title': row[2],
                    'content': row[3],
                    'tags': row[4] or '',
                    'is_deleted': bool(row[5]),
                    'deleted_at': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            return notes
        finally:
            conn.close()

    def get_notes_by_tags(self, tags: list, include_deleted: bool = False) -> list:
        """Gets notes that have any of the specified tags."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Build query with tag filtering
            tag_conditions = []
            params = []
            
            for tag in tags:
                tag_conditions.append('Tags LIKE ?')
                params.append(f'%{tag}%')
            
            tag_filter = ' OR '.join(tag_conditions)
            
            if include_deleted:
                query = f'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE ({tag_filter}) ORDER BY UpdatedAt DESC'
            else:
                query = f'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE ({tag_filter}) AND IsDeleted = 0 ORDER BY UpdatedAt DESC'
            
            cursor.execute(query, params)
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'jira_key': row[1],
                    'title': row[2],
                    'content': row[3],
                    'tags': row[4] or '',
                    'is_deleted': bool(row[5]),
                    'deleted_at': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            return notes
        finally:
            conn.close()

    def search_notes(self, search_term: str, include_deleted: bool = False) -> list:
        """Searches notes by title, content, or Jira key."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            search_pattern = f'%{search_term}%'
            
            if include_deleted:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE (Title LIKE ? OR Content LIKE ? OR JiraKey LIKE ?) ORDER BY UpdatedAt DESC',
                    (search_pattern, search_pattern, search_pattern)
                )
            else:
                cursor.execute(
                    'SELECT Id, JiraKey, Title, Content, Tags, IsDeleted, DeletedAt, CreatedAt, UpdatedAt FROM Annotations WHERE (Title LIKE ? OR Content LIKE ? OR JiraKey LIKE ?) AND IsDeleted = 0 ORDER BY UpdatedAt DESC',
                    (search_pattern, search_pattern, search_pattern)
                )
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'jira_key': row[1],
                    'title': row[2],
                    'content': row[3],
                    'tags': row[4] or '',
                    'is_deleted': bool(row[5]),
                    'deleted_at': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            return notes
        finally:
            conn.close()

    def get_all_tags(self) -> list:
        """Gets all unique tags from all notes."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT Tags FROM Annotations WHERE Tags IS NOT NULL AND Tags != "" AND IsDeleted = 0')
            
            all_tags = set()
            for row in cursor.fetchall():
                if row[0]:
                    # Split tags by comma and clean them
                    tags = [tag.strip() for tag in row[0].split(',') if tag.strip()]
                    all_tags.update(tags)
            
            return sorted(list(all_tags))
        finally:
            conn.close()

    # --- Legacy Annotation Methods (for backward compatibility) ---

    def save_annotation(self, jira_key: str, title: str, content: str):
        """Saves or updates an annotation based on Jira key and title (legacy method)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Id FROM Annotations WHERE JiraKey = ? AND Title = ? AND IsDeleted = 0", (jira_key, title))
            result = cursor.fetchone()
            
            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            if result:
                cursor.execute(
                    "UPDATE Annotations SET Content = ?, UpdatedAt = ? WHERE Id = ?",
                    (content, current_time, result[0])
                )
            else:
                cursor.execute(
                    "INSERT INTO Annotations (JiraKey, Title, Content, IsDeleted) VALUES (?, ?, ?, 0)",
                    (jira_key, title, content)
                )
            conn.commit()
        finally:
            conn.close()

    def get_annotations(self, jira_key: str) -> list:
        """Retrieves all annotations for a given Jira key (legacy method)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT Title, Content FROM Annotations WHERE JiraKey = ? AND IsDeleted = 0 ORDER BY Title', (jira_key,))
            return cursor.fetchall()
        finally:
            conn.close()

    def delete_annotation(self, jira_key: str, title: str):
        """Deletes a specific annotation (legacy method - now soft delete)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Id FROM Annotations WHERE JiraKey = ? AND Title = ? AND IsDeleted = 0", (jira_key, title))
            result = cursor.fetchone()
            if result:
                self.delete_note_soft(result[0])
        finally:
            conn.close()

    def rename_annotation(self, jira_key: str, old_title: str, new_title: str):
        """Renames an annotation title (legacy method)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            cursor.execute(
                "UPDATE Annotations SET Title = ?, UpdatedAt = ? WHERE JiraKey = ? AND Title = ? AND IsDeleted = 0",
                (new_title, current_time, jira_key, old_title)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_annotations(self) -> list:
        """Retrieves all annotations across all Jira keys (legacy method)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT JiraKey, Title, UpdatedAt FROM Annotations WHERE IsDeleted = 0 ORDER BY UpdatedAt DESC')
            return cursor.fetchall()
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
            
    def update_local_worklog_comment(self, jira_key: str, start_time: datetime, comment: str):
        """Updates the comment of a worklog entry based on jira_key and start_time.
        
        Args:
            jira_key: The Jira issue key
            start_time: The start time of the worklog entry
            comment: The new comment text
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE LocalWorklogHistory SET Comment = ? WHERE JiraKey = ? AND StartTime = ?',
                (comment, jira_key, start_time.isoformat())
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
            # Prima verifica se esiste già un record per questo jira_key
            cursor.execute(
                'SELECT COUNT(*) FROM ViewHistory WHERE JiraKey = ?',
                (jira_key,)
            )
            exists = cursor.fetchone()[0] > 0
            
            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            # Otteniamo il timestamp UTC con il suffisso Z che indica UTC
            current_time = datetime.now(timezone.utc).isoformat()
            
            if exists:
                # Se esiste, aggiorna solo il timestamp
                cursor.execute(
                    'UPDATE ViewHistory SET LastViewedAt = ? WHERE JiraKey = ?',
                    (current_time, jira_key)
                )
            else:
                # Se non esiste, inserisci un nuovo record
                cursor.execute(
                    'INSERT INTO ViewHistory (JiraKey, LastViewedAt) VALUES (?, ?)',
                    (jira_key, current_time)
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
            
            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            if result:
                # Update existing entry
                cursor.execute(
                    'UPDATE JQLHistory SET LastUsedAt = ? WHERE Id = ?',
                    (current_time, result[0])
                )
            else:
                # Add new entry
                cursor.execute(
                    'INSERT INTO JQLHistory (Query, LastUsedAt) VALUES (?, ?)',
                    (query, current_time)
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

            # Otteniamo il timestamp attuale con informazioni sul fuso orario
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            cursor.execute(
                'INSERT OR REPLACE INTO NotificationSubscriptions (JiraKey, LastCheckedTimestamp, last_comment_date, is_read) VALUES (?, ?, NULL, 1)',
                (jira_key, current_time)
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
    
    # --- File Attachment Methods ---
    def add_file_attachment(self, jira_key: str, attachment_id: str, file_name: str, 
                           file_path: str, file_hash: str, file_size: int, mime_type: str = None):
        """
        Adds or updates a file attachment record.
        
        Args:
            jira_key: The Jira issue key
            attachment_id: The unique ID of the attachment from Jira
            file_name: The original file name
            file_path: The local path where the file is saved
            file_hash: SHA-256 hash of the file content for identification
            file_size: Size of the file in bytes
            mime_type: Optional MIME type of the file
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get current time in ISO format with timezone info
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO FileAttachments 
                (JiraKey, AttachmentId, FileName, FilePath, FileHash, FileSize, MimeType, DownloadedAt, LastCheckedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (jira_key, attachment_id, file_name, file_path, file_hash, file_size, mime_type, current_time, current_time))
            conn.commit()
        finally:
            conn.close()
    
    def get_file_attachment(self, jira_key: str, attachment_id: str):
        """
        Gets a file attachment record by Jira key and attachment ID.
        
        Returns:
            A dictionary with file attachment details or None if not found.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Id, JiraKey, AttachmentId, FileName, FilePath, FileHash, FileSize, MimeType, DownloadedAt, LastCheckedAt
                FROM FileAttachments 
                WHERE JiraKey = ? AND AttachmentId = ?
            """, (jira_key, attachment_id))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'id': row[0],
                'jira_key': row[1],
                'attachment_id': row[2],
                'file_name': row[3],
                'file_path': row[4],
                'file_hash': row[5],
                'file_size': row[6],
                'mime_type': row[7],
                'downloaded_at': row[8],
                'last_checked_at': row[9]
            }
        finally:
            conn.close()
    
    def get_file_attachments_by_jira_key(self, jira_key: str):
        """
        Gets all file attachments for a specific Jira issue.
        
        Returns:
            A list of dictionaries with file attachment details.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Id, JiraKey, AttachmentId, FileName, FilePath, FileHash, FileSize, MimeType, DownloadedAt, LastCheckedAt
                FROM FileAttachments 
                WHERE JiraKey = ?
                ORDER BY DownloadedAt DESC
            """, (jira_key,))
            
            attachments = []
            for row in cursor.fetchall():
                attachments.append({
                    'id': row[0],
                    'jira_key': row[1],
                    'attachment_id': row[2],
                    'file_name': row[3],
                    'file_path': row[4],
                    'file_hash': row[5],
                    'file_size': row[6],
                    'mime_type': row[7],
                    'downloaded_at': row[8],
                    'last_checked_at': row[9]
                })
            return attachments
        finally:
            conn.close()
    
    def update_attachment_last_checked(self, jira_key: str, attachment_id: str):
        """Updates the last checked timestamp for an attachment."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get current time in ISO format with timezone info
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                UPDATE FileAttachments
                SET LastCheckedAt = ?
                WHERE JiraKey = ? AND AttachmentId = ?
            """, (current_time, jira_key, attachment_id))
            conn.commit()
        finally:
            conn.close()
            
    def delete_file_attachment(self, jira_key: str, attachment_id: str):
        """Removes a file attachment record."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM FileAttachments
                WHERE JiraKey = ? AND AttachmentId = ?
            """, (jira_key, attachment_id))
            conn.commit()
        finally:
            conn.close()
            
    def store_priority_update(self, jira_key: str, priority_id: str, priority_name: str = None) -> bool:
        """Store a priority update for later syncing with Jira."""
        conn = self.get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO PriorityUpdates
                (JiraKey, PriorityId, PriorityName, UpdatedAt, SyncStatus)
                VALUES (?, ?, ?, datetime('now'), 'pending')
            """, (jira_key, priority_id, priority_name))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error storing priority update: {e}")
            return False
        finally:
            conn.close()
    
    def get_local_priority(self, jira_key: str) -> dict:
        """Get the local priority override for a Jira issue."""
        conn = self.get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT PriorityId, PriorityName
                FROM PriorityUpdates
                WHERE JiraKey = ?
                ORDER BY UpdatedAt DESC
                LIMIT 1
            """, (jira_key,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'name': result[1] if result[1] else result[0]
                }
            return None
        except sqlite3.Error as e:
            print(f"Database error getting local priority: {e}")
            return None
        finally:
            conn.close()
    
    def set_local_priority(self, jira_key: str, priority_id: str, priority_name: str) -> bool:
        """Set a local priority override for a Jira issue."""
        return self.store_priority_update(jira_key, priority_id, priority_name)
    
    def remove_local_priority(self, jira_key: str) -> bool:
        """Remove the local priority override for a Jira issue."""
        conn = self.get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM PriorityUpdates
                WHERE JiraKey = ?
            """, (jira_key,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error removing local priority: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_priority_updates(self) -> list:
        """Get all pending priority updates."""
        conn = self.get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT JiraKey, PriorityId, PriorityName, UpdatedAt
                FROM PriorityUpdates
                WHERE SyncStatus = 'pending'
                ORDER BY UpdatedAt ASC
            """)
            
            results = cursor.fetchall()
            return [
                {
                    'jira_key': row[0],
                    'priority_id': row[1],
                    'priority_name': row[2],
                    'updated_at': row[3]
                }
                for row in results
            ]
        except sqlite3.Error as e:
            print(f"Database error getting priority updates: {e}")
            return []
        finally:
            conn.close()
    
    def mark_priority_update_synced(self, jira_key: str) -> bool:
        """Mark a priority update as synced."""
        conn = self.get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE PriorityUpdates
                SET SyncStatus = 'synced', SyncedAt = datetime('now')
                WHERE JiraKey = ?
            """, (jira_key,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error marking priority update as synced: {e}")
            return False
        finally:
            conn.close()
            
    def close(self):
        if self.conn:
            self.conn.close()
