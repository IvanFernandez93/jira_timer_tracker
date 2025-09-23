from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime
import logging

from views.mini_timer_dialog import MiniTimerDialog

logger = logging.getLogger('JiraTimeTracker')

class MiniTimerController(QObject):
    """Controller for the mini timer dialog."""

    # Signals
    timer_started = pyqtSignal(str)  # Emits the jira_key when timer starts
    timer_paused = pyqtSignal(str)   # Emits the jira_key when timer is paused
    timer_stopped = pyqtSignal(str, int, str)  # Emits jira_key, seconds, and note when timer stops
    
    def __init__(self, jira_key, db_service, parent=None):
        super().__init__(parent)
        self.jira_key = jira_key
        self.db_service = db_service
        self.is_running = False
        self.seconds_tracked = 0
        self.start_time = None
        
        # Create the view
        self.view = MiniTimerDialog(jira_key)
        
        # Timer for updating the display
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.setInterval(1000)  # 1 second
        
        # Connect signals
        self._connect_signals()
        
        # Get initial local time
        self._load_local_time()
        
    def _connect_signals(self):
        """Connect signals from the view."""
        self.view.play_btn.clicked.connect(self.start_timer)
        self.view.pause_btn.clicked.connect(self.pause_timer)
        self.view.stop_btn.clicked.connect(self.stop_timer)
        
    def _load_local_time(self):
        """Load initial local time from database."""
        try:
            self.seconds_tracked = self.db_service.get_local_time(self.jira_key)
            self.view.update_timer_display(self.seconds_tracked)
        except Exception as e:
            logger.error(f"Error loading local time: {e}")
            self.seconds_tracked = 0
            
    def start_timer(self):
        """Start the timer."""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_time = datetime.now()
        self.timer.start()
        self.timer_started.emit(self.jira_key)
        logger.debug(f"Timer started for {self.jira_key}")
        
    def pause_timer(self):
        """Pause the timer."""
        if not self.is_running:
            return
            
        self.is_running = False
        self.timer.stop()
        
        # Update the database with the current time
        self._save_time()
        
        self.timer_paused.emit(self.jira_key)
        logger.debug(f"Timer paused for {self.jira_key}")
        
    def stop_timer(self):
        """Stop the timer and save the worklog."""
        if self.is_running:
            self.pause_timer()
            
        note = self.view.get_note()
        self.timer_stopped.emit(self.jira_key, self.seconds_tracked, note)
        logger.debug(f"Timer stopped for {self.jira_key}, total time: {self.seconds_tracked}s")
        
        # Reset the timer
        self.seconds_tracked = 0
        self.view.update_timer_display(0)
        
        # Close the dialog
        self.view.close()
        
    def _update_timer(self):
        """Update the timer display."""
        if not self.is_running:
            return
            
        elapsed_seconds = int((datetime.now() - self.start_time).total_seconds())
        current_total = self.seconds_tracked + elapsed_seconds
        
        self.view.update_timer_display(current_total)
        
    def _save_time(self):
        """Save the current time to the database."""
        if not self.start_time:
            return
            
        elapsed_seconds = int((datetime.now() - self.start_time).total_seconds())
        self.seconds_tracked += elapsed_seconds
        self.start_time = datetime.now()  # Reset start time
        
        try:
            # Save to database
            self.db_service.update_local_time(
                self.jira_key, 
                self.seconds_tracked,
                self.start_time.isoformat()
            )
        except Exception as e:
            logger.error(f"Error saving time: {e}")
            
    def run(self):
        """Show the dialog and start the timer."""
        self.view.show()
        # Start the timer immediately
        self.start_timer()
        
    def close(self):
        """Close the dialog."""
        # Make sure to save time before closing
        if self.is_running:
            self.pause_timer()
            
        self.view.close()