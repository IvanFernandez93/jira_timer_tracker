from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from qfluentwidgets import PushButton, FluentIcon

class MiniWidgetView(QWidget):
    """
    A small, always-on-top widget that appears when the main window is minimized.
    Fulfills requirement 2.6.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Window flags to make it a borderless, always-on-top widget
        self.setWindowFlags(
            Qt.WindowType.Tool | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 150)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Set a semi-transparent background style
        self.setStyleSheet("""
            MiniWidgetView {
                background-color: rgba(30, 30, 30, 0.9);
                border: 1px solid #555;
                border-radius: 12px;
            }
            QLabel {
                color: #F1F1F1;
                background-color: transparent;
                border: none;
            }
            QComboBox {
                color: #F1F1F1;
                background-color: #2D2D2D;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        # Jira Key and Timer
        self.jira_key_label = QLabel("No active Jira")
        self.jira_key_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Timer controls
        controls_layout = QHBoxLayout()
        self.play_btn = PushButton(FluentIcon.PLAY, "Play")
        self.pause_btn = PushButton(FluentIcon.PAUSE, "Pause")
        self.stop_btn = PushButton(FluentIcon.CLOSE, "Stop")  # Replacing STOP with CLOSE

        self.play_btn.setFixedWidth(80)
        self.pause_btn.setFixedWidth(80)
        self.stop_btn.setFixedWidth(80)

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)

        # Favorite Jiras ComboBox
        self.favorites_combo = QComboBox()
        self.favorites_combo.setPlaceholderText("Switch to favorite...")

        # Restore Button
        self.restore_btn = PushButton("Restore App")

        # Assemble the layout
        main_layout.addWidget(self.jira_key_label)
        main_layout.addWidget(self.timer_label)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.favorites_combo)
        main_layout.addWidget(self.restore_btn)

    def move_to_bottom_right(self, screen):
        """Moves the widget to the bottom right corner of the screen."""
        screen_geometry = screen.availableGeometry()
        widget_geometry = self.geometry()
        x = screen_geometry.width() - widget_geometry.width() - 20
        y = screen_geometry.height() - widget_geometry.height() - 20
        self.move(x, y)
