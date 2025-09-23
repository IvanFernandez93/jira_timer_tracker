from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QDialog,
    QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView,
    QDialogButtonBox, QSizePolicy
)
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    PushButton, SearchLineEdit, FluentIcon as FIF
)

class NotesLoaderWorker(QThread):
    """Worker thread for loading notes asynchronously."""
    
    notes_loaded = pyqtSignal(list)  # List of note tuples (jira_key, title, updated_at)
    notes_error = pyqtSignal(str)    # Error message
    
    def __init__(self, db_service):
        super().__init__()
        self.db_service = db_service
        self.is_cancelled = False
        self.setObjectName("NotesLoaderWorker")
    
    def cancel(self):
        """Cancel the notes loading."""
        self.is_cancelled = True
    
    def run(self):
        """Load all notes from the database."""
        try:
            if self.is_cancelled:
                return
            
            # Load notes from database
            notes = self.db_service.get_all_annotations()
            
            if not self.is_cancelled:
                self.notes_loaded.emit(notes)
            
        except Exception as e:
            if not self.is_cancelled:
                self.notes_error.emit(str(e))

class NotesGridDialog(QDialog):
    """Dialog for displaying all notes in a grid with Jira key, note title, and update date."""
    
    # Segnali per richiedere l'apertura del dettaglio o l'avvio del timer di un ticket Jira
    open_jira_detail_requested = pyqtSignal(str)  # Emette la chiave Jira
    start_timer_requested = pyqtSignal(str)  # Emette la chiave Jira per avviare il timer
    
    def __init__(self, db_service, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.notes_loader_worker = None
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
        self.table = QTableWidget(0, 4)  # Aggiungiamo una colonna per il pulsante di dettaglio
        self.table.setHorizontalHeaderLabels(["Jira Key", "Titolo Nota", "Data Aggiornamento", "Azioni"])
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Jira Key
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Date
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Actions
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

        # Start async loading
        self._start_async_notes_loading()

    def _start_async_notes_loading(self):
        """Start asynchronous loading of notes with loading indicator."""
        # Show loading indicator
        self.table.setRowCount(0)
        self.table.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.search_box.setEnabled(False)
        
        # Add loading row
        self.table.insertRow(0)
        loading_item = QTableWidgetItem("Caricamento note...")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 0, loading_item)
        self.table.setSpan(0, 0, 1, 4)  # Span across all columns        # Cancel any existing loader
        if self.notes_loader_worker:
            self.notes_loader_worker.cancel()
            self.notes_loader_worker.wait()
        
        # Start new loader
        self.notes_loader_worker = NotesLoaderWorker(self.db_service)
        self.notes_loader_worker.notes_loaded.connect(self._on_notes_loaded)
        self.notes_loader_worker.notes_error.connect(self._on_notes_error)
        self.notes_loader_worker.start()

    def _on_notes_loaded(self, notes):
        """Handle successful loading of notes."""
        try:
            # Clear loading indicator
            self.table.clearContents()
            self.table.setRowCount(0)
            self.table.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.search_box.setEnabled(True)
            
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

                # Update Date (format it nicely and convert from UTC to local time)
                try:
                    from datetime import datetime
                    
                    # Parse the UTC datetime
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    
                    # Convert to local time
                    local_dt = dt.astimezone()  # Senza argomenti, astimezone converte al fuso orario locale
                    
                    # Format for display with local timezone
                    formatted_date = local_dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    formatted_date = updated_at

                date_item = QTableWidgetItem(formatted_date)
                self.table.setItem(row_position, 2, date_item)
                
                # Action Buttons (Detail View and Start Timer)
                from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout
                action_cell_widget = QWidget()
                action_layout = QHBoxLayout(action_cell_widget)
                action_layout.setContentsMargins(4, 2, 4, 2)
                action_layout.setSpacing(4)
                
                # Create detail button with icon
                detail_btn = PushButton()
                detail_btn.setIcon(FIF.LINK)
                detail_btn.setToolTip(f"Apri dettaglio ticket {jira_key}")
                detail_btn.setFixedSize(32, 32)
                detail_btn.clicked.connect(lambda checked=False, key=jira_key: self._open_detail_view(key))
                action_layout.addWidget(detail_btn)
                
                # Create timer button with icon
                timer_btn = PushButton()
                timer_btn.setIcon(FIF.CLOCK)
                timer_btn.setToolTip(f"Avvia timer per {jira_key}")
                timer_btn.setFixedSize(32, 32)
                timer_btn.clicked.connect(lambda checked=False, key=jira_key: self._start_timer(key))
                action_layout.addWidget(timer_btn)
                
                self.table.setCellWidget(row_position, 3, action_cell_widget)

            self.hide_status()

        except Exception as e:
            self._on_notes_error(f"Errore nella costruzione della tabella: {str(e)}")

    def _on_notes_error(self, error_message):
        """Handle error loading notes."""
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.search_box.setEnabled(True)
        
        # Add error row
        self.table.insertRow(0)
        error_item = QTableWidgetItem(f"Errore: {error_message}")
        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 0, error_item)
        self.table.setSpan(0, 0, 1, 4)  # Span across all columns

    def load_notes(self):
        """Start async loading of notes."""
        self._start_async_notes_loading()

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

    def _open_detail_view(self, jira_key):
        """Opens the detail view for the given Jira key."""
        if jira_key:
            # Emettiamo il segnale per richiedere l'apertura della vista di dettaglio
            self.open_jira_detail_requested.emit(jira_key)
            
    def _start_timer(self, jira_key):
        """Avvia il timer per la chiave Jira specificata."""
        if jira_key:
            # Emettiamo il segnale per richiedere l'avvio del timer
            self.start_timer_requested.emit(jira_key)
    
    def closeEvent(self, event):
        """Handle dialog closing by cancelling any active workers."""
        # Cancel notes loader if active
        if self.notes_loader_worker:
            self.notes_loader_worker.cancel()
            # Wait briefly for the worker to finish
            if not self.notes_loader_worker.wait(3000):  # 3 second timeout
                self.notes_loader_worker.terminate()
                self.notes_loader_worker.wait(1000)
        
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)