from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from views.status_color_dialog import StatusColorDialog

class StatusColorController(QObject):
    """Controller for the status color configuration dialog."""
    
    def __init__(self, db_service, parent=None):
        super().__init__()
        self.db_service = db_service
        # Parent the dialog to the provided parent to ensure correct stacking
        self.dialog = StatusColorDialog(parent)
        
        # Override placeholder methods in the view
        self.dialog.add_status_color_to_db = self.add_status_color
        self.dialog.delete_status_color = self.delete_status_color
        self.dialog.update_status_color_in_db = self.update_status_color
        
    def run(self):
        """Shows the dialog and returns the result."""
        # Populate the table with current status colors
        status_colors = self.db_service.get_all_status_colors()
        self.dialog.populate_table(status_colors)
        
        # Show the dialog and return the result
        return self.dialog.exec()
    
    def add_status_color(self, status_name, color_hex):
        """Adds a new status color to the database."""
        self.db_service.set_status_color(status_name, color_hex)
        
        # Refresh the table
        status_colors = self.db_service.get_all_status_colors()
        self.dialog.populate_table(status_colors)
        
    def update_status_color(self, status_name, color_hex):
        """Updates an existing status color in the database."""
        self.db_service.set_status_color(status_name, color_hex)
        
        # Refresh the table
        status_colors = self.db_service.get_all_status_colors()
        self.dialog.populate_table(status_colors)
        
    def delete_status_color(self, status_name):
        """Deletes a status color from the database."""
        self.db_service.delete_status_color(status_name)
        
        # Refresh the table
        status_colors = self.db_service.get_all_status_colors()
        self.dialog.populate_table(status_colors)