from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                         QComboBox, QColorDialog, QListWidget, QListWidgetItem, QFrame, 
                         QFormLayout, QLineEdit, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QFont

class PriorityConfigDialog(QDialog):
    """
    Dialog for configuring Jira issue priorities.
    Allows users to customize priority colors and labels.
    """
    priorities_updated = pyqtSignal()
    
    def __init__(self, parent=None, priorities=None, priority_configs=None):
        """
        Initialize the priority configuration dialog.
        
        Args:
            parent: Parent widget
            priorities: List of priorities from Jira
            priority_configs: Dictionary of priority configurations from local DB
        """
        super().__init__(parent)
        self.setWindowTitle("Priority Configuration")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.priorities = priorities or []
        self.priority_configs = priority_configs or {}
        self.default_colors = {
            "Highest": "#FF0000",  # Red
            "High": "#FF9900",     # Orange
            "Medium": "#FFFF00",   # Yellow
            "Low": "#00FF00",      # Green
            "Lowest": "#0000FF",   # Blue
        }
        
        self._init_ui()
        self._populate_priorities()
        
    def _init_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Configure the appearance of priorities in the application.")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)
        
        # Priority List
        self.priority_list = QListWidget()
        self.priority_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.priority_list.currentItemChanged.connect(self._on_priority_selected)
        main_layout.addWidget(self.priority_list)
        
        # Form for editing the selected priority
        form_frame = QFrame()
        form_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        form_layout = QFormLayout(form_frame)
        
        self.name_label = QLabel("Select a priority")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        form_layout.addRow("Priority:", self.name_label)
        
        # Custom Label
        self.custom_label = QLineEdit()
        self.custom_label.setPlaceholderText("Leave empty to use default label")
        form_layout.addRow("Custom Label:", self.custom_label)
        
        # Color Selector
        color_layout = QHBoxLayout()
        self.color_preview = QFrame()
        self.color_preview.setMinimumSize(24, 24)
        self.color_preview.setMaximumSize(24, 24)
        self.color_preview.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self._on_color_select)
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)
        form_layout.addRow("Color:", color_layout)
        
        # Reset to Default
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self._on_reset)
        form_layout.addRow("", self.reset_button)
        
        main_layout.addWidget(form_frame)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Disable form initially
        self._set_form_enabled(False)
        
    def _populate_priorities(self):
        """Populate the priority list with items from Jira."""
        self.priority_list.clear()
        
        # If no priorities from Jira, show some defaults
        if not self.priorities:
            default_names = ["Highest", "High", "Medium", "Low", "Lowest"]
            for name in default_names:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, {"id": name.lower(), "name": name})
                self.priority_list.addItem(item)
            return
            
        # Add priorities from Jira
        for priority in self.priorities:
            item = QListWidgetItem(priority.get("name", ""))
            item.setData(Qt.ItemDataRole.UserRole, priority)
            self.priority_list.addItem(item)
    
    def _on_priority_selected(self, current, previous):
        """Handle priority selection change."""
        if not current:
            self._set_form_enabled(False)
            return
            
        priority_data = current.data(Qt.ItemDataRole.UserRole)
        priority_id = priority_data.get("id", "")
        priority_name = priority_data.get("name", "")
        
        self.name_label.setText(priority_name)
        self._set_form_enabled(True)
        
        # Get configuration for this priority
        config = self.priority_configs.get(priority_id, {})
        
        # Set custom label if it exists
        self.custom_label.setText(config.get('label', ''))
        
        # Set color - use default if not configured
        color_code = config.get('color', self.default_colors.get(priority_name, "#808080"))
        self.color_preview.setStyleSheet(f"background-color: {color_code};")
        self.color_preview.setProperty("current_color", color_code)
    
    def _on_color_select(self):
        """Open color dialog to select a new color."""
        current_color = QColor(self.color_preview.property("current_color") or "#808080")
        color = QColorDialog.getColor(current_color, self, "Select Priority Color")
        
        if color.isValid():
            color_code = color.name()
            self.color_preview.setStyleSheet(f"background-color: {color_code};")
            self.color_preview.setProperty("current_color", color_code)
    
    def _on_reset(self):
        """Reset the selected priority to default settings."""
        current_item = self.priority_list.currentItem()
        if not current_item:
            return
            
        priority_data = current_item.data(Qt.ItemDataRole.UserRole)
        priority_name = priority_data.get("name", "")
        
        # Reset to default color
        default_color = self.default_colors.get(priority_name, "#808080")
        self.color_preview.setStyleSheet(f"background-color: {default_color};")
        self.color_preview.setProperty("current_color", default_color)
        
        # Clear custom label
        self.custom_label.clear()
    
    def _on_save(self):
        """Save all priority configurations."""
        updated_configs = {}
        
        # Iterate through all priorities
        for i in range(self.priority_list.count()):
            item = self.priority_list.item(i)
            priority_data = item.data(Qt.ItemDataRole.UserRole)
            priority_id = priority_data.get("id", "")
            
            # If this is the selected item, get values from form
            if item == self.priority_list.currentItem():
                color_code = self.color_preview.property("current_color")
                custom_label = self.custom_label.text().strip()
                
                updated_configs[priority_id] = {
                    'color': color_code,
                    'label': custom_label if custom_label else None
                }
            else:
                # Keep existing configuration
                if priority_id in self.priority_configs:
                    updated_configs[priority_id] = self.priority_configs[priority_id]
        
        # Return updated configurations
        self.priority_configs = updated_configs
        self.priorities_updated.emit()
        self.accept()
    
    def _set_form_enabled(self, enabled):
        """Enable or disable the form controls."""
        self.custom_label.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
        self.name_label.setEnabled(enabled)
        
    def get_updated_configs(self):
        """Return the updated priority configurations."""
        return self.priority_configs