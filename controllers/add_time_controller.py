from PyQt6.QtWidgets import QDialog
from views.add_time_dialog import AddTimeDialog

class AddTimeController:
    """
    Controller to manage the AddTimeDialog.
    """
    def __init__(self, parent_view=None):
        # parent_view should be the main window or the calling window so stacking behaves
        self.dialog = AddTimeDialog(parent_view)

    def run(self) -> dict | None:
        """
        Shows the dialog and returns the entered data upon acceptance.
        Returns None if the dialog is cancelled.
        """
        if self.dialog.exec() == QDialog.DialogCode.Accepted:
            return self.dialog.get_data()
        return None
