#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Universal Search Widget - Widget di ricerca universale simile a VSCode
Supporta ricerca in tempo reale con Ctrl+F in tutti i componenti dell'applicazione.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, 
    QCheckBox, QLabel, QFrame, QTextEdit, QListWidget, QTableWidget,
    QToolButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QTextCursor, QTextCharFormat, QColor, QShortcut
import re
from typing import List, Union, Optional, Any
import logging

logger = logging.getLogger(__name__)

try:
    from qfluentwidgets import (
        LineEdit, PushButton, CheckBox, ToolButton, FluentIcon as FIF
    )
    FLUENT_AVAILABLE = True
except ImportError:
    # Fallback to standard widgets if FluentUI is not available
    LineEdit = QLineEdit
    PushButton = QPushButton
    CheckBox = QCheckBox
    ToolButton = QToolButton
    FLUENT_AVAILABLE = False


class UniversalSearchWidget(QFrame):
    """
    Widget di ricerca universale che può essere integrato in qualsiasi finestra
    per fornire funzionalità di ricerca simile a VSCode con Ctrl+F.
    """
    
    # Segnali
    search_requested = pyqtSignal(str, bool, bool)  # text, case_sensitive, whole_word
    close_requested = pyqtSignal()
    next_requested = pyqtSignal()
    previous_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_targets = []  # Lista di widget dove cercare
        self.current_matches = []  # Matches correnti
        self.current_match_index = -1
        self.last_search_text = ""
        
        self.setup_ui()
        self.setup_shortcuts()
        self.hide()  # Nascosto di default
        
    def setup_ui(self):
        """Configura l'interfaccia utente del widget di ricerca."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            UniversalSearchWidget {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        
        # Layout principale orizzontale
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Campo di ricerca
        if FLUENT_AVAILABLE:
            self.search_edit = LineEdit()
            self.search_edit.setPlaceholderText("Cerca... (Ctrl+F)")
        else:
            self.search_edit = QLineEdit()
            self.search_edit.setPlaceholderText("Cerca... (Ctrl+F)")
        
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.returnPressed.connect(self.find_next)
        
        # Label per conteggio risultati
        self.results_label = QLabel("0 di 0")
        self.results_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        self.results_label.setMinimumWidth(50)
        
        # Pulsanti di navigazione
        if FLUENT_AVAILABLE:
            self.prev_btn = ToolButton()
            self.prev_btn.setIcon(FIF.UP)
            self.next_btn = ToolButton()
            self.next_btn.setIcon(FIF.DOWN)
        else:
            self.prev_btn = QToolButton()
            self.prev_btn.setText("↑")
            self.next_btn = QToolButton()
            self.next_btn.setText("↓")
        
        self.prev_btn.setToolTip("Risultato precedente (Shift+F3)")
        self.next_btn.setToolTip("Risultato successivo (F3)")
        self.prev_btn.clicked.connect(self.find_previous)
        self.next_btn.clicked.connect(self.find_next)
        
        # Opzioni di ricerca
        if FLUENT_AVAILABLE:
            self.case_sensitive_cb = CheckBox("Aa")
        else:
            self.case_sensitive_cb = QCheckBox("Aa")
        self.case_sensitive_cb.setToolTip("Sensibile alle maiuscole/minuscole")
        self.case_sensitive_cb.toggled.connect(self._on_search_options_changed)
        
        if FLUENT_AVAILABLE:
            self.whole_word_cb = CheckBox("Ab")
        else:
            self.whole_word_cb = QCheckBox("Ab")
        self.whole_word_cb.setToolTip("Parola intera")
        self.whole_word_cb.toggled.connect(self._on_search_options_changed)
        
        # Pulsante chiudi
        if FLUENT_AVAILABLE:
            self.close_btn = ToolButton()
            self.close_btn.setIcon(FIF.CLOSE)
        else:
            self.close_btn = QToolButton()
            self.close_btn.setText("✕")
        self.close_btn.setToolTip("Chiudi ricerca (Esc)")
        self.close_btn.clicked.connect(self.hide_search)
        
        # Aggiungi widgets al layout
        layout.addWidget(self.search_edit)
        layout.addWidget(self.results_label)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.case_sensitive_cb)
        layout.addWidget(self.whole_word_cb)
        layout.addStretch()
        layout.addWidget(self.close_btn)
        
    def setup_shortcuts(self):
        """Configura le scorciatoie da tastiera."""
        # Ctrl+F per aprire la ricerca
        self.open_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.parent())
        self.open_shortcut.activated.connect(self.show_search)
        
        # Esc per chiudere la ricerca
        self.close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.close_shortcut.activated.connect(self.hide_search)
        
        # F3 per prossimo risultato
        self.next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F3), self.parent())
        self.next_shortcut.activated.connect(self.find_next)
        
        # Shift+F3 per risultato precedente
        self.prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self.parent())
        self.prev_shortcut.activated.connect(self.find_previous)
        
    def add_search_target(self, widget):
        """
        Aggiunge un widget come target per la ricerca.
        
        Args:
            widget: Widget dove effettuare la ricerca (QTextEdit, QTextBrowser, QListWidget, etc.)
        """
        if widget not in self.search_targets:
            self.search_targets.append(widget)
            logger.debug(f"Added search target: {widget.__class__.__name__}")
    
    def remove_search_target(self, widget):
        """Rimuove un widget dai target di ricerca."""
        if widget in self.search_targets:
            self.search_targets.remove(widget)
            logger.debug(f"Removed search target: {widget.__class__.__name__}")
    
    def show_search(self):
        """Mostra il widget di ricerca e imposta il focus."""
        self.show()
        self.search_edit.setFocus()
        self.search_edit.selectAll()
        
    def hide_search(self):
        """Nasconde il widget di ricerca e pulisce i risultati."""
        self.hide()
        self._clear_highlights()
        self.close_requested.emit()
        
    def _on_search_text_changed(self):
        """Gestisce il cambio del testo di ricerca."""
        search_text = self.search_edit.text()
        if search_text != self.last_search_text:
            self.last_search_text = search_text
            if search_text:
                # Avvia ricerca con un piccolo delay per evitare troppe ricerche
                QTimer.singleShot(300, self._perform_search)
            else:
                self._clear_search_results()
    
    def _on_search_options_changed(self):
        """Gestisce il cambio delle opzioni di ricerca."""
        if self.search_edit.text():
            self._perform_search()
    
    def _perform_search(self):
        """Esegue la ricerca sui target configurati."""
        search_text = self.search_edit.text().strip()
        if not search_text:
            self._clear_search_results()
            return
        
        case_sensitive = self.case_sensitive_cb.isChecked()
        whole_word = self.whole_word_cb.isChecked()
        
        # Pulisce risultati precedenti
        self._clear_highlights()
        self.current_matches = []
        
        # Cerca in tutti i target
        total_matches = 0
        for widget in self.search_targets:
            matches = self._search_in_widget(widget, search_text, case_sensitive, whole_word)
            total_matches += len(matches)
            self.current_matches.extend(matches)
        
        # Aggiorna UI
        self._update_results_label(total_matches)
        
        # Evidenzia primo risultato se presente
        if self.current_matches:
            self.current_match_index = 0
            self._highlight_current_match()
        else:
            self.current_match_index = -1
        
        # Emette segnale per ricerca personalizzata
        self.search_requested.emit(search_text, case_sensitive, whole_word)
    
    def _search_in_widget(self, widget, search_text: str, case_sensitive: bool, whole_word: bool) -> List[dict]:
        """
        Cerca il testo in un widget specifico.
        
        Returns:
            Lista di dizionari con informazioni sui match trovati
        """
        matches = []
        
        try:
            # Gestisce diversi tipi di widget
            if hasattr(widget, 'toPlainText'):
                # QTextEdit, QTextBrowser
                content = widget.toPlainText()
                widget_matches = self._find_text_matches(content, search_text, case_sensitive, whole_word)
                for match in widget_matches:
                    match['widget'] = widget
                    match['type'] = 'text'
                matches.extend(widget_matches)
                
            elif hasattr(widget, 'count'):
                # QListWidget
                for i in range(widget.count()):
                    item = widget.item(i)
                    if item:
                        content = item.text()
                        text_matches = self._find_text_matches(content, search_text, case_sensitive, whole_word)
                        for match in text_matches:
                            match['widget'] = widget
                            match['type'] = 'list_item'
                            match['item_index'] = i
                        matches.extend(text_matches)
                        
            elif hasattr(widget, 'text'):
                # QLabel, QLineEdit, etc.
                content = widget.text()
                widget_matches = self._find_text_matches(content, search_text, case_sensitive, whole_word)
                for match in widget_matches:
                    match['widget'] = widget
                    match['type'] = 'simple_text'
                matches.extend(widget_matches)
        
        except Exception as e:
            logger.warning(f"Error searching in widget {widget.__class__.__name__}: {e}")
        
        return matches
    
    def _find_text_matches(self, content: str, search_text: str, case_sensitive: bool, whole_word: bool) -> List[dict]:
        """Trova tutte le occorrenze del testo nel contenuto."""
        matches = []
        
        if not content or not search_text:
            return matches
        
        # Prepara il pattern di ricerca
        flags = 0 if case_sensitive else re.IGNORECASE
        
        if whole_word:
            pattern = r'\b' + re.escape(search_text) + r'\b'
        else:
            pattern = re.escape(search_text)
        
        try:
            for match in re.finditer(pattern, content, flags):
                matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(),
                    'context': self._get_match_context(content, match.start(), match.end())
                })
        except Exception as e:
            logger.warning(f"Error in regex search: {e}")
        
        return matches
    
    def _get_match_context(self, content: str, start: int, end: int, context_length: int = 50) -> str:
        """Ottiene il contesto attorno a un match."""
        context_start = max(0, start - context_length)
        context_end = min(len(content), end + context_length)
        
        before = content[context_start:start]
        match_text = content[start:end]
        after = content[end:context_end]
        
        return f"...{before}[{match_text}]{after}..."
    
    def _highlight_current_match(self):
        """Evidenzia il match corrente."""
        if not self.current_matches or self.current_match_index < 0:
            return
        
        current_match = self.current_matches[self.current_match_index]
        widget = current_match['widget']
        
        try:
            if current_match['type'] == 'text':
                # QTextEdit/QTextBrowser
                if hasattr(widget, 'textCursor'):
                    cursor = widget.textCursor()
                    cursor.setPosition(current_match['start'])
                    cursor.setPosition(current_match['end'], QTextCursor.MoveMode.KeepAnchor)
                    widget.setTextCursor(cursor)
                    widget.ensureCursorVisible()
                    
            elif current_match['type'] == 'list_item':
                # QListWidget
                if hasattr(widget, 'setCurrentRow'):
                    widget.setCurrentRow(current_match['item_index'])
                    
        except Exception as e:
            logger.warning(f"Error highlighting match: {e}")
    
    def find_next(self):
        """Vai al prossimo risultato."""
        if not self.current_matches:
            return
        
        self.current_match_index = (self.current_match_index + 1) % len(self.current_matches)
        self._highlight_current_match()
        self._update_results_label(len(self.current_matches))
        self.next_requested.emit()
    
    def find_previous(self):
        """Vai al risultato precedente."""
        if not self.current_matches:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.current_matches)
        self._highlight_current_match()
        self._update_results_label(len(self.current_matches))
        self.previous_requested.emit()
    
    def _update_results_label(self, total_matches: int):
        """Aggiorna la label con il conteggio dei risultati."""
        if total_matches == 0:
            self.results_label.setText("0 di 0")
        else:
            current = self.current_match_index + 1 if self.current_match_index >= 0 else 1
            self.results_label.setText(f"{current} di {total_matches}")
    
    def _clear_search_results(self):
        """Pulisce tutti i risultati di ricerca."""
        self.current_matches = []
        self.current_match_index = -1
        self._clear_highlights()
        self.results_label.setText("0 di 0")
    
    def _clear_highlights(self):
        """Rimuove tutti gli highlight dai widget."""
        for widget in self.search_targets:
            try:
                if hasattr(widget, 'textCursor'):
                    # Rimuove selezione da QTextEdit/QTextBrowser
                    cursor = widget.textCursor()
                    cursor.clearSelection()
                    widget.setTextCursor(cursor)
            except Exception as e:
                logger.warning(f"Error clearing highlights: {e}")


class SearchableMixin:
    """
    Mixin class per aggiungere facilmente funzionalità di ricerca a qualsiasi widget/dialog.
    """
    
    def init_search_functionality(self):
        """Inizializza la funzionalità di ricerca per questa finestra."""
        if not hasattr(self, 'search_widget'):
            self.search_widget = UniversalSearchWidget(self)
            
            # Aggiungi il widget di ricerca al layout principale
            if hasattr(self, 'layout') and self.layout():
                layout = self.layout()
                if isinstance(layout, QVBoxLayout):
                    layout.insertWidget(0, self.search_widget)
                else:
                    # Crea un nuovo layout verticale se necessario
                    main_layout = QVBoxLayout()
                    main_layout.addWidget(self.search_widget)
                    main_layout.addWidget(self.centralWidget() if hasattr(self, 'centralWidget') else self)
                    self.setLayout(main_layout)
    
    def add_searchable_widget(self, widget):
        """Aggiunge un widget come target di ricerca."""
        if hasattr(self, 'search_widget'):
            self.search_widget.add_search_target(widget)
    
    def remove_searchable_widget(self, widget):
        """Rimuove un widget dai target di ricerca."""
        if hasattr(self, 'search_widget'):
            self.search_widget.remove_search_target(widget)
    
    def show_search(self):
        """Mostra il widget di ricerca."""
        if hasattr(self, 'search_widget'):
            self.search_widget.show_search()
    
    def hide_search(self):
        """Nasconde il widget di ricerca."""
        if hasattr(self, 'search_widget'):
            self.search_widget.hide_search()