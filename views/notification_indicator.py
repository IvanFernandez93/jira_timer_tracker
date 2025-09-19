from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtGui import QColor, QFont
from qfluentwidgets import IconWidget, FluentIcon as FIF

class NotificationIndicator(QWidget):
    """
    A notification indicator that shows a badge with the count of unread notifications.
    Using a simpler approach with standard widgets instead of custom painting.
    """
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create the icon widget
        self.icon = IconWidget(FIF.RINGER, self)
        self.icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon.setFixedSize(24, 24)
        
        # Create the badge label
        self.badge = QLabel(self)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(16, 16)
        self.badge.setStyleSheet("""
            background-color: #E74C3C;
            color: white;
            border-radius: 8px;
            font-weight: bold;
            font-size: 8px;
        """)
        
        # Add icon to layout
        layout.addWidget(self.icon)
        
        # Set initial state
        self.notification_count = 0
        self.setVisible(False)  # Hidden by default until notifications arrive
        self.setToolTip("Notifiche")
        self.setFixedSize(32, 24)
        
        # Position the badge on top of the icon at the top-right corner
        self.badge.move(16, 0)
        self.badge.hide()
        
    def set_count(self, count: int):
        """Sets the notification count and updates the badge."""
        if self.notification_count != count:
            self.notification_count = count
            self.setVisible(count > 0)
            
            if count > 0:
                # Update badge text
                self.badge.setText(str(min(99, count)))
                self.badge.show()
            else:
                self.badge.hide()
                
            self.setToolTip(f"{count} {'notifica' if count == 1 else 'notifiche'} non lette")
            
    def mousePressEvent(self, event):
        """Emits the clicked signal when the indicator is clicked."""
        self.clicked.emit()
        super().mousePressEvent(event)