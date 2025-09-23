from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QDialog,
    QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView,
    QDialogButtonBox, QSizePolicy
)
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    PushButton, SearchLineEdit, FluentIcon as FIF
)

class NotesGridDialog(QDialog):
    """Dialog for displaying all notes in a grid with Jira key, note title, and update date."""

    def __init__(self, db_service, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.setWindowTitle("Tutte le Note")
        self.resize(1000, 600)

        # Main layout
        self.main_layout = QVBoxLayout(self)

        # Header section
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("Tutte le Note")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.refresh_btn = PushButton("Aggiorna")
        # Usa l'icona di sistema invece di FluentIcon per compatibilità
        from PyQt6.QtWidgets import QStyle
        self.refresh_btn.setIcon(self.refresh_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.setToolTip("Aggiorna la lista delle note")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addWidget(self.refresh_btn)
        self.main_layout.addLayout(self.header_layout)

        # Description
        self.description_label = QLabel("Mostra tutte le note salvate ordinate per data di aggiornamento.")
        self.main_layout.addWidget(self.description_label)

        # Search section
        self.search_layout = QHBoxLayout()
        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Cerca per chiave Jira, titolo o contenuto")
        self.search_box.setToolTip("Filtra le note per chiave Jira, titolo o contenuto")
        self.search_layout.addWidget(self.search_box)
        self.main_layout.addLayout(self.search_layout)

        # Table section
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Jira Key", "Titolo Nota", "Data Aggiornamento"])
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Jira Key
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Date
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.main_layout.addWidget(self.table)

        # Status/error message section
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("color: red;")
        self.main_layout.addWidget(self.status_label)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )

        # Connect signals
        self.button_box.rejected.connect(self.accept)
        self.refresh_btn.clicked.connect(self.load_notes)
        self.search_box.textChanged.connect(self._filter_notes)

        # Add button box to layout
        self.main_layout.addWidget(self.button_box)

        # Load initial data
        self.load_notes()

    def load_notes(self):
        """Load all notes from the database."""
        try:
            self.table.setRowCount(0)
            notes = self.db_service.get_all_annotations()

            if not notes:
                self.show_info("Nessuna nota trovata.")
                return

            for jira_key, title, updated_at in notes:
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)

                # Jira Key
                key_item = QTableWidgetItem(jira_key)
                self.table.setItem(row_position, 0, key_item)

                # Note Title
                title_item = QTableWidgetItem(title)
                self.table.setItem(row_position, 1, title_item)

                # Update Date (format it nicely)
                try:
                    from datetime import datetime
                    # Parse the datetime string and format it
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    formatted_date = updated_at

                date_item = QTableWidgetItem(formatted_date)
                self.table.setItem(row_position, 2, date_item)

            self.hide_status()

        except Exception as e:
            self.show_error(f"Errore nel caricamento delle note: {str(e)}")

    def _filter_notes(self, text: str):
        """Filter notes based on search text."""
        search_term = text.lower()
        for row in range(self.table.rowCount()):
            jira_key = self.table.item(row, 0).text().lower()
            title = self.table.item(row, 1).text().lower()

            # Check if search term is in jira key or title
            should_show = (search_term in jira_key) or (search_term in title)

            self.table.setRowHidden(row, not should_show)

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

    def showEvent(self, event):
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(self)
        except Exception:
            pass

        super().showEvent(event)