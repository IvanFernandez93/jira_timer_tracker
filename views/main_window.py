from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt6.QtWidgets import QMenu, QHBoxLayout, QFrame, QLabel
from PyQt6.QtGui import QAction
from qfluentwidgets import FluentWindow, NavigationItemPosition, SubtitleLabel, setFont
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import Theme, setTheme, isDarkTheme

from .notification_indicator import NotificationIndicator
from .sync_status_indicator import SyncStatusIndicator

from .jira_grid_view import JiraGridView
from .history_view import HistoryView

class MainWindow(FluentWindow):
    windowStateChanged = pyqtSignal(Qt.WindowState)
    # Define new signals for navigation actions
    lastActiveRequested = pyqtSignal()
    settingsRequested = pyqtSignal()
    searchJqlRequested = pyqtSignal()
    notesRequested = pyqtSignal()
    syncQueueRequested = pyqtSignal()
    notificationsRequested = pyqtSignal()
    closing = pyqtSignal()  # Signal emitted when window is closing

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jira Time Tracker")
        self.setGeometry(100, 100, 1200, 800)

        # Create and add the Jira Grid View as a sub-interface
        self.jira_grid_view = JiraGridView()
        
        # Create and add the History View
        self.history_view = HistoryView()
        
        # Create sync status indicator
        self.sync_status_indicator = SyncStatusIndicator()
        self.sync_status_indicator.clicked.connect(self._on_sync_status_clicked)
        self.sync_status_indicator.setVisible(False)  # Hide initially
        
        # Create notification indicator
        self.notification_indicator = NotificationIndicator()
        self.notification_indicator.clicked.connect(self._on_notification_clicked)
        self.notification_indicator.setVisible(False)  # Hide initially
        self.notification_indicator.setToolTip("Notifiche")
        
        # Add indicators to the title bar
        self._add_indicators_to_titlebar()
        
        self.initNavigation()

    def initNavigation(self):
        # Add main grid interface
        self.addSubInterface(self.jira_grid_view, FIF.DOCUMENT, "Griglia Jira")
        
        # Add history view interface
        self.addSubInterface(self.history_view, FIF.HISTORY, "Cronologia")

        # Placeholder for "Last Active Jira" - con nuova icona
        self.last_active_item = self.navigationInterface.addItem(
            "last_active",
            FIF.RETURN,
            "Ultima Jira Attiva",
            position=NavigationItemPosition.TOP,
            onClick=self.onLastActiveClicked
        )
        self.last_active_item.setToolTip("Torna all'ultimo ticket Jira aperto")
        
        # JQL Search button
        self.search_item = self.navigationInterface.addItem(
            "search_jql",
            FIF.SEARCH,
            "Ricerca JQL",
            position=NavigationItemPosition.TOP,
            onClick=self.onSearchJqlClicked
        )
        self.search_item.setToolTip("Esegui una ricerca avanzata con JQL")

        # Notes Grid button
        self.notes_item = self.navigationInterface.addItem(
            "notes_grid",
            FIF.DOCUMENT,
            "Tutte le Note",
            position=NavigationItemPosition.TOP,
            onClick=self.onNotesClicked
        )
        self.notes_item.setToolTip("Visualizza tutte le note in una griglia")

        # Sync Queue button
        self.navigationInterface.addSeparator()
        self.sync_queue_item = self.navigationInterface.addItem(
            "sync_queue", 
            FIF.UPDATE,
            "Coda Sincronizzazione",
            position=NavigationItemPosition.BOTTOM,
            onClick=self._on_sync_status_clicked
        )
        self.sync_queue_item.setToolTip("Gestisci la coda di sincronizzazione")
        
        # Settings button
        self.settings_item = self.navigationInterface.addItem(
            "settings",
            FIF.SETTING,
            "Impostazioni",
            position=NavigationItemPosition.BOTTOM,
            onClick=self.onSettingsClicked
        )
        self.settings_item.setToolTip("Impostazioni dell'applicazione e temi")

    @pyqtSlot()
    def onLastActiveClicked(self):
        self.lastActiveRequested.emit()

    @pyqtSlot()
    def onSearchJqlClicked(self):
        self.searchJqlRequested.emit()

    @pyqtSlot()
    def onNotesClicked(self):
        self.notesRequested.emit()

    @pyqtSlot()
    def onSettingsClicked(self):
        # Create a context menu for settings
        menu = QMenu(self)
        
        # Add theme toggle action
        theme_action = QAction("Toggle Theme (Dark/Light)", self)
        theme_action.triggered.connect(self.toggle_theme)
        menu.addAction(theme_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add settings action
        settings_action = QAction("Jira Configuration", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        menu.addAction(settings_action)
        
        # Show the menu at the appropriate position
        menu.exec(self.settings_item.mapToGlobal(self.settings_item.rect().bottomLeft()))
    
    def show_settings_dialog(self):
        # Trigger the settings dialog
        self.settingsRequested.emit()
        
    def toggle_theme(self):
        # Toggle between light and dark theme
        is_dark = isDarkTheme()
        new_theme = Theme.LIGHT if is_dark else Theme.DARK
        setTheme(new_theme)
        
        # Save the theme preference
        settings = QSettings()
        settings.setValue('theme/dark', 0 if is_dark else 1)
        settings.sync()
        
    def _add_indicators_to_titlebar(self):
        """Add indicators to the title bar."""
        # Create a frame for the indicators in the title bar
        indicators_frame = QFrame(self.titleBar)
        indicators_layout = QHBoxLayout(indicators_frame)
        indicators_layout.setContentsMargins(0, 0, 10, 0)
        indicators_layout.setSpacing(10)
        
        # Add the indicators to the layout
        indicators_layout.addWidget(self.notification_indicator)
        indicators_layout.addWidget(self.sync_status_indicator)
        
        # Add the frame to the title bar
        self.titleBar.layout().addWidget(indicators_frame, 0, Qt.AlignmentFlag.AlignRight)
        
    def update_sync_status(self, pending_count, failed_count):
        """Updates the sync status indicator."""
        # Usa l'indicatore di stato della sincronizzazione
        self.sync_status_indicator.set_counts(pending_count, failed_count)
        
        # Aggiorna anche il tooltip del pulsante nella barra di navigazione
        if pending_count > 0 or failed_count > 0:
            tooltip = []
            if pending_count > 0:
                tooltip.append(f"{pending_count} operazioni in attesa")
            if failed_count > 0:
                tooltip.append(f"{failed_count} operazioni fallite")
            
            tooltip_text = "\n".join(tooltip)
            self.sync_queue_item.setToolTip(tooltip_text)
        else:
            self.sync_queue_item.setToolTip("Gestisci la coda di sincronizzazione")
        
    def _on_sync_status_clicked(self):
        """Handles click on the sync queue navigation item."""
        self.syncQueueRequested.emit()
        
    def _on_notification_clicked(self):
        """Handles click on the notification indicator."""
        self.notificationsRequested.emit()
        
    def update_notification_count(self, count):
        """Updates the notification indicator count."""
        self.notification_indicator.set_count(count)

    def changeEvent(self, event):
        """Override the changeEvent to detect window state changes."""
        if event.type() == event.Type.WindowStateChange:
            self.windowStateChanged.emit(self.windowState())
        super().changeEvent(event)

    def closeEvent(self, event):
        """Override the closeEvent to emit closing signal."""
        self.closing.emit()
        super().closeEvent(event)
