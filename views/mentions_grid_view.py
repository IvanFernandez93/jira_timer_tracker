from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class MentionsGridView(QDialog):
    """
    A view for displaying tickets that mention the current user.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tickets Mentioning Me")
        self.setMinimumSize(800, 500)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        
        # Create table widget
        self.table = QTableWidget(0, 5)  # 0 rows initially, 5 columns
        self.table.setHorizontalHeaderLabels(["Key", "Summary", "Status", "Priority", "Updated"])
        
        # Set header properties
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Add table to layout
        self.layout.addWidget(self.table)
        
        # Add buttons for actions
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh the list of tickets with mentions")
        
        self.open_btn = QPushButton("Open in Jira")
        self.open_btn.setToolTip("Open the selected ticket in Jira")
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setToolTip("Close this dialog")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.open_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(button_layout)