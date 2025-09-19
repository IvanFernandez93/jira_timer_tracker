from PyQt6.QtCore import QObject, pyqtSignal

class MiniWidgetController(QObject):
    """
    Controller for the MiniWidgetView.
    """
    restore_requested = pyqtSignal()
    favorite_selected = pyqtSignal(str) # Emits jira_key
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, view, db_service):
        super().__init__()
        self.view = view
        self.db_service = db_service
        self._connect_signals()

    def _connect_signals(self):
        self.view.restore_btn.clicked.connect(self.restore_requested.emit)
        self.view.favorites_combo.activated.connect(self._on_favorite_selected)
        self.view.play_btn.clicked.connect(self.play_requested.emit)
        self.view.pause_btn.clicked.connect(self.pause_requested.emit)
        self.view.stop_btn.clicked.connect(self.stop_requested.emit)

    def update_display(self, jira_key, time_str):
        """Updates the Jira key and timer display."""
        self.view.jira_key_label.setText(jira_key or "No active Jira")
        self.view.timer_label.setText(time_str)

    def load_favorites(self):
        """Loads favorite Jiras into the combobox."""
        self.view.favorites_combo.clear()
        self.view.favorites_combo.addItem("Switch to favorite...", userData=None)
        
        favorites = self.db_service.get_all_favorites()
        for key in favorites:
            self.view.favorites_combo.addItem(key, userData=key)

    def _on_favorite_selected(self, index):
        """Handles the selection of a favorite Jira from the combobox."""
        jira_key = self.view.favorites_combo.itemData(index)
        if jira_key:
            self.favorite_selected.emit(jira_key)
        # Reset combo to placeholder
        self.view.favorites_combo.setCurrentIndex(0)

    def show(self, screen):
        """Shows the widget and positions it."""
        self.load_favorites()
        self.view.move_to_bottom_right(screen)
        self.view.show()

    def hide(self):
        """Hides the widget."""
        self.view.hide()
