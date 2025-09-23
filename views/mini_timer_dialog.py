from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from qfluentwidgets import PushButton, FluentIcon as FIF

class MiniTimerDialog(QDialog):
    """
    A small timer window that can be used from various places in the application.
    This implements the same interface as the mini widget but can be used as a standalone dialog.
    """
    def __init__(self, jira_key, parent=None):
        super().__init__(parent)
        
        self.jira_key = jira_key
        
        # Configura come una finestra normale ma sempre in primo piano
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setWindowTitle(f"Timer - {jira_key}")
        # Usa l'icona corretta
        try:
            self.setWindowIcon(FIF.CLOCK)
        except Exception:
            # Fallback se l'icona non è disponibile
            pass
        self.setFixedSize(320, 170)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Stile per la finestra del timer
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
                border: none;
            }
            QComboBox {
                color: #333333;
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        # Jira Key and Timer
        self.jira_key_label = QLabel(jira_key)
        self.jira_key_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Timer controls
        controls_layout = QHBoxLayout()
        self.play_btn = PushButton(FIF.PLAY, "Play")
        self.pause_btn = PushButton(FIF.PAUSE, "Pause")
        self.stop_btn = PushButton(FIF.CLOSE, "Stop")

        self.play_btn.setFixedWidth(80)
        self.pause_btn.setFixedWidth(80)
        self.stop_btn.setFixedWidth(80)

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)

        # Note field
        from PyQt6.QtWidgets import QLineEdit
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel("Nota:"))
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Aggiungi una nota per questo tempo tracciato")
        note_layout.addWidget(self.note_edit)

        # Assemble the layout
        main_layout.addWidget(self.jira_key_label)
        main_layout.addWidget(self.timer_label)
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(note_layout)

    def update_timer_display(self, seconds: int):
        """Update the timer display with the given number of seconds."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        self.timer_label.setText(time_str)

    def get_note(self) -> str:
        """Get the note from the note edit field."""
        return self.note_edit.text()
        
    def set_note_hint(self, hint: str):
        """Set a hint text for the note field.
        
        This will be displayed as a placeholder text and can be used to provide
        additional information about the ticket, such as if it's fictional.
        """
        self.note_edit.setPlaceholderText(hint)