from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QToolButton
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QIcon
from qfluentwidgets import FluentIcon as FIF

class SyncStatusIndicator(QWidget):
    """
    A status indicator widget for sync operations.
    Shows a colored dot and a count of pending/failed operations.
    """
    clicked = pyqtSignal()  # Signal emitted when the indicator is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_count = 0
        self._failed_count = 0
        self._error_state = False
        self._setup_ui()
        
    def _setup_ui(self):
        """Sets up the widget UI."""
        self.setToolTip("Stato della sincronizzazione")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Status indicator dot
        self.status_indicator = QWidget()
        self.status_indicator.setFixedSize(12, 12)
        
        # Count label
        self.count_label = QLabel("0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color: #555;")
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.count_label)
        
        # Set initial state
        self._update_appearance()
        
    def set_counts(self, pending: int, failed: int):
        """Sets the pending and failed operation counts."""
        self._pending_count = pending
        self._failed_count = failed
        self._error_state = failed > 0
        self._update_appearance()
        
    def _update_appearance(self):
        """Updates the widget appearance based on current state."""
        total_count = self._pending_count + self._failed_count
        
        # Update count label
        self.count_label.setText(str(total_count))
        
        # Set visibility based on count
        self.setVisible(total_count > 0)
        
        # Update tooltip
        if total_count > 0:
            tooltip = []
            if self._pending_count > 0:
                tooltip.append(f"{self._pending_count} operazioni in attesa")
            if self._failed_count > 0:
                tooltip.append(f"{self._failed_count} operazioni fallite")
            self.setToolTip("\n".join(tooltip))
        else:
            self.setToolTip("Nessuna operazione in coda")
            
    def _update_appearance(self):
        """Updates the widget appearance based on current state."""
        total_count = self._pending_count + self._failed_count
        
        # Update count label
        self.count_label.setText(str(total_count))
        
        # Set visibility based on count
        self.setVisible(total_count > 0)
        
        # Update status indicator color
        if self._error_state:
            color = "#FF3232"  # Red for error
        elif self._pending_count > 0:
            color = "#FFA500"  # Orange for pending
        else:
            color = "#32CD32"  # Green for ok
            
        self.status_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
            border: 1px solid {color};
        """)
        
        # Update tooltip
        if total_count > 0:
            tooltip = []
            if self._pending_count > 0:
                tooltip.append(f"{self._pending_count} operazioni in attesa")
            if self._failed_count > 0:
                tooltip.append(f"{self._failed_count} operazioni fallite")
            self.setToolTip("\n".join(tooltip))
        else:
            self.setToolTip("Nessuna operazione in coda")
        
    def mousePressEvent(self, event):
        """Handles mouse press events to emit the clicked signal."""
        self.clicked.emit()
        super().mousePressEvent(event)