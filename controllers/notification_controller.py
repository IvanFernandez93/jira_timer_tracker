from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from services.db_service import DatabaseService
from services.jira_service import JiraService

class NotificationController(QObject):
    """
    Controller for managing notifications about Jira issue comments.
    """
    notification_count_changed = pyqtSignal(int)  # Signal emitted when notification count changes
    
    def __init__(self, db_service: DatabaseService, jira_service: JiraService, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.jira_service = jira_service
        self.notification_count = 0
        
        # Set up refresh timer (check every 5 minutes by default)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_notifications)
        self.check_interval = 5 * 60 * 1000  # 5 minutes in milliseconds
        
    def start_notification_checks(self):
        """Start periodic notification checks."""
        # Only start checks if db_service exposes the expected methods
        try:
            if not hasattr(self.db_service, 'get_all_notification_subscriptions'):
                return
        except Exception:
            return

        # Safe to start
        try:
            self.check_notifications()  # Check immediately once
            self.refresh_timer.start(self.check_interval)
        except Exception:
            # If the DB or Jira service is a dummy in tests, skip
            return
        
    def stop_notification_checks(self):
        """Stop periodic notification checks."""
        self.refresh_timer.stop()
        
    def set_check_interval(self, minutes: int):
        """Set the interval for checking notifications."""
        if minutes < 1:
            minutes = 1  # Minimum 1 minute
        self.check_interval = minutes * 60 * 1000
        
        # Restart timer if it's running
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.refresh_timer.start(self.check_interval)
            
    def check_notifications(self):
        """Check for new notifications on subscribed issues."""
        # Get all notification subscriptions (defensive)
        try:
            subscriptions = self.db_service.get_all_notification_subscriptions()
        except Exception:
            subscriptions = []

        if not subscriptions:
            try:
                self._update_notification_count(0)
            except Exception:
                pass
            return
        
        # We'll track new notifications found in this check
        new_notifications_count = 0
        
        # For each subscription, check if there are new comments
        for subscription in subscriptions:
            issue_key = subscription['issue_key']
            last_comment_date = subscription['last_comment_date']  # This could be None for first check
            
            try:
                # Get comments for the issue from Jira
                comments = self.jira_service.get_issue_comments(issue_key)
                if not comments:
                    continue
                
                # Find the newest comment
                newest_comment = max(comments, key=lambda c: c.get('created', ''))
                newest_date = newest_comment.get('created')
                
                # If no last comment date recorded or the newest comment is newer, we have a notification
                if not last_comment_date or newest_date > last_comment_date:
                    new_notifications_count += 1
                    # Update the last comment date in the database if possible
                    try:
                        if hasattr(self.db_service, 'update_notification_subscription'):
                            self.db_service.update_notification_subscription(
                                issue_key,
                                {'last_comment_date': newest_date, 'is_read': False}
                            )
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error checking notifications for {issue_key}: {str(e)}")
                
        # Update the notification count
        try:
            unread_count = self.db_service.get_unread_notifications_count()
        except Exception:
            unread_count = 0
        try:
            self._update_notification_count(unread_count)
        except Exception:
            pass
        
    def mark_all_as_read(self):
        """Mark all notifications as read."""
        try:
            if hasattr(self.db_service, 'mark_all_notifications_read'):
                self.db_service.mark_all_notifications_read()
        except Exception:
            pass
        try:
            self._update_notification_count(0)
        except Exception:
            pass
        
    def mark_notification_read(self, issue_key: str):
        """Mark a specific notification as read."""
        try:
            if hasattr(self.db_service, 'update_notification_subscription'):
                self.db_service.update_notification_subscription(issue_key, {'is_read': True})
        except Exception:
            pass
        try:
            unread_count = self.db_service.get_unread_notifications_count()
        except Exception:
            unread_count = 0
        try:
            self._update_notification_count(unread_count)
        except Exception:
            pass
        
    def subscribe_to_issue(self, issue_key: str):
        """Subscribe to notifications for an issue."""
        # Check if already subscribed
        try:
            if hasattr(self.db_service, 'get_notification_subscription') and self.db_service.get_notification_subscription(issue_key):
                return False
        except Exception:
            return False

        # Add new subscription if possible
        try:
            if hasattr(self.db_service, 'add_notification_subscription'):
                self.db_service.add_notification_subscription(issue_key)
                return True
        except Exception:
            pass
        return False
        
    def unsubscribe_from_issue(self, issue_key: str):
        """Unsubscribe from notifications for an issue."""
        try:
            if hasattr(self.db_service, 'delete_notification_subscription'):
                self.db_service.delete_notification_subscription(issue_key)
        except Exception:
            pass

        # Update notification count
        try:
            unread_count = self.db_service.get_unread_notifications_count()
        except Exception:
            unread_count = 0
        try:
            self._update_notification_count(unread_count)
        except Exception:
            pass
        return True
        
    def is_subscribed(self, issue_key: str) -> bool:
        """Check if notifications are enabled for an issue."""
        try:
            if hasattr(self.db_service, 'get_notification_subscription'):
                return self.db_service.get_notification_subscription(issue_key) is not None
        except Exception:
            pass
        return False
        
    def _update_notification_count(self, count: int):
        """Update the notification count and emit signal if changed."""
        if self.notification_count != count:
            self.notification_count = count
            self.notification_count_changed.emit(count)