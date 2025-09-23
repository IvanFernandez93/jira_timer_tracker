from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QListWidget, QListWidgetItem
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QDialog, QDialogButtonBox
from qfluentwidgets import (
    PushButton, TextEdit, StrongBodyLabel, BodyLabel, 
    LineEdit, InfoBar, InfoBarPosition, FluentIcon as FIF
)

class JqlHistoryDialog(QDialog):
    """Dialog for managing JQL history and favorites."""
    jql_selected = pyqtSignal(str)  # Signal emitted when a JQL is selected to use
    
    def __init__(self, parent=None, from_grid=False):
        super().__init__(parent)
        self.from_grid = from_grid
        self.setWindowTitle("Gestione JQL")
        self.resize(900, 600)  # Increased width and height for better display of long queries
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.history_tab = QWidget()
        self.favorites_tab = QWidget()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.history_tab, "Cronologia")
        self.tab_widget.addTab(self.favorites_tab, "Preferiti")
        
        # Add tab widget to dialog
        self.main_layout.addWidget(self.tab_widget)
        
        # Setup each tab
        self._setup_history_tab()
        self._setup_favorites_tab()
        
        # Add quick select button if opened from grid
        if self.from_grid:
            self._add_quick_select_button()
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        
        # Connect signals
        self.button_box.rejected.connect(self.accept)
        
        # Add button box to layout
        self.main_layout.addWidget(self.button_box)
        
    def _add_quick_select_button(self):
        """Add a quick select button when opened from grid."""
        # Create a horizontal layout for the quick select button
        quick_select_layout = QHBoxLayout()
        
        # Add some spacing
        quick_select_layout.addStretch()
        
        # Create the quick select button
        self.quick_select_btn = PushButton("Seleziona e Applica")
        self.quick_select_btn.setIcon(FIF.CHECKBOX)
        self.quick_select_btn.setToolTip("Seleziona la query evidenziata e applicala alla ricerca principale")
        self.quick_select_btn.setEnabled(False)  # Initially disabled
        
        quick_select_layout.addWidget(self.quick_select_btn)
        quick_select_layout.addStretch()
        
        # Add the layout to the main layout
        self.main_layout.addLayout(quick_select_layout)
        
    def _setup_history_tab(self):
        """Setup the history tab with recent JQL queries."""
        layout = QVBoxLayout(self.history_tab)
        
        layout.addWidget(StrongBodyLabel("Cronologia JQL:"))
        layout.addWidget(BodyLabel("Seleziona una query dalla lista sottostante e clicca 'Usa' per applicarla alla ricerca principale."))
        
        # Create list widget for history items
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.history_list)
        
        # Create buttons for history operations
        buttons_layout = QHBoxLayout()
        
        self.use_history_btn = PushButton("Usa Questa Query")
        self.use_history_btn.setIcon(FIF.CHECKBOX)
        self.add_to_favorites_btn = PushButton("Salva nei Preferiti")
        self.add_to_favorites_btn.setIcon(FIF.BRUSH)  # Changed icon to a more appropriate one
        
        buttons_layout.addWidget(self.use_history_btn)
        buttons_layout.addWidget(self.add_to_favorites_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # JQL preview
        layout.addWidget(StrongBodyLabel("Anteprima Query Selezionata:"))
        self.jql_preview = TextEdit()
        self.jql_preview.setReadOnly(True)
        self.jql_preview.setFixedHeight(120)  # Increased height for better display of long queries
        layout.addWidget(self.jql_preview)
        
    def _setup_favorites_tab(self):
        """Setup the favorites tab with saved JQL queries."""
        layout = QVBoxLayout(self.favorites_tab)
        
        layout.addWidget(StrongBodyLabel("Query JQL Preferite:"))
        layout.addWidget(BodyLabel("Seleziona una query preferita dalla lista sottostante e clicca 'Usa Questa Query' per applicarla alla ricerca principale."))
        
        # Create list widget for favorites
        self.favorites_list = QListWidget()
        self.favorites_list.setAlternatingRowColors(True)
        self.favorites_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.favorites_list)
        
        # Create buttons for favorite operations
        buttons_layout = QHBoxLayout()
        
        self.use_favorite_btn = PushButton("Usa Questa Query")
        self.use_favorite_btn.setIcon(FIF.CHECKBOX)
        self.rename_favorite_btn = PushButton("Rinomina")
        self.rename_favorite_btn.setIcon(FIF.EDIT)
        self.delete_favorite_btn = PushButton("Elimina")
        self.delete_favorite_btn.setIcon(FIF.DELETE)
        
        buttons_layout.addWidget(self.use_favorite_btn)
        buttons_layout.addWidget(self.rename_favorite_btn)
        buttons_layout.addWidget(self.delete_favorite_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # JQL preview for favorites
        layout.addWidget(StrongBodyLabel("Anteprima Query Selezionata:"))
        self.favorite_jql_preview = TextEdit()
        self.favorite_jql_preview.setReadOnly(True)
        self.favorite_jql_preview.setFixedHeight(120)  # Increased height for better display of long queries
        layout.addWidget(self.favorite_jql_preview)
        
    def populate_history(self, history_items):
        """Populate the history list with items from the database."""
        self.history_list.clear()
        for query, timestamp in history_items:
            # Create a more readable display name with better truncation
            if len(query) <= 120:
                display_name = query
            else:
                # Try to truncate at word boundaries for better readability
                truncated = query[:120]
                last_space = truncated.rfind(' ')
                if last_space > 80:  # Only break at space if it's not too early
                    display_name = query[:last_space] + "..."
                else:
                    display_name = truncated + "..."
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, query)
            # Enhanced tooltip with full query and timestamp
            item.setToolTip(f"Ultimo utilizzo: {timestamp}\n\nQuery completa:\n{query}")
            self.history_list.addItem(item)
        
    def populate_favorites(self, favorite_items):
        """Populate the favorites list with items from the database."""
        self.favorites_list.clear()
        for id, name, query in favorite_items:
            # Create a display name that shows both the favorite name and a preview of the query
            if len(query) <= 60:
                display_name = f"{name}: {query}"
            else:
                # Show name and truncated query
                truncated_query = query[:60]
                last_space = truncated_query.rfind(' ')
                if last_space > 30:
                    truncated_query = query[:last_space]
                display_name = f"{name}: {truncated_query}..."
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, {"id": id, "name": name, "query": query})
            # Enhanced tooltip showing the full query
            item.setToolTip(f"Nome: {name}\n\nQuery completa:\n{query}")
            self.favorites_list.addItem(item)
            
    def show_info(self, title, message):
        """Shows an info message using InfoBar."""
        try:
            InfoBar.success(
                title=title,
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, title, str(message))
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        
    def show_error(self, title, message):
        """Shows an error message using InfoBar."""
        try:
            InfoBar.error(
                title=title,
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, title, str(message))
            except Exception:
                pass