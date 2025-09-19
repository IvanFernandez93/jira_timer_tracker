from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy,
    QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView
)
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    PushButton, LineEdit, SearchLineEdit, FluentIcon as FIF
)

class HistoryView(QWidget):
    """A view that displays the last 100 Jira issues viewed."""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("history_view")
        # Columns configuration for history grid
        self.columns_config = [
            {"id": "key", "label": "Jira Key", "visible": True, "sortable": True},
            {"id": "title", "label": "Titolo", "visible": True, "sortable": True},
            {"id": "last_access", "label": "Ultimo Accesso", "visible": True, "sortable": True},
            {"id": "actions", "label": "Azioni", "visible": True, "sortable": False},
        ]
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header section
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("Cronologia Visualizzazioni")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.refresh_btn = PushButton("Aggiorna")
        # Usa l'icona di sistema invece di FluentIcon per compatibilità
        from PyQt6.QtWidgets import QStyle
        self.refresh_btn.setIcon(self.refresh_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.setToolTip("Aggiorna la lista della cronologia")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addWidget(self.refresh_btn)
        self.main_layout.addLayout(self.header_layout)
        
        # Description
        self.description_label = QLabel("Mostra gli ultimi 100 ticket visualizzati in ordine cronologico.")
        self.main_layout.addWidget(self.description_label)
        
        # Search section
        self.search_layout = QHBoxLayout()
        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Cerca per chiave o descrizione")
        self.search_box.setToolTip("Filtra la cronologia per chiave o descrizione")
        self.search_layout.addWidget(self.search_box)
        self.main_layout.addLayout(self.search_layout)
        
        # Table section
        self.table = QTableWidget(0, len([c for c in self.columns_config if c.get('visible', True)]))
        self.table.setHorizontalHeaderLabels([c.get('label') for c in self.columns_config if c.get('visible', True)])
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Fixed width for actions column
        self.table.setColumnWidth(3, 40)  # Set fixed width for actions column to fit button
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.main_layout.addWidget(self.table)
        
        # Status/error message section
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("color: red;")
        self.main_layout.addWidget(self.status_label)
        
    def clear_table(self):
        """Clears the table content."""
        self.table.setRowCount(0)

    def set_app_settings(self, app_settings):
        """Load columns config from app settings if present."""
        try:
            import json
            saved = app_settings.get_setting('history_grid_columns', None)
            if saved:
                self.columns_config = json.loads(saved)
                # Rebuild table headers
                visible = [c for c in self.columns_config if c.get('visible', True)]
                self.table.setColumnCount(len(visible))
                self.table.setHorizontalHeaderLabels([c.get('label') for c in visible])
        except Exception:
            pass
        
    def show_error(self, message):
        """Shows an error message."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setVisible(True)
        
    def show_info(self, message):
        """Shows an info message."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: green;")
        self.status_label.setVisible(True)
        
    def hide_status(self):
        """Hides the status message."""
        self.status_label.setVisible(False)