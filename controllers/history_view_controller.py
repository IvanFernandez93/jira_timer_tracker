from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView, QWidget
from PyQt6.QtGui import QColor, QBrush
from qfluentwidgets import TransparentToolButton
from .async_history_loader import AsyncHistoryLoader

class HistoryViewController(QObject):
    """Controller for the History View."""
    issue_opened = pyqtSignal(str)  # Signal when an issue is opened from the history
    
    def __init__(self, view, db_service, jira_service):
        super().__init__()
        self.view = view
        self.db_service = db_service
        self.jira_service = jira_service
        self.issue_cache = {}  # Cache for issue data
        
        # Initialize async loader
        self.async_loader = AsyncHistoryLoader(jira_service, db_service)
        self.async_loader.title_updated.connect(self._update_issue_title)
        self.async_loader.loading_progress.connect(self._update_loading_progress)
        self.async_loader.loading_completed.connect(self._on_async_loading_completed)
        
        # Connect refresh button
        self.view.refresh_btn.clicked.connect(self.load_history)
        
    def _connect_signals(self):
        """Connect signals from the view."""
        self.view.refresh_btn.clicked.connect(self.load_history)
        self.view.search_box.textChanged.connect(self._filter_table)
        self.view.table.doubleClicked.connect(self._on_row_double_clicked)
        
    def load_history(self):
        """Loads the view history from the database with async title loading."""
        self.view.clear_table()
        self.view.hide_status()
        
        # Get view history from database
        history_items = self.db_service.get_view_history()
        
        if not history_items:
            self.view.show_info("Nessun elemento nella cronologia.")
            return
            
        # Add rows to the table immediately with placeholders
        self.view.table.setRowCount(len(history_items))
        
        # Dictionary to keep track of already loaded issues
        added_issues = set()
        row_index = 0
        issue_keys_to_load = []
        
        # Add items to table with initial placeholders
        for jira_key, last_viewed_at in history_items:
            # Skip duplicates (shouldn't happen with our DB schema but just in case)
            if jira_key in added_issues:
                continue
                
            added_issues.add(jira_key)
            
            # Create items with immediate data
            key_item = QTableWidgetItem(jira_key)
            
            # Start with cached title if available, otherwise show loading placeholder
            cached_title = self._get_cached_title_immediate(jira_key)
            title = cached_title if cached_title else "Caricamento titolo..."
            title_item = QTableWidgetItem(title)
            
            # Format the timestamp and convert from UTC to local time
            try:
                # Importiamo datetime per la conversione di fuso orario
                from datetime import datetime, timezone, timedelta
                import time
                
                # Determiniamo se la stringa è in formato ISO o SQLite
                if 'T' in last_viewed_at or 'Z' in last_viewed_at:
                    # Formato ISO
                    dt_utc = datetime.fromisoformat(last_viewed_at.replace('Z', '+00:00'))
                else:
                    # Formato SQLite - assumiamo che sia già UTC
                    dt_utc = datetime.strptime(last_viewed_at, "%Y-%m-%d %H:%M:%S")
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                
                # Otteniamo l'offset del fuso orario locale in modo esplicito
                # Su Windows time.localtime().tm_gmtoff può non essere disponibile
                # Calcoliamo l'offset in un modo compatibile con Windows
                local_now = datetime.now()
                utc_now = datetime.now(timezone.utc)
                utc_offset = local_now - utc_now.replace(tzinfo=None)
                utc_offset_sec = int(utc_offset.total_seconds())
                
                # Converte a fuso orario locale usando l'offset esplicito
                dt_local = dt_utc.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(seconds=utc_offset_sec)))
                
                # Formatta la data secondo le preferenze locali
                date_str = dt_local.strftime("%d/%m/%Y %H:%M:%S")
            except Exception as e:
                # In caso di errore, usa il formato semplice precedente
                date_str = last_viewed_at.split(".")[0].replace("T", " ")
                print(f"Error converting date: {e}")
                
            date_item = QTableWidgetItem(date_str)
            
            # Set items in the table
            self.view.table.setItem(row_index, 0, key_item)
            self.view.table.setItem(row_index, 1, title_item)
            self.view.table.setItem(row_index, 2, date_item)
            
            # Add action buttons
            self._add_action_buttons(row_index, jira_key)
            
            # Add to list of issues that need title loading if not cached
            if not cached_title:
                issue_keys_to_load.append(jira_key)
            
            row_index += 1
            
        # Start async loading of titles for issues that need it
        if issue_keys_to_load:
            self.view.show_info(f"Caricamento titoli per {len(issue_keys_to_load)} issue...")
            self.async_loader.load_titles_async(issue_keys_to_load)
        
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
        
    def _get_cached_title_immediate(self, jira_key: str) -> str:
        """Gets issue title from immediate cache sources only (no API calls)"""
        # Check in-memory cache first
        if jira_key in self.issue_cache:
            return self.issue_cache[jira_key].get('summary', '')
            
        # Check database cache
        try:
            cached_issues = self.db_service.get_recent_issues(limit=100)
            for issue in cached_issues:
                if issue.get('key') == jira_key and issue.get('summary'):
                    # Add to memory cache
                    self.issue_cache[jira_key] = {
                        'summary': issue['summary'],
                        'status': issue.get('status', '')
                    }
                    return issue['summary']
        except Exception:
            pass
            
        return ""  # Empty string indicates not found in cache
        
    def _update_issue_title(self, jira_key: str, title: str, status: str):
        """Updates issue title in the table when loaded asynchronously"""
        try:
            # Update cache
            self.issue_cache[jira_key] = {
                'summary': title,
                'status': status
            }
            
            # Find the row with this jira_key and update the title
            for row in range(self.view.table.rowCount()):
                key_item = self.view.table.item(row, 0)
                if key_item and key_item.text() == jira_key:
                    title_item = self.view.table.item(row, 1)
                    if title_item:
                        title_item.setText(title)
                        
                        # Apply status color if we have status info
                        if status:
                            self._apply_status_color_to_row(row, status)
                    break
                    
        except Exception as e:
            print(f"Error updating issue title for {jira_key}: {e}")
            
    def _update_loading_progress(self, loaded: int, total: int):
        """Updates loading progress indicator"""
        try:
            if total > 0:
                percentage = (loaded / total) * 100
                self.view.show_info(f"Caricamento titoli: {loaded}/{total} ({percentage:.0f}%)")
        except Exception:
            pass
            
    def _on_async_loading_completed(self):
        """Called when async title loading is completed"""
        try:
            self.view.hide_status()
        except Exception:
            pass
            
    def _apply_status_color_to_row(self, row: int, status: str):
        """Applies status color to a specific row"""
        try:
            status_color_hex = self.db_service.get_status_color(status)
            if status_color_hex:
                color = QColor(status_color_hex)
                color.setAlpha(40)  # Semi-transparent
                brush = QBrush(color)
                
                # Apply color to all cells in the row
                for col in range(self.view.table.columnCount()):
                    item = self.view.table.item(row, col)
                    if item:
                        item.setBackground(brush)
        except Exception as e:
            print(f"Error applying status color to row {row}: {e}")
        
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
        
    def start_async_title_loading(self):
        """Starts async loading of issue titles for better performance."""
        try:
            # Get all issue keys currently in the table
            issue_keys = []
            for row in range(self.view.table.rowCount()):
                key_item = self.view.table.item(row, 0)
                if key_item:
                    issue_keys.append(key_item.text())
            
            if issue_keys:
                # Start async loading for issues that need title updates
                self.async_loader.start_loading(issue_keys)
                
        except Exception as e:
            print(f"Error starting async title loading: {e}")