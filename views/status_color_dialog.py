from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QWidget
from PyQt6.QtCore import Qt
from qfluentwidgets import (
    TableWidget, PushButton, LineEdit, TransparentToolButton, 
    FluentIcon as FIF, InfoBar, InfoBarPosition
)

class StatusColorDialog(QDialog):
    """Dialog for configuring status colors."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configura Colori Stati")
        self.setMinimumSize(500, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Info text
        info_label = QLabel(
            "Configura i colori per gli stati specifici di Jira. "
            "Gli stati con colore assegnato verranno evidenziati nella griglia principale."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Table for status colors
        self.table = TableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nome Stato", "Colore", "Azioni", ""])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # Add new status layout
        add_layout = QHBoxLayout()
        self.new_status_input = LineEdit()
        self.new_status_input.setPlaceholderText("Nome nuovo stato...")
        add_layout.addWidget(self.new_status_input)
        
        self.color_btn = PushButton("Scegli colore")
        self.color_btn.setIcon(FIF.BRUSH)
        self.current_color = "#FFFFFF"  # Default white
        add_layout.addWidget(self.color_btn)
        
        self.add_btn = PushButton("Aggiungi")
        self.add_btn.setIcon(FIF.ADD)
        add_layout.addWidget(self.add_btn)
        
        layout.addLayout(add_layout)
        
        # Dialog buttons
        buttons_layout = QHBoxLayout()
        self.close_btn = PushButton("Chiudi")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Connect signals
        self.close_btn.clicked.connect(self.accept)
        self.color_btn.clicked.connect(self.select_color)
        self.add_btn.clicked.connect(self.add_status_color)
        
    def select_color(self):
        """Opens the color dialog to select a color."""
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setText(f"Colore: {self.current_color}")
            self._on_color_changed(color)
    
    def _on_color_changed(self, color):
        """Updates the current color when selected in the color dialog."""
        self.current_color = color.name()
        self.color_btn.setText(f"Colore: {self.current_color}")
        
    def add_status_color(self):
        """Adds a new status color to the table."""
        status_name = self.new_status_input.text().strip()
        if not status_name:
            try:
                InfoBar.error(
                    title="Errore",
                    content="Il nome dello stato non può essere vuoto.",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
            except Exception:
                try:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Errore", "Il nome dello stato non può essere vuoto.")
                except Exception:
                    pass
            return
        
        # Call controller method to add to database
        self.add_status_color_to_db(status_name, self.current_color)
        
        # Reset inputs
        self.new_status_input.clear()
        self.current_color = "#FFFFFF"
        self.color_btn.setText("Scegli colore")
        
    def add_status_color_to_db(self, status_name, color_hex):
        """
        This method will be implemented by the controller.
        It's a placeholder here.
        """
        pass
        
    def populate_table(self, status_colors):
        """
        Populates the table with status colors from the database.
        status_colors: list of (status_name, color_hex) tuples
        """
        self.table.setRowCount(0)  # Clear existing rows
        
        for status_name, color_hex in status_colors:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Status name
            status_item = QTableWidgetItem(status_name)
            self.table.setItem(row, 0, status_item)
            
            # Color preview
            color_label = QLabel()
            color_label.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #333;")
            color_label.setMinimumSize(30, 20)
            self.table.setCellWidget(row, 1, color_label)
            
            # Actions layout
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)
            
            # Edit button
            edit_btn = TransparentToolButton()
            edit_btn.setIcon(FIF.EDIT)
            edit_btn.setToolTip("Modifica colore")
            edit_btn.clicked.connect(lambda _, name=status_name, color=color_hex, r=row: self.edit_status_color(name, color, r))
            actions_layout.addWidget(edit_btn)
            
            # Delete button
            delete_btn = TransparentToolButton()
            delete_btn.setIcon(FIF.DELETE)
            delete_btn.setToolTip("Elimina")
            delete_btn.clicked.connect(lambda _, name=status_name: self.delete_status_color(name))
            actions_layout.addWidget(delete_btn)
            
            # Create a widget to hold the buttons
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 2, actions_widget)
            
            # Empty column for spacing
            empty_item = QTableWidgetItem("")
            self.table.setItem(row, 3, empty_item)
            
    def edit_status_color(self, status_name, current_color, row):
        """Opens the color dialog to edit an existing status color."""
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        
        self.editing_status = status_name
        self.editing_row = row
        
        # Converti il colore corrente in QColor
        initial_color = QColor(current_color)
        
        color = QColorDialog.getColor(initial_color)
        if color.isValid():
            new_color_hex = color.name()
            
            # Aggiorna immediatamente la preview
            color_label = QLabel()
            color_label.setStyleSheet(f"background-color: {new_color_hex}; border: 1px solid #333;")
            color_label.setMinimumSize(30, 20)
            self.table.setCellWidget(self.editing_row, 1, color_label)
            
            # Salva nel database
            self.update_status_color_in_db(self.editing_status, new_color_hex)
        
        # Clean up
        if hasattr(self, 'editing_status'):
            delattr(self, 'editing_status')
        if hasattr(self, 'editing_row'):
            delattr(self, 'editing_row')
    
    def update_status_color_in_db(self, status_name, color_hex):
        """
        This method will be implemented by the controller.
        It's a placeholder here.
        """
        pass

    def showEvent(self, event):
        super().showEvent(event)