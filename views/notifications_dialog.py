from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QAbstractItemView, QFrame, QWidget)
from PyQt6.QtGui import QIcon
from qfluentwidgets import (FluentIcon, MessageBox, PushButton, 
                           TableWidget, ComboBox, LineEdit, SearchLineEdit,
                           IconWidget, Flyout)

from controllers.notification_controller import NotificationController
from services.jira_service import JiraService

class NotificationsDialog(QDialog):
    """Dialog for managing notification subscriptions."""
    
    # Signal emitted when user wants to open issue detail
    open_issue_detail = pyqtSignal(str)  # Emits jira_key
    
    def __init__(self, notification_controller: NotificationController, jira_service: JiraService, parent=None):
        super().__init__(parent)
        self.notification_controller = notification_controller
        self.jira_service = jira_service
        self.setWindowTitle("Gestione Notifiche")
        self.setMinimumSize(600, 400)
        
        # Default notification colors
        self.unread_color = "#FF6B6B"  # Red
        self.read_color = "#FFD93D"    # Yellow
        
        self._setup_ui()
        self._load_subscriptions()
        
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Notifiche Jira")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        refresh_btn = PushButton("Aggiorna")
        refresh_btn.setIcon(FluentIcon.SYNC)
        refresh_btn.clicked.connect(self._check_notifications_now)
        
        mark_all_read_btn = PushButton("Segna tutto come letto")
        mark_all_read_btn.clicked.connect(self._mark_all_as_read)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(mark_all_read_btn)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Add new subscription section
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Aggiungi issue:"))
        
        self.issue_key_input = LineEdit(self)
        self.issue_key_input.setPlaceholderText("Inserisci il codice della issue (es. PROJ-123)")
        add_layout.addWidget(self.issue_key_input)
        
        add_btn = PushButton("Aggiungi")
        add_btn.setIcon(FluentIcon.ADD)
        add_btn.clicked.connect(self._add_subscription)
        add_layout.addWidget(add_btn)
        
        layout.addLayout(add_layout)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Table for subscriptions
        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Issue Key", "Sommario", "Ultima Notifica", "Stato", "Azioni"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Issue Key column auto-resize
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Summary column stretches
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Last notification column auto-resize
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status column auto-resize
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Actions column fixed width
        self.table.setColumnWidth(4, 100)  # Set fixed width for actions column
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Enable double click to open issue detail
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        close_btn = PushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
    def _load_subscriptions(self):
        """Load and display notification subscriptions."""
        # Clear table
        self.table.setRowCount(0)
        
        # Get all subscriptions from database
        subscriptions = self.notification_controller.db_service.get_all_notification_subscriptions()
        if not subscriptions:
            return
            
        # Populate table
        self.table.setRowCount(len(subscriptions))
        row = 0
        
        for sub in subscriptions:
            # Issue Key
            key_item = QTableWidgetItem(sub['issue_key'])
            key_item.setToolTip(sub['issue_key'])  # Show full key on hover
            self.table.setItem(row, 0, key_item)
            
            # Summary - try to get from Jira if possible
            summary = "Caricamento..."
            self.table.setItem(row, 1, QTableWidgetItem(summary))
            
            # Load issue summary asynchronously (we'll just simulate it here)
            try:
                issue = self.jira_service.get_issue(sub['issue_key'])
                if issue and 'fields' in issue and 'summary' in issue['fields']:
                    summary = issue['fields']['summary']
                    self.table.setItem(row, 1, QTableWidgetItem(summary))
            except Exception:
                self.table.setItem(row, 1, QTableWidgetItem("Non disponibile"))
            
            # Last notification date
            last_date = sub['last_comment_date'] or "Mai"
            if last_date != "Mai":
                # Format date nicely
                last_date = last_date.split('T')[0]
            self.table.setItem(row, 2, QTableWidgetItem(last_date))
            
            # Status (read/unread)
            status = "Letto" if sub['is_read'] else "Non letto"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(Qt.GlobalColor.darkGreen if sub['is_read'] else Qt.GlobalColor.darkRed)
            self.table.setItem(row, 3, status_item)
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)
            
            # Mark as read button
            if not sub['is_read']:
                read_btn = QPushButton()
                read_btn.setIcon(FluentIcon.ACCEPT_MEDIUM.icon())
                read_btn.setToolTip("Segna come letto")
                read_btn.setFixedSize(24, 24)
                read_btn.clicked.connect(lambda _, key=sub['issue_key']: self._mark_as_read(key))
                actions_layout.addWidget(read_btn)
            
            # Delete subscription button
            delete_btn = QPushButton()
            delete_btn.setIcon(FluentIcon.DELETE.icon())
            delete_btn.setToolTip("Cancella iscrizione")
            delete_btn.setFixedSize(24, 24)
            delete_btn.clicked.connect(lambda _, key=sub['issue_key']: self._delete_subscription(key))
            actions_layout.addWidget(delete_btn)
            
            # Open in browser button
            open_btn = QPushButton()
            open_btn.setIcon(FluentIcon.LINK.icon())
            open_btn.setToolTip("Apri in browser")
            open_btn.setFixedSize(24, 24)
            open_btn.clicked.connect(lambda _, key=sub['issue_key']: self._open_in_browser(key))
            actions_layout.addWidget(open_btn)
            
            # Open detail button
            detail_btn = QPushButton()
            detail_btn.setIcon(FluentIcon.INFO.icon())
            detail_btn.setToolTip("Apri dettaglio")
            detail_btn.setFixedSize(24, 24)
            detail_btn.clicked.connect(lambda _, key=sub['issue_key']: self._open_issue_detail(key))
            actions_layout.addWidget(detail_btn)
            
            # Add layout to table
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 4, actions_widget)
            
            row += 1
            
        # Apply row highlighting after populating table
        self._apply_row_highlighting()
            
    def _add_subscription(self):
        """Add a new notification subscription."""
        issue_key = self.issue_key_input.text().strip()
        if not issue_key:
            Flyout.create(
                title='Errore',
                content='Inserisci un codice issue valido',
                target=self.issue_key_input,
                parent=self
            )
            return
            
        # Validate issue exists
        try:
            issue = self.jira_service.get_issue(issue_key)
            if not issue:
                Flyout.create(
                    title='Errore',
                    content=f'Issue {issue_key} non trovata',
                    target=self.issue_key_input,
                    parent=self
                )
                return
        except Exception as e:
            Flyout.create(
                title='Errore',
                content=f'Errore nel verificare la issue: {str(e)}',
                target=self.issue_key_input,
                parent=self
            )
            return
            
        # Add subscription
        success = self.notification_controller.subscribe_to_issue(issue_key)
        if success:
            self.issue_key_input.clear()
            self._load_subscriptions()
        else:
            Flyout.create(
                title='Informazione',
                content=f'Sei già iscritto alle notifiche per {issue_key}',
                target=self.issue_key_input,
                parent=self
            )
            
    def _delete_subscription(self, issue_key):
        """Delete a notification subscription."""
        msg_box = MessageBox(
            'Conferma cancellazione',
            f'Vuoi davvero cancellare l\'iscrizione per {issue_key}?',
            self
        )
        
        if msg_box.exec():
            self.notification_controller.unsubscribe_from_issue(issue_key)
            self._load_subscriptions()
            
    def _mark_as_read(self, issue_key):
        """Mark a notification as read."""
        self.notification_controller.mark_notification_read(issue_key)
        self._load_subscriptions()
        
    def _mark_all_as_read(self):
        """Mark all notifications as read."""
        self.notification_controller.mark_all_as_read()
        self._load_subscriptions()
        
    def _check_notifications_now(self):
        """Force an immediate check for notifications."""
        self.notification_controller.check_notifications()
        self._load_subscriptions()
        
    def _open_in_browser(self, issue_key):
        """Open the issue in browser."""
        self.jira_service.open_issue_in_browser(issue_key)
    
    def _open_issue_detail(self, issue_key):
        """Emit signal to open issue detail."""
        self.open_issue_detail.emit(issue_key)
    
    def _on_row_double_clicked(self, model_index):
        """Handle double click on table row to open issue detail."""
        row = model_index.row()
        key_item = self.table.item(row, 0)
        if key_item:
            issue_key = key_item.text()
            self._open_issue_detail(issue_key)
    
    def _apply_row_highlighting(self):
        """Apply row highlighting based on notification read status."""
        from PyQt6.QtGui import QColor
        
        for row in range(self.table.rowCount()):
            # Get the status item (column 3)
            status_item = self.table.item(row, 3)
            if status_item:
                status_text = status_item.text()
                
                # Choose color based on status
                if status_text == "Non letto":
                    color = QColor(self.unread_color)
                else:  # "Letto"
                    color = QColor(self.read_color)
                
                # Apply semi-transparent background to all cells in the row
                color.setAlpha(60)  # Semi-transparent
                
                for col in range(4):  # Skip actions column (4)
                    item = self.table.item(row, col)
                    if item:
                        from PyQt6.QtGui import QBrush
                        brush = QBrush(color)
                        item.setBackground(brush)
    
    def load_notification_colors(self, app_settings):
        """Load notification colors from app settings."""
        if app_settings:
            self.unread_color = app_settings.get_setting("notification_unread_color", "#FF6B6B")
            self.read_color = app_settings.get_setting("notification_read_color", "#FFD93D")

    def showEvent(self, event):
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(self)
        except Exception:
            pass

        super().showEvent(event)