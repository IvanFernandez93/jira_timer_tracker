from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import QDateTime, Qt
from views.jql_history_dialog import JqlHistoryDialog

class JqlHistoryController:
    """Controller for the JQL History dialog."""
    def __init__(self, db_service, from_grid=False):
        self.db_service = db_service
        self.from_grid = from_grid
        self.view = JqlHistoryDialog(from_grid=from_grid)
        self._connect_signals()
        
    def _connect_signals(self):
        # History tab signals
        self.view.history_list.currentItemChanged.connect(self._on_history_item_selected)
        self.view.use_history_btn.clicked.connect(self._on_use_history)
        self.view.add_to_favorites_btn.clicked.connect(self._on_add_to_favorites)
        
        # Favorites tab signals
        self.view.favorites_list.currentItemChanged.connect(self._on_favorite_item_selected)
        self.view.use_favorite_btn.clicked.connect(self._on_use_favorite)
        self.view.rename_favorite_btn.clicked.connect(self._on_rename_favorite)
        self.view.delete_favorite_btn.clicked.connect(self._on_delete_favorite)
        
        # Quick select button (only if from grid)
        if self.from_grid:
            self.view.quick_select_btn.clicked.connect(self._on_quick_select)
        
    def run(self):
        """Load data and show the dialog."""
        self._load_history()
        self._load_favorites()
        self._update_button_states()
        self.view.show()
    
    def _load_history(self):
        """Load JQL history from the database."""
        history_items = self.db_service.get_jql_history()
        self.view.populate_history(history_items)
    
    def _load_favorites(self):
        """Load favorite JQLs from the database."""
        favorite_items = self.db_service.get_favorite_jqls()
        self.view.populate_favorites(favorite_items)
    
    def _update_button_states(self):
        """Update button states based on selections."""
        # History tab buttons
        history_selected = self.view.history_list.currentItem() is not None
        self.view.use_history_btn.setEnabled(history_selected)
        self.view.add_to_favorites_btn.setEnabled(history_selected)
        
        # Favorites tab buttons
        favorite_selected = self.view.favorites_list.currentItem() is not None
        self.view.use_favorite_btn.setEnabled(favorite_selected)
        self.view.rename_favorite_btn.setEnabled(favorite_selected)
        self.view.delete_favorite_btn.setEnabled(favorite_selected)
        
        # Quick select button (only if from grid)
        if self.from_grid:
            quick_select_enabled = history_selected or favorite_selected
            self.view.quick_select_btn.setEnabled(quick_select_enabled)
    
    def _on_history_item_selected(self, current, previous):
        """Handle history item selection."""
        if current:
            query = current.data(Qt.ItemDataRole.UserRole)
            self.view.jql_preview.setPlainText(query)
        else:
            self.view.jql_preview.clear()
        self._update_button_states()
    
    def _on_favorite_item_selected(self, current, previous):
        """Handle favorite item selection."""
        if current:
            data = current.data(Qt.ItemDataRole.UserRole)
            self.view.favorite_jql_preview.setPlainText(data["query"])
        else:
            self.view.favorite_jql_preview.clear()
        self._update_button_states()
    
    def _on_use_history(self):
        """Use selected history item."""
        current = self.view.history_list.currentItem()
        if current:
            query = current.data(Qt.ItemDataRole.UserRole)
            self.view.jql_selected.emit(query)
            self.db_service.add_jql_history(query)  # Update last used time
            self.view.show_info("Query Applicata", "La query selezionata è stata applicata alla ricerca principale.")
            self.view.accept()
    
    def _on_add_to_favorites(self):
        """Add selected history item to favorites."""
        current = self.view.history_list.currentItem()
        if not current:
            return
            
        query = current.data(Qt.ItemDataRole.UserRole)
        name, ok = QInputDialog.getText(
            self.view, 
            "Salva JQL nei Preferiti", 
            "Nome della query:",
            text=query[:20] + ("..." if len(query) > 20 else "")
        )
        
        if ok and name:
            # Check if name already exists
            favorites = self.db_service.get_favorite_jqls()
            for _, fav_name, _ in favorites:
                if fav_name == name:
                    QMessageBox.warning(
                        self.view, 
                        "Nome Duplicato", 
                        f"Esiste già una query preferita con il nome '{name}'.\n"
                        "Scegli un nome diverso."
                    )
                    return
                    
            self.db_service.add_favorite_jql(name, query)
            self.view.show_info("Preferiti", f"Query '{name}' aggiunta ai preferiti.")
            self._load_favorites()
    
    def _on_use_favorite(self):
        """Use selected favorite query."""
        current = self.view.favorites_list.currentItem()
        if current:
            data = current.data(Qt.ItemDataRole.UserRole)
            query = data["query"]
            self.view.jql_selected.emit(query)
            self.db_service.add_jql_history(query)  # Add to history
            self.view.show_info("Query Applicata", f"La query preferita '{data['name']}' è stata applicata alla ricerca principale.")
            self.view.accept()
    
    def _on_rename_favorite(self):
        """Rename selected favorite query."""
        current = self.view.favorites_list.currentItem()
        if not current:
            return
            
        data = current.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self.view, 
            "Rinomina Query Preferita", 
            "Nuovo nome:",
            text=data["name"]
        )
        
        if ok and new_name:
            # Check if name already exists
            favorites = self.db_service.get_favorite_jqls()
            for fav_id, fav_name, _ in favorites:
                if fav_name == new_name and fav_id != data["id"]:
                    QMessageBox.warning(
                        self.view, 
                        "Nome Duplicato", 
                        f"Esiste già una query preferita con il nome '{new_name}'.\n"
                        "Scegli un nome diverso."
                    )
                    return
            
            # Delete old and add new with updated name
            self.db_service.delete_favorite_jql(data["id"])
            self.db_service.add_favorite_jql(new_name, data["query"])
            self.view.show_info("Preferiti", f"Query rinominata in '{new_name}'.")
            self._load_favorites()
    
    def _on_delete_favorite(self):
        """Delete selected favorite query."""
        current = self.view.favorites_list.currentItem()
        if not current:
            return
            
        data = current.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self.view,
            "Conferma Eliminazione",
            f"Sei sicuro di voler eliminare la query preferita '{data['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db_service.delete_favorite_jql(data["id"])
            self.view.show_info("Preferiti", f"Query '{data['name']}' eliminata.")
            self._load_favorites()
    
    def _on_quick_select(self):
        """Handle quick select button - select and apply the currently selected query."""
        # Check which tab is active and get the selected item
        current_tab = self.view.tab_widget.currentIndex()
        
        if current_tab == 0:  # History tab
            current = self.view.history_list.currentItem()
            if current:
                query = current.data(Qt.ItemDataRole.UserRole)
                self.view.jql_selected.emit(query)
                self.db_service.add_jql_history(query)  # Update last used time
                self.view.show_info("Query Applicata", "La query selezionata è stata applicata alla ricerca principale.")
                self.view.accept()
        
        elif current_tab == 1:  # Favorites tab
            current = self.view.favorites_list.currentItem()
            if current:
                data = current.data(Qt.ItemDataRole.UserRole)
                query = data["query"]
                self.view.jql_selected.emit(query)
                self.db_service.add_jql_history(query)  # Add to history
                self.view.show_info("Query Applicata", f"La query preferita '{data['name']}' è stata applicata alla ricerca principale.")
                self.view.accept()