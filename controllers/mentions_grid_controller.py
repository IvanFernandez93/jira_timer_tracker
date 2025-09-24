from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt
import webbrowser
import logging

_logger = logging.getLogger('JiraTimeTracker')

class MentionsGridController:
    """
    Controller for the mentions grid view.
    """
    def __init__(self, view, jira_service):
        self.view = view
        self.jira_service = jira_service
        self.mentions_data = []
        
        # Connect signals
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals to slots."""
        self.view.refresh_btn.clicked.connect(self.load_mentions)
        self.view.open_btn.clicked.connect(self._open_selected_ticket)
        self.view.close_btn.clicked.connect(self.view.close)
        # Double click on row should open the ticket
        self.view.table.doubleClicked.connect(self._open_selected_ticket)
    
    def load_mentions(self):
        """Load tickets that mention the current user."""
        try:
            # Show "Loading..." indicator
            self.view.setCursor(Qt.CursorShape.WaitCursor)
            self.view.table.setRowCount(0)
            
            # Get mentions data
            mentions, error_msg = self.jira_service.search_issues_with_mentions()
            if error_msg:
                QMessageBox.warning(self.view, "Error", error_msg)
                return
                
            # Save the data
            self.mentions_data = mentions
            
            # Populate the table
            self._populate_grid()
            
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Failed to load mentions: {e}")
            _logger.error(f"Error in load_mentions: {e}")
        finally:
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _populate_grid(self):
        """Populate the grid with the tickets that mention the user."""
        self.view.table.setRowCount(0)  # Clear existing rows
        
        # Add each mention to the grid
        for row, mention in enumerate(self.mentions_data):
            self.view.table.insertRow(row)
            
            # Set the key (column 0)
            key_item = QTableWidgetItem(mention.get('key', ''))
            key_item.setData(Qt.ItemDataRole.UserRole, mention.get('key', ''))  # Store key for later use
            self.view.table.setItem(row, 0, key_item)
            
            # Set the summary (column 1)
            summary_item = QTableWidgetItem(mention.get('summary', ''))
            summary_item.setToolTip(mention.get('summary', ''))
            self.view.table.setItem(row, 1, summary_item)
            
            # Set the status (column 2)
            status_item = QTableWidgetItem(mention.get('status', 'Unknown'))
            self.view.table.setItem(row, 2, status_item)
            
            # Set the priority (column 3)
            priority_item = QTableWidgetItem(mention.get('priority', 'N/A'))
            self.view.table.setItem(row, 3, priority_item)
            
            # Set the updated date (column 4)
            updated_str = mention.get('updated', '')
            # Format the date if needed
            updated_item = QTableWidgetItem(updated_str)
            self.view.table.setItem(row, 4, updated_item)
    
    def _open_selected_ticket(self):
        """Opens the selected ticket in Jira."""
        # Get the selected row
        selected_rows = self.view.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self.view, "No Selection", "Please select a ticket to open.")
            return
            
        # Get the key from the selected row (stored in the first column's user role)
        row = selected_rows[0].row()
        key_item = self.view.table.item(row, 0)
        if not key_item:
            return
            
        issue_key = key_item.data(Qt.ItemDataRole.UserRole)
        
        try:
            # Open the ticket in the browser
            issue_url = f"{self.jira_service.jira.server_url}/browse/{issue_key}"
            webbrowser.open(issue_url)
        except Exception as e:
            QMessageBox.warning(self.view, "Error", f"Could not open browser: {e}")
            _logger.error(f"Error opening ticket {issue_key} in browser: {e}")