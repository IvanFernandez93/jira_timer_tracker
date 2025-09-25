"""
Git Issue History Dialog

Shows the Git-tracked history of changes for a Jira issue.
"""

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QMessageBox, QProgressDialog, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from qfluentwidgets import (
    FluentIcon as FIF, ToolButton, InfoBar, InfoBarPosition,
    CardWidget, CaptionLabel, BodyLabel, StrongBodyLabel
)
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

_logger = logging.getLogger('JiraTimeTracker.GitHistory')

class GitHistoryLoader(QThread):
    """Worker thread to load Git history without blocking the UI."""
    
    history_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, git_service, jira_key, limit=50):
        super().__init__()
        self.git_service = git_service
        self.jira_key = jira_key
        self.limit = limit
    
    def run(self):
        try:
            history = self.git_service.get_issue_history(self.jira_key, self.limit)
            self.history_loaded.emit(history)
        except Exception as e:
            self.error_occurred.emit(str(e))

class GitIssueHistoryDialog(QDialog):
    """Dialog to display Git-tracked history of a Jira issue."""
    
    def __init__(self, parent, git_tracking_service, jira_key, issue_summary=""):
        super().__init__(parent)
        self.git_service = git_tracking_service
        self.jira_key = jira_key
        self.issue_summary = issue_summary
        self.history_data = []
        
        self.setWindowTitle(f"Issue History: {jira_key}")
        self.setModal(True)
        self.resize(900, 600)
        
        self.setup_ui()
        self.load_history()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header_card = CardWidget()
        header_layout = QVBoxLayout(header_card)
        
        title_label = StrongBodyLabel(f"Git History: {self.jira_key}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        if self.issue_summary:
            summary_label = BodyLabel(self.issue_summary)
            summary_label.setWordWrap(True)
            header_layout.addWidget(summary_label)
        
        layout.addWidget(header_card)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = ToolButton(FIF.SYNC)
        self.refresh_btn.setToolTip("Refresh history")
        self.refresh_btn.clicked.connect(self.load_history)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.export_btn = ToolButton(FIF.SAVE)
        self.export_btn.setToolTip("Export history to file")
        self.export_btn.clicked.connect(self.export_history)
        toolbar_layout.addWidget(self.export_btn)
        
        toolbar_layout.addStretch()
        
        self.stats_label = CaptionLabel("Loading...")
        toolbar_layout.addWidget(self.stats_label)
        
        layout.addLayout(toolbar_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # History list (left side)
        history_widget = QFrame()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 0, 0, 0)
        
        history_label = BodyLabel("Commit History")
        history_layout.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_history_item_selected)
        history_layout.addWidget(self.history_list)
        
        splitter.addWidget(history_widget)
        
        # Details view (right side)
        details_widget = QFrame()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        details_label = BodyLabel("Commit Details")
        details_layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 9))
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_widget)
        
        # Set splitter proportions
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_history(self):
        """Load Git history for the issue."""
        self.history_list.clear()
        self.details_text.clear()
        self.stats_label.setText("Loading...")
        self.refresh_btn.setEnabled(False)
        
        # Start loading in background thread
        self.history_loader = GitHistoryLoader(self.git_service, self.jira_key)
        self.history_loader.history_loaded.connect(self.on_history_loaded)
        self.history_loader.error_occurred.connect(self.on_history_error)
        self.history_loader.start()
    
    def on_history_loaded(self, history_data: List[Dict[str, Any]]):
        """Handle loaded history data."""
        self.history_data = history_data
        self.refresh_btn.setEnabled(True)
        
        if not history_data:
            self.stats_label.setText("No history found")
            self.details_text.setPlainText("No Git history found for this issue.\n\nThis might mean:\n- The issue hasn't been tracked yet\n- Git tracking is not enabled\n- The issue file doesn't exist")
            return
        
        self.stats_label.setText(f"{len(history_data)} commits")
        
        # Populate history list
        for i, commit in enumerate(history_data):
            item_widget = self.create_history_item_widget(commit, i == 0)
            
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, commit)
            
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, item_widget)
        
        # Select first item by default
        if self.history_list.count() > 0:
            self.history_list.setCurrentRow(0)
            self.on_history_item_selected(self.history_list.item(0))
    
    def create_history_item_widget(self, commit: Dict[str, Any], is_latest: bool) -> CardWidget:
        """Create a widget for a history item."""
        card = CardWidget()
        card.setFixedHeight(80)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # Commit message and hash
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        message_label = BodyLabel(commit.get('message', 'No message'))
        message_label.setWordWrap(True)
        title_layout.addWidget(message_label)
        
        if is_latest:
            latest_label = CaptionLabel("LATEST")
            latest_label.setStyleSheet("color: #0078d4; font-weight: bold; background-color: #e1f5fe; padding: 2px 6px; border-radius: 3px;")
            title_layout.addWidget(latest_label)
        
        layout.addLayout(title_layout)
        
        # Commit details
        details_layout = QHBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parse and format date
        try:
            commit_date = datetime.fromisoformat(commit.get('date', '').replace(' ', 'T'))
            date_str = commit_date.strftime('%d %b %Y, %H:%M')
        except:
            date_str = commit.get('date', 'Unknown date')
        
        date_label = CaptionLabel(date_str)
        details_layout.addWidget(date_label)
        
        details_layout.addStretch()
        
        hash_label = CaptionLabel(f"#{commit.get('commit', 'unknown')[:7]}")
        hash_label.setStyleSheet("font-family: 'Consolas', monospace; background-color: #f5f5f5; padding: 1px 4px; border-radius: 2px;")
        details_layout.addWidget(hash_label)
        
        layout.addLayout(details_layout)
        
        return card
    
    def on_history_item_selected(self, item: QListWidgetItem):
        """Handle selection of a history item."""
        if not item:
            return
        
        commit_data = item.data(Qt.ItemDataRole.UserRole)
        if not commit_data:
            return
        
        # Load detailed changes for this commit
        try:
            changes = self.git_service.get_issue_changes(self.jira_key, commit_data['commit'])
            if changes:
                self.display_commit_details(commit_data, changes)
            else:
                self.details_text.setPlainText("Could not load commit details.")
        except Exception as e:
            _logger.error(f"Failed to load commit details: {e}")
            self.details_text.setPlainText(f"Error loading commit details: {e}")
    
    def display_commit_details(self, commit: Dict[str, Any], changes: Dict[str, Any]):
        """Display detailed information about a commit."""
        content = []
        
        # Header
        content.append(f"Commit: {commit.get('commit', 'unknown')}")
        content.append(f"Date: {commit.get('date', 'Unknown')}")
        content.append(f"Author: {commit.get('author', 'Unknown')}")
        content.append(f"Message: {commit.get('message', 'No message')}")
        content.append("")
        content.append("=" * 60)
        content.append("")
        
        # Changes (Git diff)
        diff_content = changes.get('diff', '')
        if diff_content:
            content.append("Changes made:")
            content.append("")
            content.append(diff_content)
        else:
            content.append("No diff information available.")
        
        self.details_text.setPlainText("\n".join(content))
    
    def on_history_error(self, error_message: str):
        """Handle error loading history."""
        self.refresh_btn.setEnabled(True)
        self.stats_label.setText("Error loading history")
        
        InfoBar.error(
            title="Loading Error",
            content=f"Failed to load Git history: {error_message}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
        self.details_text.setPlainText(f"Error loading history: {error_message}")
    
    def export_history(self):
        """Export history to a text file."""
        if not self.history_data:
            QMessageBox.information(self, "No Data", "No history data to export.")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Export History for {self.jira_key}",
            f"{self.jira_key}_git_history.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Git History for {self.jira_key}\n")
                f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for commit in self.history_data:
                    f.write(f"Commit: {commit.get('commit', 'unknown')}\n")
                    f.write(f"Date: {commit.get('date', 'Unknown')}\n")
                    f.write(f"Author: {commit.get('author', 'Unknown')}\n")
                    f.write(f"Message: {commit.get('message', 'No message')}\n")
                    f.write("-" * 40 + "\n\n")
            
            InfoBar.success(
                title="Export Successful",
                content=f"History exported to {filename}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export history: {e}")