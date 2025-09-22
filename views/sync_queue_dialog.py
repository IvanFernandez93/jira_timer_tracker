from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QColor, QBrush, QIcon
from qfluentwidgets import (
    FluentIcon as FIF, PrimaryPushButton, TransparentToolButton,
    InfoBar, InfoBarPosition
)

class SyncQueueDialog(QDialog):
    """Dialog for managing the synchronization queue."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Coda di Sincronizzazione")
        self.resize(800, 500)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Header
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("Coda di Sincronizzazione")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.main_layout.addLayout(self.header_layout)
        
        # Status summary
        self.status_layout = QHBoxLayout()
        self.pending_label = QLabel("In attesa: 0")
        self.failed_label = QLabel("Falliti: 0")
        self.completed_label = QLabel("Completati: 0")
        self.status_layout.addWidget(self.pending_label)
        self.status_layout.addWidget(self.failed_label)
        self.status_layout.addWidget(self.completed_label)
        self.status_layout.addStretch()
        self.main_layout.addLayout(self.status_layout)
        
        # Table for sync operations
        self.table = QTableWidget(0, 6)  # ID, Type, Payload, Status, Attempts, Actions
        self.table.setHorizontalHeaderLabels(["ID", "Tipo", "Dati", "Stato", "Tentativi", "Azioni"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.main_layout.addWidget(self.table)
        
        # Action buttons
        self.buttons_layout = QHBoxLayout()
        self.retry_all_btn = QPushButton("Riprova tutti")
        # Utilizziamo le icone di sistema per evitare problemi con FluentIcon
        from PyQt6.QtWidgets import QStyle
        self.retry_all_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.retry_all_btn.setToolTip("Riprova tutte le operazioni fallite")
        
        self.delete_selected_btn = QPushButton("Elimina selezionati")
        self.delete_selected_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_selected_btn.setToolTip("Elimina le operazioni selezionate")
        
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.retry_all_btn)
        self.buttons_layout.addWidget(self.delete_selected_btn)
        self.main_layout.addLayout(self.buttons_layout)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)
        
        # Error details area
        self.error_label = QLabel("Dettagli errore:")
        self.error_label.setVisible(False)
        self.error_details = QLabel()
        self.error_details.setStyleSheet("background-color: #f8f8f8; padding: 10px; border-radius: 5px; color: #d32f2f;")
        self.error_details.setWordWrap(True)
        self.error_details.setVisible(False)
        self.main_layout.addWidget(self.error_label)
        self.main_layout.addWidget(self.error_details)
        
    def clear_table(self):
        """Clears the table."""
        self.table.setRowCount(0)
        
    def show_error(self, message):
        """Shows an error message."""
        try:
            InfoBar.error(
                title="Errore",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
        except Exception:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Errore", str(message))
            except Exception:
                # Fallback: set error details
                self.error_label.setVisible(True)
                self.error_details.setText(str(message))
                self.error_details.setVisible(True)
        
    def show_info(self, message):
        """Shows an info message."""
        try:
            InfoBar.success(
                title="Info",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Info", str(message))
            except Exception:
                pass
        
    def show_error_details(self, message):
        """Shows error details at the bottom of the dialog."""
        self.error_label.setVisible(bool(message))
        self.error_details.setText(message)
        self.error_details.setVisible(bool(message))
        
    def hide_error_details(self):
        """Hides the error details area."""
        self.error_label.setVisible(False)
        self.error_details.setVisible(False)

    def showEvent(self, event):
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(self)
        except Exception:
            pass

        super().showEvent(event)