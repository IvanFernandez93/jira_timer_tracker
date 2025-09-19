from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView, QWidget
from PyQt6.QtGui import QColor, QBrush
from qfluentwidgets import TransparentToolButton

class HistoryViewController(QObject):
    """Controller for the History View."""
    issue_opened = pyqtSignal(str)  # Signal when an issue is opened from the history
    
    def __init__(self, view, db_service, jira_service):
        super().__init__()
        self.view = view
        self.db_service = db_service
        self.jira_service = jira_service
        self.issue_cache = {}  # Cache for issue data to avoid repeated Jira queries
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals from the view."""
        self.view.refresh_btn.clicked.connect(self.load_history)
        self.view.search_box.textChanged.connect(self._filter_table)
        self.view.table.doubleClicked.connect(self._on_row_double_clicked)
        
    def load_history(self):
        """Loads the view history from the database."""
        self.view.clear_table()
        self.view.hide_status()
        
        # Get view history from database
        history_items = self.db_service.get_view_history()
        
        if not history_items:
            self.view.show_info("Nessun elemento nella cronologia.")
            return
            
        # Add rows to the table
        self.view.table.setRowCount(len(history_items))
        
        # Dictionary to keep track of already loaded issues
        added_issues = set()
        row_index = 0
        
        # Add items to table
        for jira_key, last_viewed_at in history_items:
            # Skip duplicates (shouldn't happen with our DB schema but just in case)
            if jira_key in added_issues:
                continue
                
            added_issues.add(jira_key)
            
            # Create items
            key_item = QTableWidgetItem(jira_key)
            
            # For the title, we'll need to check our cache or query Jira
            title = self._get_issue_title(jira_key)
            title_item = QTableWidgetItem(title)
            
            # Format the timestamp
            date_str = last_viewed_at.split(".")[0].replace("T", " ")  # Simple formatting
            date_item = QTableWidgetItem(date_str)
            
            # Set items in the table
            self.view.table.setItem(row_index, 0, key_item)
            self.view.table.setItem(row_index, 1, title_item)
            self.view.table.setItem(row_index, 2, date_item)
            
            # Add action buttons
            self._add_action_buttons(row_index, jira_key)
            
            row_index += 1
            
        # Apply status colors based on status (if available in cache)
        self._apply_status_colors()
        
        # Adjust column widths
        self.view.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.view.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.view.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.view.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
    def _get_issue_title(self, jira_key):
        """Gets the issue title either from cache or Jira API."""
        if jira_key in self.issue_cache:
            return self.issue_cache[jira_key].get('summary', 'Titolo non disponibile')
            
        try:
            issue = self.jira_service.get_issue(jira_key)
            if issue:
                summary = issue.get('fields', {}).get('summary', 'Titolo non disponibile')
                status = issue.get('fields', {}).get('status', {}).get('name', '')
                
                # Cache the issue data
                self.issue_cache[jira_key] = {
                    'summary': summary,
                    'status': status
                }
                
                return summary
        except Exception as e:
            print(f"Error getting issue title: {e}")
            
        return "Titolo non disponibile"
        
    def _add_action_buttons(self, row, jira_key):
        """Adds action buttons to the row."""
        # Create an open button directly as cell widget
        open_btn = TransparentToolButton()
        open_btn.setText("")  # Remove text to prevent overlap
        open_btn.setIcon(TransparentToolButton().style().standardIcon(QWidget.style(open_btn).StandardPixmap.SP_DialogOpenButton))
        open_btn.setToolTip("Apri ticket in Jira")
        open_btn.setFixedSize(32, 32)  # Set fixed size for consistent appearance
        open_btn.clicked.connect(lambda _, key=jira_key: self._on_open_issue(key))
        
        # Set the button directly as the cell widget
        self.view.table.setCellWidget(row, 3, open_btn)
        
    def _apply_status_colors(self):
        """Applies status colors to the rows based on Jira status."""
        for row in range(self.view.table.rowCount()):
            key_item = self.view.table.item(row, 0)
            if not key_item:
                continue
                
            jira_key = key_item.text()
            
            # Get status from cache if available
            if jira_key in self.issue_cache and 'status' in self.issue_cache[jira_key]:
                status_name = self.issue_cache[jira_key]['status']
                
                # Get color for this status
                color_hex = self.db_service.get_status_color(status_name)
                
                if color_hex:
                    color = QColor(color_hex)
                    color.setAlpha(40)  # Semi-transparent
                    brush = QBrush(color)
                    
                    # Apply to all cells in the row
                    for col in range(3):  # Skip action column
                        item = self.view.table.item(row, col)
                        if item:
                            item.setBackground(brush)
                            
    def _filter_table(self, text):
        """Filters the table by text."""
        search_text = text.lower()
        for row in range(self.view.table.rowCount()):
            show_row = False
            
            # Check first two columns (key and title)
            for col in range(2):
                item = self.view.table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
                    
            self.view.table.setRowHidden(row, not show_row)
            
    def _on_row_double_clicked(self, index):
        """Handles double click on table row."""
        row = index.row()
        key_item = self.view.table.item(row, 0)
        if key_item:
            self._on_open_issue(key_item.text())
            
    def _on_open_issue(self, jira_key):
        """Emits signal to open the issue."""
        self.issue_opened.emit(jira_key)