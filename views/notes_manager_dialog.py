from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QDialog,
    QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView,
    QDialogButtonBox, QLineEdit, QTextEdit, QPushButton, QComboBox,
    QMessageBox, QSplitter, QListWidget, QListWidgetItem, QCheckBox,
    QGroupBox, QFormLayout, QInputDialog, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont
from qfluentwidgets import (
    PushButton, SearchLineEdit, FluentIcon as FIF, PrimaryPushButton,
    ToolButton, ComboBox
)
from datetime import datetime
from typing import Dict, Optional
import json
import logging

from views.markdown_editor import MarkdownEditor
from services.note_manager import NoteManager, NoteData, NoteState

logger = logging.getLogger(__name__)

class SortableTableItem(QTableWidgetItem):
    """Item personalizzato per il QTableWidget che supporta l'ordinamento corretto dei tipi di dati."""
    
    def __init__(self, text="", sort_key=None):
        super().__init__(text)
        self._sort_key = sort_key
        
    def __lt__(self, other):
        """Metodo di confronto per l'ordinamento personalizzato."""
        if self._sort_key is not None and hasattr(other, '_sort_key') and other._sort_key is not None:
            return self._sort_key < other._sort_key
        return super().__lt__(other)

class NotesManagerDialog(QDialog):
    """Dialog for complete notes management with CRUD operations, tags, and soft delete."""
    
    # Segnali per richiedere l'apertura di altre viste
    all_notes_requested = pyqtSignal()
    open_jira_detail_requested = pyqtSignal(str)  # Emette la chiave Jira
    start_timer_requested = pyqtSignal(str)  # Emette la chiave Jira per avviare il timer

    def __init__(self, db_service, app_settings, jira_service=None, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.app_settings = app_settings
        self.jira_service = jira_service
        
        # Initialize advanced note management system
        from services.git_service import GitService
        self.git_service = GitService()
        self.note_manager = NoteManager(self.db_service, self.git_service)
        
        # Current state tracking
        self.current_note_id = None
        self.current_note_state: Optional[NoteState] = None
        self.show_deleted = False
        
        # Connect note manager signals
        self.note_manager.note_state_changed.connect(self._on_note_state_changed)
        self.note_manager.note_saved.connect(self._on_note_saved)
        self.note_manager.note_error.connect(self._on_note_error)
        
        # Performance optimization: content change detection
        self._last_content_hash = None
        self._content_changed = False

        self.setWindowTitle("Gestione Note")
        # Use non-destructive method to add maximize button
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        # Ensure dialog is not modal and can stay open when main gets focus
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.setModal(False)
        self.resize(1200, 800)

        # Main layout with splitter
        self.main_layout = QVBoxLayout(self)

        # Header section
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("Gestione Note")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Header buttons
        self.new_btn = PrimaryPushButton("Nuova Nota")
        self.new_btn.setIcon(FIF.ADD)
        self.refresh_btn = PushButton("Aggiorna")
        self.refresh_btn.setIcon(FIF.UPDATE)
        self.all_notes_btn = PushButton("Tutte le Note")
        self.all_notes_btn.setIcon(FIF.LIST)

        self.header_layout.addWidget(self.title_label)
        self.header_layout.addWidget(self.new_btn)
        self.header_layout.addWidget(self.refresh_btn)
        self.header_layout.addWidget(self.all_notes_btn)
        self.main_layout.addLayout(self.header_layout)

        # Create splitter for main content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # Left panel - Notes list
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        # Search and filters
        self.search_layout = QHBoxLayout()
        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Cerca per titolo, contenuto o chiave Jira")
        self.search_box.setToolTip("Filtra le note per titolo, contenuto o chiave Jira")

        self.tag_filter_combo = ComboBox()
        self.tag_filter_combo.addItem("Tutti i tag", "")
        self.tag_filter_combo.setToolTip("Filtra per tag")

        self.show_deleted_cb = QCheckBox("Mostra note eliminate")
        self.show_deleted_cb.setChecked(self.show_deleted)

        self.search_layout.addWidget(self.search_box)
        self.search_layout.addWidget(self.tag_filter_combo)
        self.search_layout.addWidget(self.show_deleted_cb)
        self.left_layout.addLayout(self.search_layout)

        # Notes table
        self.notes_table = QTableWidget(0, 4)
        self.notes_table.setHorizontalHeaderLabels(["Titolo", "Jira Key", "Tag", "Aggiornato"])
        self.notes_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.notes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        self.notes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Jira Key
        self.notes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Tags
        self.notes_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Updated
        self.notes_table.setAlternatingRowColors(True)
        self.notes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.notes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Abilita l'ordinamento delle colonne
        self.notes_table.setSortingEnabled(True)
        # Ordina per default per data di aggiornamento decrescente (più recenti prima)
        self.notes_table.horizontalHeader().setSortIndicator(3, Qt.SortOrder.DescendingOrder)
        self.left_layout.addWidget(self.notes_table)

        # Right panel - Note editor
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)

        # Note editor header
        self.editor_header = QGroupBox("Editor Nota")
        self.editor_header_layout = QVBoxLayout(self.editor_header)

        # Note form
        self.form_layout = QFormLayout()

        # Jira Key con pulsanti per aprire dettaglio e avviare timer
        jira_key_layout = QHBoxLayout()
        self.jira_key_edit = QLineEdit()
        self.jira_key_edit.setPlaceholderText("Opzionale - lascia vuoto per nota generale")
        self.jira_key_edit.setToolTip("Chiave Jira associata alla nota (opzionale)")
        jira_key_layout.addWidget(self.jira_key_edit)
        
        # Pulsante per aprire il dettaglio della Jira
        self.open_jira_btn = PushButton()
        self.open_jira_btn.setIcon(FIF.LINK)
        self.open_jira_btn.setToolTip("Apri dettaglio del ticket Jira")
        self.open_jira_btn.setFixedSize(32, 32)
        self.open_jira_btn.clicked.connect(self._open_jira_detail)
        self.open_jira_btn.setEnabled(False)  # Disabilitato finché non c'è una Jira valida
        jira_key_layout.addWidget(self.open_jira_btn)
        
        # Pulsante per avviare il timer per la Jira
        self.start_timer_btn = PushButton()
        self.start_timer_btn.setIcon(FIF.CLOCK)
        self.start_timer_btn.setToolTip("Avvia timer per questo ticket")
        self.start_timer_btn.setFixedSize(32, 32)
        self.start_timer_btn.clicked.connect(self._start_timer)
        self.start_timer_btn.setEnabled(False)  # Disabilitato finché non c'è una Jira valida
        jira_key_layout.addWidget(self.start_timer_btn)
        
        self.form_layout.addRow("Jira Key:", jira_key_layout)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Titolo della nota")
        self.title_edit.setToolTip("Titolo della nota")
        self.form_layout.addRow("Titolo:", self.title_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("tag1, tag2, tag3")
        self.tags_edit.setToolTip("Tag separati da virgola")
        self.form_layout.addRow("Tag:", self.tags_edit)

        self.fictitious_cb = QCheckBox("Ticket fittizio")
        self.fictitious_cb.setToolTip("Segna questo ticket come fittizio (non verrà verificato su Jira)")
        self.form_layout.addRow("", self.fictitious_cb)

        self.editor_header_layout.addLayout(self.form_layout)

        # Content editor
        self.content_label = QLabel("Contenuto:")
        self.editor_header_layout.addWidget(self.content_label)

        self.content_edit = MarkdownEditor(show_toolbar=True)
        self.content_edit.setPlaceholderText("Contenuto della nota (Markdown supportato)...")
        self.content_edit.setMinimumHeight(200)
        
        # Connect to optimized change detection
        self.content_edit.textChanged.connect(self._on_content_changed_optimized)
        
        self.editor_header_layout.addWidget(self.content_edit)

        # Status information layout
        self.status_layout = QHBoxLayout()
        
        # Draft status label
        self.draft_status_label = QLabel("📝 BOZZA")
        self.draft_status_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
        self.status_layout.addWidget(self.draft_status_label)
        
        # Commit status label  
        self.commit_status_label = QLabel("Nuova bozza")
        self.commit_status_label.setStyleSheet("QLabel { color: gray; }")
        self.status_layout.addWidget(self.commit_status_label)
        
        # Save status labels
        self.save_status_label = QLabel("Mai salvato")
        self.save_status_label.setStyleSheet("color: gray; font-size: 11px;")
        self.status_layout.addWidget(self.save_status_label)
        
        self.draft_status_label = QLabel("")
        self.draft_status_label.setStyleSheet("color: orange; font-size: 11px;")
        self.status_layout.addWidget(self.draft_status_label)
        
        self.status_layout.addStretch()
        
        self.editor_header_layout.addLayout(self.status_layout)

        # Action buttons
        self.actions_layout = QHBoxLayout()

        self.save_btn = PrimaryPushButton("Salva bozza")
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Salva come bozza (modificabile)")

        self.commit_btn = PushButton("Commit")
        self.commit_btn.setIcon(FIF.ACCEPT)
        self.commit_btn.setEnabled(False)
        self.commit_btn.setToolTip("Commit definitivo (readonly)")

        self.delete_btn = PushButton("Elimina")
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.setEnabled(False)

        self.restore_btn = PushButton("Ripristina")
        self.restore_btn.setIcon(FIF.RETURN)
        self.restore_btn.setEnabled(False)
        self.restore_btn.setVisible(False)

        self.actions_layout.addWidget(self.save_btn)
        self.actions_layout.addWidget(self.commit_btn)
        self.actions_layout.addWidget(self.delete_btn)
        self.actions_layout.addWidget(self.restore_btn)
        self.actions_layout.addStretch()

        self.editor_header_layout.addLayout(self.actions_layout)

        # Info section
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 10px; color: gray;")
        self.editor_header_layout.addWidget(self.info_label)

        self.right_layout.addWidget(self.editor_header)

        # Add panels to splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([600, 600])

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        self.main_layout.addWidget(self.button_box)

        # Connect signals
        self.button_box.rejected.connect(self.accept)
        self.new_btn.clicked.connect(self.create_new_note)
        self.refresh_btn.clicked.connect(self.refresh_notes)
        self.all_notes_btn.clicked.connect(self.show_all_notes_grid)
        self.search_box.textChanged.connect(self.apply_filters)
        self.tag_filter_combo.currentIndexChanged.connect(self.apply_filters)
        self.show_deleted_cb.toggled.connect(self.on_show_deleted_toggled)
        self.notes_table.itemSelectionChanged.connect(self.on_note_selected)
        self.notes_table.doubleClicked.connect(self._on_table_double_clicked)
        self.save_btn.clicked.connect(self._handle_save_action)
        self.commit_btn.clicked.connect(self._handle_commit_action)
        self.delete_btn.clicked.connect(self.delete_note)
        self.restore_btn.clicked.connect(self.restore_note)
        self.title_edit.textChanged.connect(self.on_content_changed)
        self.content_edit.textChanged.connect(self.on_content_changed)
        self.tags_edit.textChanged.connect(self.on_content_changed)
        self.jira_key_edit.textChanged.connect(self._on_jira_key_changed)

        # Load initial data
        self.load_tags()
        self.load_notes()

    def load_tags(self):
        """Load all available tags for the filter combo."""
        try:
            tags = self.db_service.get_all_tags()
            self.tag_filter_combo.clear()
            self.tag_filter_combo.addItem("Tutti i tag", "")

            for tag in tags:
                self.tag_filter_combo.addItem(tag, tag)
        except Exception as e:
            print(f"Error loading tags: {e}")

    def load_notes(self):
        """Load all notes from database."""
        try:
            # Disattiva temporaneamente l'ordinamento durante il caricamento
            current_sort_column = self.notes_table.horizontalHeader().sortIndicatorSection()
            current_sort_order = self.notes_table.horizontalHeader().sortIndicatorOrder()
            self.notes_table.setSortingEnabled(False)
            
            notes = self.db_service.get_all_notes(include_deleted=self.show_deleted)
            self.notes_table.setRowCount(0)

            for note in notes:
                row_position = self.notes_table.rowCount()
                self.notes_table.insertRow(row_position)

                # Title - Ordinabile normalmente come testo
                title_item = QTableWidgetItem(note['title'])
                title_item.setData(Qt.ItemDataRole.UserRole, note['id'])  # Store note ID
                if note['is_deleted']:
                    title_item.setForeground(Qt.GlobalColor.gray)
                    font = title_item.font()
                    font.setStrikeOut(True)
                    title_item.setFont(font)
                self.notes_table.setItem(row_position, 0, title_item)

                # Jira Key - Ordinabile normalmente come testo
                jira_item = QTableWidgetItem(note['jira_key'] or "")
                if note['is_deleted']:
                    jira_item.setForeground(Qt.GlobalColor.gray)
                self.notes_table.setItem(row_position, 1, jira_item)

                # Tags - Ordinabile normalmente come testo
                tags_item = QTableWidgetItem(note['tags'])
                if note['is_deleted']:
                    tags_item.setForeground(Qt.GlobalColor.gray)
                self.notes_table.setItem(row_position, 2, tags_item)

                # Updated date - Ordinabile cronologicamente
                try:
                    from datetime import datetime
                    # Ottiene il timestamp UTC
                    dt_utc = datetime.fromisoformat(note['updated_at'].replace('Z', '+00:00'))
                    
                    # Converte a fuso orario locale
                    dt_local = dt_utc.astimezone()  # Senza argomenti, astimezone converte al fuso locale
                    
                    formatted_date = dt_local.strftime("%d/%m/%Y %H:%M")
                    
                    # Utilizziamo SortableTableItem per l'ordinamento corretto delle date
                    date_item = SortableTableItem(formatted_date, dt_local.timestamp())
                except Exception:
                    formatted_date = note['updated_at'] or ""
                    date_item = QTableWidgetItem(formatted_date)
                
                if note['is_deleted']:
                    date_item.setForeground(Qt.GlobalColor.gray)
                self.notes_table.setItem(row_position, 3, date_item)
                
            # Riattiva l'ordinamento e ripristina l'indicatore precedente
            self.notes_table.setSortingEnabled(True)
            self.notes_table.horizontalHeader().setSortIndicator(current_sort_column, current_sort_order)

        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel caricamento delle note: {str(e)}")

    def refresh_notes(self):
        """Refresh notes list and tags while maintaining current filters."""
        # Store current filter selections
        current_tag_filter = self.tag_filter_combo.currentData()
        
        # Reload data
        self.load_tags()  # Refresh tags in case new ones were added
        self.load_notes()
        
        # Restore tag filter selection if it still exists
        if current_tag_filter:
            for i in range(self.tag_filter_combo.count()):
                if self.tag_filter_combo.itemData(i) == current_tag_filter:
                    self.tag_filter_combo.setCurrentIndex(i)
                    break
        
        self.apply_filters()  # Apply current filters after reloading

    def apply_filters(self):
        """Apply search and tag filters to the notes table."""
        search_term = self.search_box.text().lower()
        selected_tag = self.tag_filter_combo.currentData()

        for row in range(self.notes_table.rowCount()):
            title = self.notes_table.item(row, 0).text().lower()
            jira_key = self.notes_table.item(row, 1).text().lower()
            tags = self.notes_table.item(row, 2).text().lower()

            # Search filter
            search_match = (search_term in title) or (search_term in jira_key) or (search_term in tags)

            # Tag filter
            tag_match = (not selected_tag) or (selected_tag in tags)

            # Show/hide row
            self.notes_table.setRowHidden(row, not (search_match and tag_match))

    def on_show_deleted_toggled(self, checked):
        """Handle show deleted notes toggle."""
        self.show_deleted = checked
        self.load_notes()
        self.apply_filters()  # Apply filters after reloading

    def create_new_note(self):
        """Create a new note."""
        self.current_note_id = None
        self.clear_editor()
        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.restore_btn.setVisible(False)
        self.title_edit.setFocus()

    def clear_editor(self):
        """Clear the note editor."""
        self.jira_key_edit.clear()
        self.title_edit.clear()
        self.tags_edit.clear()
        self.fictitious_cb.setChecked(False)
        self.content_edit.setMarkdown("")
        self.info_label.clear()

    def on_note_selected(self):
        """Handle note selection in the table."""
        selected_items = self.notes_table.selectedItems()
        if not selected_items:
            return

        # Get note ID from the first column of selected row
        row = selected_items[0].row()
        title_item = self.notes_table.item(row, 0)
        note_id = title_item.data(Qt.ItemDataRole.UserRole)

        if note_id:
            self.load_note_in_editor(note_id)

    def load_note_in_editor(self, note_id):
        """Load a note into the editor using optimized note manager."""
        try:
            # Stop any ongoing auto-save
            self.note_manager.stop_auto_save()
            
            # Use note manager to load note with state management
            success, note, state = self.note_manager.load_note(note_id)
            
            if not success or not note or not state:
                logger.warning(f"Failed to load note {note_id}")
                return

            # Update UI with note data
            self.current_note_id = note_id
            self.jira_key_edit.setText(note.get('jira_key', ''))
            self.title_edit.setText(note.get('title', ''))
            self.tags_edit.setText(note.get('tags', ''))
            self.fictitious_cb.setChecked(note.get('is_fictitious', False))
            
            # Set content and calculate hash for change detection
            content = note.get('content', '')
            self.content_edit.setMarkdown(content)
            self._last_content_hash = hash(content)
            self._content_changed = False

            # Update JIRA-related button states
            has_jira = bool(note.get('jira_key'))
            self.open_jira_btn.setEnabled(has_jira)
            self.start_timer_btn.setEnabled(has_jira)
            
            # State is automatically handled by note manager callbacks
            # Update status and info labels
            self._update_status_labels(note)

            # Update info label
            try:
                # Converti tutte le date da UTC a fuso orario locale
                created_dt = datetime.fromisoformat(note['created_at'].replace('Z', '+00:00')).astimezone()
                updated_dt = datetime.fromisoformat(note['updated_at'].replace('Z', '+00:00')).astimezone()
                created_str = created_dt.strftime("%d/%m/%Y %H:%M")
                updated_str = updated_dt.strftime("%d/%m/%Y %H:%M")

                if note['is_deleted']:
                    deleted_dt = datetime.fromisoformat(note['deleted_at'].replace('Z', '+00:00')).astimezone()
                    deleted_str = deleted_dt.strftime("%d/%m/%Y %H:%M")
                    self.info_label.setText(f"Creata: {created_str} | Aggiornata: {updated_str} | Eliminata: {deleted_str}")
                else:
                    self.info_label.setText(f"Creata: {created_str} | Aggiornata: {updated_str}")
            except:
                self.info_label.setText("")

            # Update button states
            self.save_btn.setEnabled(False)  # Will be enabled when content changes
            self.delete_btn.setEnabled(not note['is_deleted'])
            self.restore_btn.setEnabled(note['is_deleted'])
            self.restore_btn.setVisible(note['is_deleted'])

        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel caricamento della nota: {str(e)}")

    def on_content_changed(self):
        """Handle content changes in the editor."""
        if self.current_note_id is not None:
            self.save_btn.setEnabled(True)

    def save_note(self):
        """Save the current note."""
        try:
            title = self.title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "Errore", "Il titolo è obbligatorio.")
                return

            jira_key = self.jira_key_edit.text().strip() or None
            content = self.content_edit.toMarkdown()
            tags = self.tags_edit.text().strip()
            is_fictitious = self.fictitious_cb.isChecked()

            if self.current_note_id:
                # Update existing note as draft
                self.db_service.update_note(
                    self.current_note_id,
                    jira_key=jira_key,
                    title=title,
                    content=content,
                    tags=tags,
                    is_fictitious=is_fictitious,
                    is_draft=True
                )
            else:
                # Create new note as draft
                self.current_note_id = self.db_service.create_note(
                    jira_key=jira_key,
                    title=title,
                    content=content,
                    tags=tags,
                    is_fictitious=is_fictitious,
                    is_draft=True
                )

            # If jira_service is available and this is a jira key that's marked as fictitious,
            # add it to the fictitious tickets cache
            if self.jira_service and jira_key and is_fictitious:
                self.jira_service.mark_ticket_as_fictitious(jira_key)
            elif self.jira_service and jira_key and not is_fictitious:
                # If it's now marked as NOT fictitious, remove it from the cache
                self.jira_service.unmark_ticket_as_fictitious(jira_key)

            self.save_btn.setEnabled(False)
            
            # Memorizza l'ID della nota corrente prima di ricaricare
            saved_note_id = self.current_note_id
            
            # Ricarica le note e i tag
            self.load_notes()  # Refresh the list
            self.load_tags()  # Refresh tags in filter
            
            # Riseleziona la nota appena salvata nella tabella
            if saved_note_id:
                self._select_note_by_id(saved_note_id)

            QMessageBox.information(self, "Successo", "Nota salvata con successo.")

        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel salvataggio della nota: {str(e)}")

    def _on_content_changed_optimized(self):
        """Optimized content change handler with hash-based detection."""
        if not self.current_note_state or self.current_note_state.state_name == 'committed':
            return
            
        # Calculate content hash to detect actual changes
        current_content = self.content_edit.toPlainText()
        current_hash = hash(current_content)
        
        if current_hash != self._last_content_hash:
            self._last_content_hash = current_hash
            self._content_changed = True
            
            # Start auto-save for draft notes
            if self.current_note_state.state_name == 'draft':
                self.note_manager.start_auto_save()
                self._update_draft_status_label("Modifiche in corso...")
    
    def _handle_save_action(self):
        """Handle save button click using advanced note manager."""
        try:
            if not self.current_note_state:
                # Create new note
                note_data = self._collect_note_data()
                if note_data:
                    success, note_id, state = self.note_manager.create_new_note(note_data)
                    if success:
                        self.current_note_id = note_id
                        self._refresh_notes_list()
                        self._select_note_by_id(note_id)
                return
            
            if self.current_note_state.state_name == 'committed':
                # Convert to draft for editing
                success = self.note_manager.convert_to_draft(self.current_note_id)
                if success:
                    self._refresh_notes_list()
            elif self.current_note_state.state_name in ['draft', 'new']:
                # Save as draft
                note_data = self._collect_note_data()
                if note_data:
                    success = self.note_manager.save_draft(self.current_note_id, note_data)
                    if success:
                        self._refresh_notes_list()
                        
        except Exception as e:
            logger.error(f"Save action failed: {e}")
            QMessageBox.warning(self, "Errore", f"Errore durante il salvataggio: {e}")

    def _collect_note_data(self) -> Optional[NoteData]:
        """Collect note data from UI fields with validation."""
        try:
            jira_key = self.jira_key_edit.text().strip() or 'GENERAL'
            title = self.title_edit.text().strip()
            content = self.content_edit.toMarkdown()
            tags = self.tags_edit.text().strip()
            is_fictitious = self.fictitious_cb.isChecked()
            
            if not title:
                QMessageBox.warning(self, "Errore", "Il titolo è obbligatorio")
                return None
                
            return NoteData(
                jira_key=jira_key,
                title=title,
                content=content,
                tags=tags,
                is_fictitious=is_fictitious
            )
            
        except Exception as e:
            logger.error(f"Error collecting note data: {e}")
            QMessageBox.warning(self, "Errore", f"Errore nei dati: {e}")
            return None
    
    def _on_note_state_changed(self, state: NoteState):
        """Handle note state changes from the note manager."""
        self.current_note_state = state
        self._update_ui_for_state(state)
        
    def _on_note_saved(self, note_id: int, message: str):
        """Handle successful note save."""
        self._update_draft_status_label(f"✓ {message}")
        self._refresh_notes_list()
        
    def _on_note_error(self, error_message: str):
        """Handle note management errors."""
        QMessageBox.warning(self, "Errore", error_message)
        
    def _update_ui_for_state(self, state: NoteState):
        """Update UI elements based on note state."""
        if state.state_name == 'committed':
            self.content_edit.setReadOnly(True)
            self.title_edit.setReadOnly(True)
            self.jira_key_edit.setReadOnly(True)
            self.tags_edit.setReadOnly(True)
            self.fictitious_cb.setEnabled(False)
            self._update_draft_status_label("📋 COMMITTATA")
            
        elif state.state_name == 'draft':
            self.content_edit.setReadOnly(False)
            self.title_edit.setReadOnly(False)
            self.jira_key_edit.setReadOnly(False)
            self.tags_edit.setReadOnly(False)
            self.fictitious_cb.setEnabled(True)
            self._update_draft_status_label("📝 BOZZA")
            
        else:  # new
            self.content_edit.setReadOnly(False)
            self.title_edit.setReadOnly(False)
            self.jira_key_edit.setReadOnly(False)
            self.tags_edit.setReadOnly(False)
            self.fictitious_cb.setEnabled(True)
            self._update_draft_status_label("✨ NUOVA")
            now = datetime.now().strftime("%H:%M:%S")
            self._update_draft_status_label(f"💾 Bozza salvata alle {now}")
                
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel salvare la bozza: {e}")

    def _convert_to_draft(self):
        """Convert a committed note back to draft mode for editing."""
        if not self.current_note_id:
            return
            
        reply = QMessageBox.question(
            self, 
            "Modifica Nota",
            "Convertire la nota in bozza per modificarla?\n"
            "La nota tornerà in modalità editing e dovrà essere ri-committata.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Convert to draft in database
                from datetime import datetime, timezone
                current_time = datetime.now(timezone.utc).isoformat()
                
                conn = self.db_service.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE Annotations SET IsDraft = 1, DraftSavedAt = ?, UpdatedAt = ? WHERE Id = ?',
                    (current_time, current_time, self.current_note_id)
                )
                conn.commit()
                conn.close()
                
                # Refresh UI
                self.load_note_in_editor(self.current_note_id)
                
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore nella conversione: {e}")
    
    def _handle_commit_action(self):
        """Handle commit button click using advanced note manager."""
        try:
            if not self.current_note_state:
                return
                
            if self.current_note_state.state_name == 'committed':
                # Show git history
                self._show_git_history()
            elif self.current_note_state.state_name == 'draft':
                # Commit the note
                self._commit_note_advanced()
                
        except Exception as e:
            logger.error(f"Commit action failed: {e}")
            QMessageBox.warning(self, "Errore", f"Errore durante il commit: {e}")

    def _commit_note_advanced(self):
        """Commit current note using advanced note manager."""
        try:
            if not self.current_note_id:
                return
                
            # Save any pending changes first
            if self._content_changed:
                note_data = self._collect_note_data()
                if note_data:
                    success = self.note_manager.save_draft(self.current_note_id, note_data)
                    if not success:
                        return
                        
            # Get commit message from user
            from PyQt6.QtWidgets import QInputDialog
            commit_message, ok = QInputDialog.getText(
                self, 
                "Commit Note", 
                "Inserisci il messaggio di commit:",
                text="Update note content"
            )
            
            if not ok or not commit_message.strip():
                return
                
            # Use note manager to commit
            success = self.note_manager.commit_note(self.current_note_id, commit_message.strip())
            
            if success:
                self._refresh_notes_list()
                
        except Exception as e:
            logger.error(f"Advanced commit failed: {e}")
            QMessageBox.warning(self, "Errore", f"Errore nel commit: {e}")
                
            # Save current state as draft first
            self._save_draft()
            
            # Get note data
            note = self.db_service.get_note_by_id(self.current_note_id)
            if not note:
                return
            
            # Prepare metadata for git
            metadata = {
                'jira_key': note['jira_key'],
                'title': note['title'],
                'tags': note['tags'],
                'created_at': note['created_at'],
                'is_fictitious': note['is_fictitious']
            }
            
            # Commit to git
            commit_hash = self.git_service.commit_note(
                note['jira_key'] or 'GENERAL',
                note['title'],
                note['content'],
                metadata,
                commit_message
            )
            
            if commit_hash:
                # Mark as committed in database
                self.db_service.commit_note(self.current_note_id, commit_hash)
                
                # Refresh the note display
                self.load_note_in_editor(self.current_note_id)
                QMessageBox.information(self, "Successo", f"Nota committata con successo!\nHash: {commit_hash[:8]}")
            else:
                QMessageBox.warning(self, "Errore", "Errore nel committare la nota")
                
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel commit: {e}")
            
    def _show_git_history(self):
        """Show git history for the current note."""
        if not self.current_note_id:
            return
            
        try:
            note = self.db_service.get_note_by_id(self.current_note_id)
            if not note or not note['jira_key'] or not note['title']:
                QMessageBox.information(self, "Info", "Nessuna storia git disponibile per questa nota")
                return
                
            history = self.git_service.get_note_history(note['jira_key'], note['title'])
            
            if not history:
                QMessageBox.information(self, "Info", "Nessuna storia git trovata per questa nota")
                return
                
            # Create history dialog
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Storia Git: {note['title']}")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            
            # Format history
            history_text = f"📚 Storia Git per '{note['title']}'\n"
            history_text += "=" * 50 + "\n\n"
            
            for i, entry in enumerate(history):
                history_text += f"🔸 Commit {i+1}: {entry['hash'][:8]}\n"
                history_text += f"📅 Data: {entry['date']}\n" 
                history_text += f"💬 Messaggio: {entry['message']}\n"
                history_text += "-" * 40 + "\n\n"
                
            text_edit.setPlainText(history_text)
            layout.addWidget(text_edit)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel visualizzare la storia: {e}")
    
    def _update_save_status_label(self, text: str):
        """Update the save status label."""
        self.save_status_label.setText(text)
    
    def _update_draft_status_label(self, text: str):
        """Update the draft status label."""
        self.draft_status_label.setText(text)
        
    def _set_note_editing_mode(self, note_state: str):
        """
        Set note editing mode based on state: 'draft', 'committed', 'new'
        
        DRAFT MODE: 🟠 Editable content, Save Draft + Commit available
        COMMITTED MODE: 🟢 Readonly content, Edit + Commit + Delete available  
        NEW MODE: 🆕 Editable content, Save Draft available
        """
        self.current_note_state = note_state
        
        if note_state == 'draft':
            # DRAFT: Content editable, can save draft or commit
            self.content_edit.setReadOnly(False)
            self.jira_key_edit.setReadOnly(False)
            self.title_edit.setReadOnly(False) 
            self.tags_edit.setReadOnly(False)
            
            # Button visibility
            self.save_btn.setVisible(True)
            self.save_btn.setText("💾 Salva Bozza")
            self.save_btn.setToolTip("Salva modifiche come bozza")
            
            self.commit_btn.setVisible(True)
            self.commit_btn.setText("✅ Commit")
            self.commit_btn.setToolTip("Committa la nota (readonly)")
            
            self.delete_btn.setVisible(True)
            self.delete_btn.setEnabled(True)
            
            # UI styling - normal editing
            self._apply_editing_styles(False)
            
        elif note_state == 'committed':
            # COMMITTED: Readonly content, can edit or delete
            self.content_edit.setReadOnly(True)
            self.jira_key_edit.setReadOnly(True) 
            self.title_edit.setReadOnly(True)
            self.tags_edit.setReadOnly(True)
            
            # Button visibility - special committed mode
            self.save_btn.setVisible(True)
            self.save_btn.setText("✏️ Modifica")  
            self.save_btn.setToolTip("Converti in bozza per modificare")
            
            self.commit_btn.setVisible(True)
            self.commit_btn.setText("📊 Storia") 
            self.commit_btn.setToolTip("Visualizza cronologia git")
            
            self.delete_btn.setVisible(True)
            self.delete_btn.setEnabled(True)
            
            # UI styling - readonly
            self._apply_editing_styles(True)
            
        elif note_state == 'new':
            # NEW: Content editable, only save as draft available
            self.content_edit.setReadOnly(False)
            self.jira_key_edit.setReadOnly(False)
            self.title_edit.setReadOnly(False)
            self.tags_edit.setReadOnly(False)
            
            # Button visibility
            self.save_btn.setVisible(True)
            self.save_btn.setText("💾 Salva Bozza")
            self.save_btn.setToolTip("Salva nuova nota come bozza")
            
            self.commit_btn.setVisible(False)  # No commit until saved as draft
            self.delete_btn.setVisible(False)  # No delete for unsaved notes
            
            # UI styling - normal editing
            self._apply_editing_styles(False)
        
        # Fictitious checkbox always remains editable (per requirements)
        self.fictitious_cb.setEnabled(True)
        
    def _apply_editing_styles(self, readonly: bool):
        """Apply visual styling based on editing mode."""
        if readonly:
            # Subtle readonly styling
            self.title_edit.setStyleSheet("QLineEdit { background-color: #f8f9fa; border: 1px solid #dee2e6; }")
            self.tags_edit.setStyleSheet("QLineEdit { background-color: #f8f9fa; border: 1px solid #dee2e6; }")
            self.content_edit.setStyleSheet("QTextEdit { background-color: #f8f9fa; border: 1px solid #dee2e6; }")
        else:
            # Normal editing styling
            self.title_edit.setStyleSheet("QLineEdit { background-color: white; border: 1px solid #ced4da; }")
            self.tags_edit.setStyleSheet("QLineEdit { background-color: white; border: 1px solid #ced4da; }")  
            self.content_edit.setStyleSheet("QTextEdit { background-color: white; border: 1px solid #ced4da; }")

    def _update_status_labels(self, note: Dict):
        """Update status labels with draft and commit information."""
        is_draft = note.get('is_draft', False)
        
        if is_draft:
            self.draft_status_label.setText("📝 BOZZA")
            self.draft_status_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
            
            # Show draft saved time
            draft_saved_at = note.get('draft_saved_at')
            if draft_saved_at:
                try:
                    draft_dt = datetime.fromisoformat(draft_saved_at.replace('Z', '+00:00')).astimezone()
                    draft_str = draft_dt.strftime("%d/%m/%Y %H:%M:%S")
                    self.commit_status_label.setText(f"Bozza salvata: {draft_str}")
                    self.commit_status_label.setStyleSheet("QLabel { color: gray; }")
                except:
                    self.commit_status_label.setText("Bozza salvata: sconosciuto")
                    self.commit_status_label.setStyleSheet("QLabel { color: gray; }")
            else:
                self.commit_status_label.setText("Nuova bozza")
                self.commit_status_label.setStyleSheet("QLabel { color: gray; }")
        else:
            self.draft_status_label.setText("✓ COMMITTATO")
            self.draft_status_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            
            # Show last commit info
            last_commit_hash = note.get('last_commit_hash')
            if last_commit_hash:
                try:
                    # Get commit date from git
                    commit_date = self.git_service.get_commit_date(last_commit_hash)
                    if commit_date:
                        commit_dt = datetime.fromisoformat(commit_date).astimezone()
                        commit_str = commit_dt.strftime("%d/%m/%Y %H:%M:%S")
                        short_hash = last_commit_hash[:8]
                        self.commit_status_label.setText(f"Ultimo commit: {commit_str} ({short_hash})")
                        self.commit_status_label.setStyleSheet("QLabel { color: green; }")
                    else:
                        self.commit_status_label.setText(f"Commit: {last_commit_hash[:8]}")
                        self.commit_status_label.setStyleSheet("QLabel { color: green; }")
                except:
                    self.commit_status_label.setText("Commit: sconosciuto")
                    self.commit_status_label.setStyleSheet("QLabel { color: green; }")
            else:
                self.commit_status_label.setText("Nessun commit")
                self.commit_status_label.setStyleSheet("QLabel { color: gray; }")

    def delete_note(self):
        """Soft delete the current note."""
        if not self.current_note_id:
            return

        reply = QMessageBox.question(
            self, "Conferma Eliminazione",
            "Sei sicuro di voler eliminare questa nota?\nLa nota potrà essere ripristinata dalle impostazioni.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_service.delete_note_soft(self.current_note_id)
                self.load_notes()
                self.apply_filters()  # Apply filters after reloading
                self.clear_editor()
                self.current_note_id = None
                self.save_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
                self.restore_btn.setEnabled(False)
                self.restore_btn.setVisible(False)
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore nell'eliminazione della nota: {str(e)}")

    def restore_note(self):
        """Restore a soft-deleted note."""
        if not self.current_note_id:
            return

        try:
            self.db_service.restore_note(self.current_note_id)
            self.load_notes()
            self.apply_filters()  # Apply filters after reloading
            self.load_note_in_editor(self.current_note_id)  # Reload to update UI
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel ripristino della nota: {str(e)}")

    def show_all_notes_grid(self):
        """Shows a dialog with all notes in a grid view."""
        try:
            # Emette un segnale per richiedere l'apertura del dialogo delle note
            from PyQt6.QtCore import pyqtSignal
            if not hasattr(self.__class__, 'all_notes_requested'):
                self.__class__.all_notes_requested = pyqtSignal()
            self.all_notes_requested.emit()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nell'apertura della vista note: {str(e)}")
            
    def _open_jira_detail(self):
        """Opens the detail view for the Jira issue associated with the current note."""
        jira_key = self.jira_key_edit.text().strip()
        if jira_key:
            self.open_jira_detail_requested.emit(jira_key)
    
    def _on_jira_key_changed(self):
        """Handle changes to the Jira key field."""
        # Aggiorna lo stato dei pulsanti in base alla presenza di una chiave Jira
        jira_key = self.jira_key_edit.text().strip()
        has_jira = bool(jira_key)
        self.open_jira_btn.setEnabled(has_jira)
        self.start_timer_btn.setEnabled(has_jira)
        # Chiamare anche il metodo originale per gestire le modifiche al contenuto
        self.on_content_changed()
        
    def _start_timer(self):
        """Avvia il timer per il ticket Jira associato alla nota corrente."""
        jira_key = self.jira_key_edit.text().strip()
        if jira_key:
            self.start_timer_requested.emit(jira_key)
        
    def _on_table_double_clicked(self, model_index):
        """Handle double-click on table row."""
        row = model_index.row()
        # Se è stata cliccata la colonna Jira Key e c'è un valore, apri il dettaglio
        if model_index.column() == 1:  # Colonna Jira Key
            jira_key = self.notes_table.item(row, 1).text().strip()
            if jira_key:
                # Se la cella contiene una chiave Jira valida, offri la possibilità di aprire il dettaglio o avviare il timer
                from PyQt6.QtWidgets import QMenu
                from PyQt6.QtGui import QCursor
                menu = QMenu(self)
                open_detail_action = menu.addAction("Apri dettaglio")
                open_detail_action.setIcon(FIF.LINK)
                start_timer_action = menu.addAction("Avvia timer")
                start_timer_action.setIcon(FIF.CLOCK)
                
                # Mostra il menu contestuale al punto del click
                action = menu.exec(QCursor.pos())
                
                if action == open_detail_action:
                    self.open_jira_detail_requested.emit(jira_key)
                elif action == start_timer_action:
                    self.start_timer_requested.emit(jira_key)
    
    def _select_note_by_id(self, note_id):
        """Seleziona una nota nella tabella dato il suo ID."""
        if note_id is None:
            return
            
        # Cerca la nota nella tabella tramite ID memorizzato in UserRole
        for row in range(self.notes_table.rowCount()):
            item = self.notes_table.item(row, 0)  # Il title item contiene l'ID della nota
            if item and item.data(Qt.ItemDataRole.UserRole) == note_id:
                # Seleziona la riga trovata
                self.notes_table.selectRow(row)
                # Assicura che la riga sia visibile
                self.notes_table.scrollToItem(item)
                return
        
    def closeEvent(self, event):
        """Handle dialog closing."""
        super().closeEvent(event)

    def showEvent(self, event):
        # Don't automatically apply always-on-top to dialog windows
        # Let the controller manage window stacking order
        super().showEvent(event)