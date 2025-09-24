from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QColorDialog, QListWidgetItem
from PyQt6.QtGui import QColor, QBrush

from views.priority_config_dialog import PriorityConfigDialog

class PriorityColorConfigController(QObject):
    """
    Controller to manage the configuration of priorities and their colors.
    """
    colors_updated = pyqtSignal()  # Signal emitted when colors are updated
    
    def __init__(self, db_service):
        super().__init__()
        self.db_service = db_service
        self.view = None
        
    def show_dialog(self, parent=None):
        """Show the priority configuration dialog."""
        self.view = PriorityConfigDialog(parent)
        self._populate_table()
        self._connect_signals()
        self.view.exec()
        
    def _connect_signals(self):
        """Connect signals from the view."""
        # Adattiamo i collegamenti ai widget corretti nella view
        self.view.save_button.clicked.connect(self._save_changes)
        self.view.cancel_button.clicked.connect(self.view.reject)
        self.view.color_button.clicked.connect(self._edit_color)
        
    def _populate_table(self):
        """Populate the table with priorities from the database."""
        # La view ha priority_list invece di priority_table
        # Clear the list
        self.view.priority_list.clear()
        
        # Get priorities from database
        priorities = self.db_service.get_priority_colors()
        
        # Default priorities if none are found
        if not priorities:
            priorities = [
                ("Highest", "#FF0000"),  # Red
                ("High", "#FFA500"),     # Orange
                ("Medium", "#FFFF00"),   # Yellow
                ("Low", "#00FF00"),      # Green
                ("Lowest", "#0000FF")    # Blue
            ]
        
        # Add items to list
        for priority_name, color_hex in priorities:
            from PyQt6.QtWidgets import QListWidgetItem
            
            item = QListWidgetItem(priority_name)
            item.setData(Qt.ItemDataRole.UserRole, {"id": priority_name.lower(), "name": priority_name})
            
            # Set color if available
            if color_hex:
                # Salva il colore nei dati dell'item
                config = {"color": color_hex, "label": None}
                item.setData(Qt.ItemDataRole.UserRole + 1, config)
            
            # Add item to list
            self.view.priority_list.addItem(item)
        
    # Questi metodi non sono più necessari perché la nuova UI gestisce 
    # l'aggiunta e l'eliminazione delle priorità in modo diverso
    # Lasciamo dei metodi vuoti per compatibilità
    def _add_priority(self):
        """Add a new priority row - not needed in the new UI."""
        pass
        
    def _delete_priority(self):
        """Delete the selected priority row - not needed in the new UI."""
        pass
            
    def _edit_color(self):
        """Open color picker when clicking on the color button."""
        # Get the selected item from the list
        current_item = self.view.priority_list.currentItem()
        if not current_item:
            return
        
        # Get priority data
        priority_data = current_item.data(Qt.ItemDataRole.UserRole)
        priority_name = priority_data.get("name", "")
        
        # Get current color from the preview
        current_color_str = self.view.color_preview.property("current_color")
        current_color = QColor(current_color_str) if current_color_str else QColor("#FFFFFF")
        
        # Open color dialog
        color = QColorDialog.getColor(
            current_color, 
            self.view,
            f"Scegli un colore per '{priority_name}'"
        )
        
        if color.isValid():
            # Update the color preview
            color_code = color.name()
            self.view.color_preview.setStyleSheet(f"background-color: {color_code};")
            self.view.color_preview.setProperty("current_color", color_code)
                
    def _save_changes(self):
        """Save all priority configurations to the database."""
        # Otteniamo le configurazioni aggiornate dalla view
        updated_configs = self.view.get_updated_configs()
        priorities = []
        
        # Convertiamo le configurazioni nel formato richiesto dal database
        for priority_id, config in updated_configs.items():
            priority_name = ""
            # Troviamo il nome della priorità in base all'ID
            for i in range(self.view.priority_list.count()):
                item = self.view.priority_list.item(i)
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data.get("id", "") == priority_id:
                    priority_name = item_data.get("name", "")
                    break
            
            if priority_name:
                color_hex = config.get("color", None)
                priorities.append((priority_name, color_hex))
        
        # Save to database
        self.db_service.save_priority_colors(priorities)
        
        # Emit signal to notify that priorities have been updated
        self.colors_updated.emit()
        
        # Close dialog
        self.view.accept()