from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QTimeEdit, QDateTimeEdit,
    QLineEdit, QDialogButtonBox
)
from PyQt6.QtCore import QDateTime, QTime, Qt

class AddTimeDialog(QDialog):
    """
    A dialog for manually adding a worklog.
    Req: 2.4.2.1
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Time Manually")

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.time_spent_edit = QTimeEdit()
        self.time_spent_edit.setDisplayFormat("hh:mm")
        
        self.start_date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd hh:mm")
        
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Optional comment for the worklog")
        
        self.task_edit = QLineEdit()
        self.task_edit.setText("compito")  # Default value as requested
        self.task_edit.setPlaceholderText("Description of the task")

        form_layout.addRow("Time Spent (hh:mm):", self.time_spent_edit)
        form_layout.addRow("Start Date:", self.start_date_edit)
        form_layout.addRow("Comment:", self.comment_edit)
        form_layout.addRow("Task:", self.task_edit)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> dict | None:
        """Returns the entered data as a dictionary."""
        time_spent = self.time_spent_edit.time()
        total_seconds = (time_spent.hour() * 3600) + (time_spent.minute() * 60)

        if total_seconds == 0:
            return None # Don't log if no time is entered

        return {
            "time_spent_seconds": total_seconds,
            "start_time": self.start_date_edit.dateTime().toPyDateTime(),
            "comment": self.comment_edit.text(),
            "task": self.task_edit.text()
        }

    def showEvent(self, event):
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(self)
        except Exception:
            pass

        super().showEvent(event)
