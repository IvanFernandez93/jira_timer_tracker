"""
Note Version History Dialog - Gestione cronologia versioni delle note
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QSplitter, QTextEdit, QComboBox, QGroupBox, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont, QIcon
from qfluentwidgets import (
    PushButton, PrimaryPushButton, FluentIcon as FIF,
    InfoBar, InfoBarPosition
)
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class NoteVersionHistoryDialog(QDialog):
    """Dialog per visualizzare e gestire la cronologia delle versioni delle note."""
    
    # Segnali
    version_restored = pyqtSignal(int)  # version_id restaurato
    
    def __init__(self, note_manager, note_id: int, note_title: str, parent=None):
        super().__init__(parent)
        self.note_manager = note_manager
        self.note_id = note_id
        self.note_title = note_title
        self.versions = []
        
        self.setWindowTitle(f"Cronologia Versioni - {note_title}")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        self.setup_ui()
        self.load_versions()
        
    def setup_ui(self):
        """Setup dell'interfaccia utente."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header con info nota
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel(f"📝 Cronologia: {self.note_title}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Pulsante refresh
        self.refresh_btn = PushButton("🔄 Aggiorna")
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.clicked.connect(self.load_versions)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(header_frame)
        
        # Splitter principale
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Pannello sinistro: Tabella versioni
        left_widget = self.create_versions_table()
        splitter.addWidget(left_widget)
        
        # Pannello destro: Dettagli versione
        right_widget = self.create_version_details()
        splitter.addWidget(right_widget)
        
        # Imposta proporzioni splitter
        splitter.setSizes([600, 400])
        
        # Pulsanti azione
        buttons_layout = QHBoxLayout()
        
        self.diff_external_btn = PrimaryPushButton("📊 Diff Esterno")
        self.diff_external_btn.setIcon(FIF.COMPARE)
        self.diff_external_btn.setEnabled(False)
        self.diff_external_btn.clicked.connect(self.show_external_diff)
        buttons_layout.addWidget(self.diff_external_btn)
        
        buttons_layout.addStretch()
        
        self.restore_btn = PushButton("↩️ Ripristina Versione")
        self.restore_btn.setIcon(FIF.HISTORY)
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.restore_selected_version)
        buttons_layout.addWidget(self.restore_btn)
        
        close_btn = PushButton("Chiudi")
        close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
    def create_versions_table(self):
        """Crea il pannello con la tabella delle versioni."""
        widget = QGroupBox("📜 Versioni Note")
        layout = QVBoxLayout(widget)
        
        # Tabella versioni
        self.versions_table = QTableWidget()
        self.versions_table.setColumnCount(6)
        self.versions_table.setHorizontalHeaderLabels([
            "Timestamp", "Tipo", "Autore", "Hash", "Commit Git", "Preview"
        ])
        
        # Configurazione tabella
        header = self.versions_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Tipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Autore
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Hash
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Commit
        # Preview si espande (stretch last section)
        
        self.versions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.versions_table.setAlternatingRowColors(True)
        self.versions_table.setSortingEnabled(True)
        
        # Connessioni
        self.versions_table.currentRowChanged.connect(self.on_version_selected)
        self.versions_table.itemDoubleClicked.connect(self.on_version_double_clicked)
        
        layout.addWidget(self.versions_table)
        
        # Info label
        self.info_label = QLabel("💡 Doppio-click su una versione per vedere i dettagli")
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.info_label)
        
        return widget
        
    def create_version_details(self):
        """Crea il pannello dei dettagli versione."""
        widget = QGroupBox("🔍 Dettagli Versione")
        layout = QVBoxLayout(widget)
        
        # Form dettagli
        form_layout = QFormLayout()
        
        self.detail_timestamp = QLabel("-")
        form_layout.addRow("📅 Timestamp:", self.detail_timestamp)
        
        self.detail_type = QLabel("-")
        form_layout.addRow("🏷️ Tipo:", self.detail_type)
        
        self.detail_author = QLabel("-")
        form_layout.addRow("👤 Autore:", self.detail_author)
        
        self.detail_hash = QLabel("-")
        form_layout.addRow("🔒 Hash:", self.detail_hash)
        
        self.detail_commit = QLabel("-")
        form_layout.addRow("🌿 Git Commit:", self.detail_commit)
        
        layout.addLayout(form_layout)
        
        # Anteprima contenuto
        layout.addWidget(QLabel("📄 Anteprima Contenuto:"))
        
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setMaximumHeight(200)
        self.content_preview.setPlaceholderText("Seleziona una versione per vedere l'anteprima...")
        layout.addWidget(self.content_preview)
        
        # Sezione diff viewer esterno
        diff_group = QGroupBox("🔧 Configurazione Diff Esterno")
        diff_layout = QFormLayout(diff_group)
        
        self.diff_tool_combo = QComboBox()
        self.diff_tool_combo.addItems([
            "VS Code (code --diff)",
            "Beyond Compare",
            "WinMerge", 
            "Notepad++ Compare",
            "Git Diff Tool",
            "Personalizzato..."
        ])
        diff_layout.addRow("🛠️ Tool:", self.diff_tool_combo)
        
        layout.addWidget(diff_group)
        
        return widget
        
    def load_versions(self):
        """Carica le versioni della nota."""
        try:
            self.versions = self.note_manager.list_versions(self.note_id, limit=200)
            self.populate_versions_table()
            
            # Aggiorna info
            count = len(self.versions)
            self.info_label.setText(f"💡 {count} versioni trovate. Doppio-click per dettagli.")
            
        except Exception as e:
            logger.error(f"Errore caricamento versioni: {e}")
            QMessageBox.warning(self, "Errore", f"Errore nel caricamento delle versioni: {e}")
            
    def populate_versions_table(self):
        """Popola la tabella con le versioni."""
        self.versions_table.setRowCount(len(self.versions))
        
        for row, version in enumerate(self.versions):
            # Timestamp
            timestamp_str = self.format_timestamp(version.get('created_at', ''))
            self.versions_table.setItem(row, 0, QTableWidgetItem(timestamp_str))
            
            # Tipo con icona
            type_str = self.format_source_type(version.get('source_type', ''))
            self.versions_table.setItem(row, 1, QTableWidgetItem(type_str))
            
            # Autore
            author = version.get('author', 'Unknown')
            self.versions_table.setItem(row, 2, QTableWidgetItem(author))
            
            # Hash (primi 8 caratteri)
            hash_short = version.get('content_hash', '')[:8]
            self.versions_table.setItem(row, 3, QTableWidgetItem(hash_short))
            
            # Commit Git (se presente)
            commit_hash = version.get('commit_hash', '')
            commit_display = commit_hash[:8] if commit_hash else "-"
            self.versions_table.setItem(row, 4, QTableWidgetItem(commit_display))
            
            # Preview (primi 100 caratteri)
            preview = version.get('preview', '')[:100]
            if len(preview) > 97:
                preview = preview[:97] + "..."
            self.versions_table.setItem(row, 5, QTableWidgetItem(preview))
            
        # Ordina per timestamp (più recente primo)
        self.versions_table.sortItems(0, Qt.SortOrder.DescendingOrder)
        
    def format_timestamp(self, timestamp_str: str) -> str:
        """Formatta il timestamp per la visualizzazione."""
        if not timestamp_str:
            return "-"
        try:
            # Parse ISO format
            if 'T' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            return timestamp_str
            
    def format_source_type(self, source_type: str) -> str:
        """Formatta il tipo di source con icone."""
        type_icons = {
            'create': '✨ Creazione',
            'draft': '📝 Bozza',
            'commit': '✅ Commit',
            'manual_restore': '↩️ Ripristino',
            'autosave': '💾 Auto-save'
        }
        return type_icons.get(source_type, f"❓ {source_type}")
        
    def on_version_selected(self, current_row: int, previous_row: int):
        """Gestisce la selezione di una versione."""
        if current_row < 0 or current_row >= len(self.versions):
            self.restore_btn.setEnabled(False)
            self.diff_external_btn.setEnabled(False)
            return
            
        version = self.versions[current_row]
        
        # Aggiorna dettagli
        self.detail_timestamp.setText(self.format_timestamp(version.get('created_at', '')))
        self.detail_type.setText(self.format_source_type(version.get('source_type', '')))
        self.detail_author.setText(version.get('author', 'Unknown'))
        self.detail_hash.setText(version.get('content_hash', ''))
        
        commit_hash = version.get('commit_hash', '')
        if commit_hash:
            self.detail_commit.setText(f"{commit_hash} 🔗")
        else:
            self.detail_commit.setText("Nessun commit")
            
        # Carica anteprima contenuto
        self.load_version_content_preview(version['id'])
        
        # Abilita pulsanti
        self.restore_btn.setEnabled(True)
        
        # Abilita diff se ci sono almeno 2 versioni selezionate o una versione + current
        selected_rows = [item.row() for item in self.versions_table.selectedItems()]
        self.diff_external_btn.setEnabled(len(self.versions) >= 2)
        
    def on_version_double_clicked(self, item):
        """Gestisce il doppio click su una versione."""
        row = item.row()
        if row >= 0 and row < len(self.versions):
            version = self.versions[row]
            self.show_version_full_content(version)
            
    def load_version_content_preview(self, version_id: int):
        """Carica l'anteprima del contenuto di una versione."""
        try:
            content = self.note_manager.db_service.get_note_version_content(version_id)
            if content:
                # Mostra i primi 500 caratteri
                preview = content[:500]
                if len(content) > 500:
                    preview += "\n\n... [contenuto troncato]"
                self.content_preview.setPlainText(preview)
            else:
                self.content_preview.setPlainText("Contenuto non disponibile")
        except Exception as e:
            logger.error(f"Errore caricamento contenuto versione {version_id}: {e}")
            self.content_preview.setPlainText(f"Errore: {e}")
            
    def show_version_full_content(self, version: Dict):
        """Mostra il contenuto completo di una versione in un dialog separato."""
        try:
            content = self.note_manager.db_service.get_note_version_content(version['id'])
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Contenuto Versione - {version.get('source_type', '')}")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Info versione
            info_text = (f"📅 {self.format_timestamp(version.get('created_at', ''))} | "
                        f"🏷️ {version.get('source_type', '')} | "
                        f"👤 {version.get('author', '')}")
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Contenuto
            content_edit = QTextEdit()
            content_edit.setPlainText(content or "Contenuto non disponibile")
            content_edit.setReadOnly(True)
            layout.addWidget(content_edit)
            
            # Pulsante chiudi
            close_btn = QPushButton("Chiudi")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nel caricamento del contenuto: {e}")
            
    def show_external_diff(self):
        """Apre il diff esterno tra versioni selezionate."""
        selected_rows = [item.row() for item in self.versions_table.selectedItems()]
        
        if len(selected_rows) == 0:
            QMessageBox.information(self, "Info", "Seleziona una versione per confrontarla con la versione corrente.")
            return
            
        # Se una sola versione selezionata, confronta con la corrente
        if len(selected_rows) == 1:
            self.diff_with_current(selected_rows[0])
        else:
            # Prendi le prime due versioni selezionate
            self.diff_between_versions(selected_rows[0], selected_rows[1])
            
    def diff_with_current(self, version_row: int):
        """Confronta una versione con la versione corrente della nota."""
        try:
            from services.external_diff_service import ExternalDiffService
            
            version = self.versions[version_row]
            version_id = version['id']
            
            # Ottieni contenuto versione
            version_content = self.note_manager.db_service.get_note_version_content(version_id)
            
            # Ottieni contenuto corrente
            current_note = self.note_manager.db_service.get_note_by_id(self.note_id)
            current_content = current_note.get('content', '') if current_note else ''
            
            # Usa il servizio diff esterno
            diff_service = ExternalDiffService()
            tool = self.diff_tool_combo.currentText()
            
            success = diff_service.open_diff(
                version_content, current_content,
                f"Versione_{version.get('source_type', '')}_{version_id}",
                f"Corrente_{self.note_title}",
                tool
            )
            
            if not success:
                QMessageBox.warning(self, "Errore", "Impossibile aprire il diff esterno. Verifica la configurazione del tool.")
                
        except ImportError:
            QMessageBox.information(self, "Info", 
                "Servizio diff esterno non ancora implementato. Verrà aggiunto prossimamente.")
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nell'apertura del diff: {e}")
            
    def diff_between_versions(self, row1: int, row2: int):
        """Confronta due versioni tra loro."""
        try:
            from services.external_diff_service import ExternalDiffService
            
            version1 = self.versions[row1]
            version2 = self.versions[row2]
            
            content1 = self.note_manager.db_service.get_note_version_content(version1['id'])
            content2 = self.note_manager.db_service.get_note_version_content(version2['id'])
            
            diff_service = ExternalDiffService()
            tool = self.diff_tool_combo.currentText()
            
            success = diff_service.open_diff(
                content1, content2,
                f"Versione_{version1.get('source_type', '')}_{version1['id']}",
                f"Versione_{version2.get('source_type', '')}_{version2['id']}",
                tool
            )
            
            if not success:
                QMessageBox.warning(self, "Errore", "Impossibile aprire il diff esterno.")
                
        except ImportError:
            QMessageBox.information(self, "Info", 
                "Servizio diff esterno non ancora implementato.")
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nell'apertura del diff: {e}")
            
    def restore_selected_version(self):
        """Ripristina la versione selezionata."""
        current_row = self.versions_table.currentRow()
        if current_row < 0:
            return
            
        version = self.versions[current_row]
        version_id = version['id']
        
        # Conferma
        type_str = self.format_source_type(version.get('source_type', ''))
        timestamp_str = self.format_timestamp(version.get('created_at', ''))
        
        reply = QMessageBox.question(
            self, "Conferma Ripristino",
            f"Ripristinare la versione:\n\n"
            f"🏷️ Tipo: {type_str}\n"
            f"📅 Data: {timestamp_str}\n"
            f"👤 Autore: {version.get('author', '')}\n\n"
            f"⚠️ La nota diventerà una bozza e potrà essere modificata prima del commit.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.note_manager.restore_version(self.note_id, version_id)
                if success:
                    # Mostra conferma
                    InfoBar.success(
                        title="Ripristino Completato",
                        content=f"Versione ripristinata come bozza. Puoi modificarla e fare commit.",
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    
                    # Emetti segnale
                    self.version_restored.emit(version_id)
                    
                    # Ricarica versioni per mostrare il nuovo snapshot di restore
                    self.load_versions()
                else:
                    QMessageBox.warning(self, "Errore", "Impossibile ripristinare la versione.")
                    
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Errore nel ripristino: {e}")