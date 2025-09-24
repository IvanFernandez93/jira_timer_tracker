from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QTimer, QEvent
from PyQt6.QtWidgets import QTableWidgetItem, QPushButton, QApplication, QMessageBox
from qfluentwidgets import FluentIcon as FIF
import logging
import re

logger = logging.getLogger('JiraTimeTracker')

from workers.worker import JiraWorker
from views.mini_widget_view import MiniWidgetView
from controllers.mini_widget_controller import MiniWidgetController
from controllers.jql_history_controller import JqlHistoryController
from controllers.history_view_controller import HistoryViewController
from controllers.sync_queue_controller import SyncQueueController
from controllers.notification_controller import NotificationController
from services.network_service import NetworkService


class MainController(QObject):
    # Using a signal to decouple the controller from knowing about worker threads
    data_loaded = pyqtSignal(list)
    load_failed = pyqtSignal(str)

    def __init__(self, view, db_service, jira_service, app_settings, timezone_service=None):
        super().__init__()
        self._logger = logging.getLogger('JiraTimeTracker')
        self.view = view
        self.db_service = db_service
        self.jira_service = jira_service
        self.app_settings = app_settings
        self.timezone_service = timezone_service
        self.open_detail_windows = {}  # Track open detail windows by issue key
        self._opening_detail_window = False  # Flag to prevent automatic closures during opening
        # Track active threads started by this controller so we can shut them down
        self._active_threads: list[QThread] = []
        # Track active worker objects so they are not garbage-collected
        self._active_workers: list[object] = []
        self._open_dialog_windows = []  # Track open dialog windows
        
        # Initialize properties used for data loading
        self.is_loading = False
        self.current_issues = []
        self.start_at = 0
        self.all_results_loaded = False
        
        # Initialize data management attributes
        self.is_loading = False
        self.current_issues = []
        self.start_at = 0
        self.all_results_loaded = False
        
        self._active_timer_key = None
        self._active_timer_seconds = 0
        # Search tracking for server-side searches and retry logic
        self._last_search_term = None
        self._last_search_was_server = False
        self._search_retry_done = False

        # Timer for updating the mini widget display
        self.widget_update_timer = QTimer(self)
        self.widget_update_timer.timeout.connect(self._update_widget_display)
        self.widget_update_timer.start(1000)  # Update every second

        self._setup_mini_widget()
        self._setup_history_view_controller()
        self._setup_sync_queue_monitor()
        self._setup_notification_controller()
        self._setup_attachment_controller()
        self._setup_network_monitoring()
        self._connect_signals()
        
        # Configure grid view with app settings for persistence
        self.view.jira_grid_view.set_app_settings(self.app_settings)
        # Apply always-on-top setting from persisted settings
        self._apply_always_on_top()
        # Install an event filter on the main view to detect activation events
        try:
            self.view.installEventFilter(self)
        except Exception:
            pass

    def _setup_mini_widget(self):
        """Initializes the mini widget and its controller."""
        self.mini_widget_view = MiniWidgetView()
        self.mini_widget_controller = MiniWidgetController(self.mini_widget_view, self.db_service)
        self.mini_widget_controller.restore_requested.connect(self._restore_main_window)
        self.mini_widget_controller.favorite_selected.connect(self._start_timer_from_widget)
        self.mini_widget_controller.play_requested.connect(self._play_active_timer)
        self.mini_widget_controller.pause_requested.connect(self._pause_active_timer)
        self.mini_widget_controller.stop_requested.connect(self._stop_active_timer)
        
    def _setup_history_view_controller(self):
        """Initializes the history view controller."""
        self.history_controller = HistoryViewController(
            self.view.history_view,
            self.db_service,
            self.jira_service
        )
        self.history_controller.issue_opened.connect(self._open_issue_from_history)
        
    def _setup_sync_queue_monitor(self):
        """Sets up a timer to periodically check the sync queue."""
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._update_sync_status)
        self.sync_timer.start(10000)  # Check every 10 seconds
        
        # Initial status check only if db_service exposes the expected methods
        try:
            if hasattr(self.db_service, 'get_pending_sync_operations') and hasattr(self.db_service, 'get_failed_sync_operations'):
                self._update_sync_status()
        except Exception:
            # If db_service is a dummy or missing methods, skip initial check
            pass
        
    def _setup_notification_controller(self):
        """Sets up the notification controller."""
        self.notification_controller = NotificationController(
            self.db_service,
            self.jira_service
        )
        
        # Connect notification count changes to the indicator
        self.notification_controller.notification_count_changed.connect(self.view.update_notification_count)
        
        # Start notification checks (will check immediately once)
        self.notification_controller.start_notification_checks()
        
    def _setup_attachment_controller(self):
        """Sets up the attachment controller."""
        from controllers.attachment_controller import AttachmentController
        
        # Create the attachment controller with the attachment service
        # that was created in main.py and assigned to this controller
        self.attachment_controller = AttachmentController(
            self.db_service,
            self.jira_service,
            self.app_settings,
            attachment_service=getattr(self, 'attachment_service', None)
        )
        
    def _setup_network_monitoring(self):
        """Sets up the network monitoring service."""
        # Initial network status
        self.is_internet_available = False
        self.is_jira_available = False
        
        # Intervallo di controllo: 30 secondi
        self.network_service = NetworkService(self.jira_service, check_interval=30000)
        
        # Connect signals for network status changes
        self.network_service.connection_changed.connect(self._on_internet_connection_changed)
        self.network_service.jira_connection_changed.connect(self._on_jira_connection_changed)
        
        # Start the monitoring
        self.network_service.start_monitoring()

    def _connect_signals(self):
        """Connect signals from the view to controller slots."""
        # Connect navigation signals from FluentWindow interface
        self.view.lastActiveRequested.connect(self._show_last_active_jira)
        self.view.settingsRequested.connect(self._show_settings_dialog)
        self.view.searchJqlRequested.connect(self._show_jql_history_dialog)
        self.view.notesRequested.connect(self._show_notes_manager_dialog)
        self.view.syncQueueRequested.connect(self._show_sync_queue_dialog)
        self.view.notificationsRequested.connect(self._show_notifications_dialog)
        self.view.check_connection_requested.connect(self._check_connection_manually)

        # Connect signals for data loading
        self.data_loaded.connect(self._on_data_loaded)
        self.load_failed.connect(self._on_load_failed)

        # Connect grid-specific signals
        # Keep instant client-side filtering while typing
        self.view.jira_grid_view.search_box.textChanged.connect(self._filter_grid)
        # When the user presses Enter in the search box, perform a server-side search
        try:
            self.view.jira_grid_view.search_box.returnPressed.connect(self._on_search_requested)
        except Exception:
            try:
                # Fallback for widgets that expose editingFinished instead
                self.view.jira_grid_view.search_box.editingFinished.connect(self._on_search_requested)
            except Exception:
                pass
        self.view.jira_grid_view.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.view.jira_grid_view.table.doubleClicked.connect(self._open_detail_view)
        
        # Monitor item selection in the grid table
        self.view.jira_grid_view.table.itemSelectionChanged.connect(self._on_grid_selection_changed)
        # Installa event filter sulla tabella per monitorare gli eventi del mouse
        self.view.jira_grid_view.table.installEventFilter(self)
        
        self.view.jira_grid_view.apply_jql_btn.clicked.connect(self._apply_custom_jql)
        self.view.jira_grid_view.jql_combo.currentIndexChanged.connect(self._on_jql_combo_changed)
        self.view.jira_grid_view.favorites_btn.clicked.connect(self._on_favorites_toggled)
        
        # Connect notification button in JiraGridView
        self.view.jira_grid_view.notifications_btn.clicked.connect(self._show_notifications_dialog)
        
        # Connect sorting completed signal to reconnect favorite buttons
        self.view.jira_grid_view.sorting_completed.connect(self._reconnect_favorite_buttons)

        # Install event filter on JQL combo box to handle Enter key
        self.view.jira_grid_view.jql_combo.installEventFilter(self)

        # Connect main window state changes for mini widget
        self.view.windowStateChanged.connect(self._on_window_state_changed)
        
        # Connect main window closing signal
        self.view.closing.connect(self._on_main_window_closing)

    def _apply_always_on_top(self):
        """Reads the persisted always_on_top setting and applies it to the main window
        and any currently open detail windows."""
        try:
            # Use central helper which reads settings and applies flags
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(self.view, app_settings=self.app_settings)
        except Exception:
            pass

        # Apply to any open detail windows
        for win in list(self.open_detail_windows.values()):
            try:
                try:
                    from services.ui_utils import apply_always_on_top
                    apply_always_on_top(win, app_settings=self.app_settings)
                except Exception:
                    pass
            except Exception:
                pass
                
    def _on_grid_selection_changed(self):
        """Monitors selection changes in the grid table."""
        self._logger.info("[DEBUG] Selezione nella griglia cambiata")
        selected = self.view.jira_grid_view.table.selectedItems()
        if selected:
            try:
                # Get the selected row
                row = selected[0].row()
                key_item = self.view.jira_grid_view.table.item(row, 0)
                if key_item:
                    issue_key = key_item.text()
                    self._logger.debug(f"[DEBUG] Riga selezionata: {row}, Issue Key: {issue_key}")
                    self._logger.debug(f"[DEBUG] Finestre di dettaglio aperte: {list(self.open_detail_windows.keys())}")
                    # Verifica se la finestra di dettaglio è attualmente aperta
                    if issue_key in self.open_detail_windows:
                        detail_window = self.open_detail_windows[issue_key]
                        self._logger.debug(f"[DEBUG] La finestra di dettaglio per {issue_key} è attualmente aperta. IsVisible: {detail_window.isVisible()}, IsHidden: {detail_window.isHidden()}")
                    # Tracciamento stack per vedere da dove viene chiamato
                    import traceback
                    self._logger.debug(f"[DEBUG] Stack trace:\n{traceback.format_stack()}")
            except Exception as e:
                self._logger.exception(f"[DEBUG] Errore durante l'elaborazione della selezione: {e}")

    def show_initial_view(self):
        """Shows the default view and triggers data loading."""
        # Set the initial interface to the Jira grid
        self.view.navigationInterface.setCurrentItem(self.view.jira_grid_view.objectName())
        
        # Populate JQL favorites dropdown
        self._populate_jql_favorites()
        
        # Ripristina lo stato del filtro dei preferiti se era attivo
        favorites_filter_enabled = self.app_settings.get_setting('favorites_filter_enabled', 'false').lower() == 'true'
        if favorites_filter_enabled:
            self._on_favorites_toggled(True)
        
        # Initialize history view
        self.history_controller.load_history()
        
        # Aggiorna lo stato della connessione
        self.view.update_network_status(self.is_internet_available, self.is_jira_available)
        
        # Start Jira issues loading asynchronously
        self.load_jira_issues()

    def load_jira_issues(self, append=False, favorite_keys: list[str] | None = None, custom_jql: str | None = None, send_jql: str | None = None):
        """
        Fetches Jira issues in a background thread.
        - append: If True, adds issues to the existing list.
        - favorite_keys: If provided, searches only for these keys.
        - custom_jql: If provided, overrides the default JQL.
        """
        if self.is_loading:
            return

        if not append:
            self.current_issues = []
            self.start_at = 0
            self.all_results_loaded = False
            self.view.jira_grid_view.clear_table()

        if self.all_results_loaded:
            return

        self.is_loading = True
        self.view.jira_grid_view.show_loading(True)

        # Determine the JQL shown in the input (the user's custom JQL) and the JQL actually
        # sent to the server (send_jql). We must not overwrite the user's input field with the
        # combined JQL used for the server-side search so that clearing the small filter box
        # won't remove the original JQL text.
        input_jql = custom_jql if custom_jql is not None else self.app_settings.get_setting(
            'last_used_jql',
            self.app_settings.get_setting('jql_query', 'assignee = currentUser() AND status != "Done"'),
        )
        self.view.jira_grid_view.set_jql_text(input_jql) # Update the input field

        # The actual JQL to send to Jira (may be a combined version including filters)
        jql = send_jql if send_jql is not None else input_jql
        
        # Verifica se siamo online o offline
        if not self.is_internet_available or not self.is_jira_available:
            self._logger.info("Modalità offline: caricamento solo dei preferiti salvati localmente")
            self.is_loading = False
            self.view.jira_grid_view.show_loading(False)
            
            # In modalità offline, mostriamo solo i preferiti dal database locale
            try:
                # Ottieni tutte le chiavi preferite
                favorite_keys = self.db_service.get_all_favorites()
                
                if not favorite_keys:
                    self.view.jira_grid_view.show_error(
                        "Modalità offline: nessun ticket preferito trovato.\n"
                        "Quando la connessione sarà ripristinata, potrai caricare tutti i ticket."
                    )
                    self.all_results_loaded = True
                    return
                
                # Carichiamo i dati di base per questi preferiti
                offline_issues = []
                for key in favorite_keys:
                    # Costruiamo un oggetto simile a quello che restituirebbe Jira
                    # ma con i dati minimi disponibili localmente
                    issue_data = {
                        'key': key,
                        'fields': {
                            'summary': f"{key} (dati offline)",
                            'status': {'name': 'Unknown'},
                            'timespent': 0  # Useremo i dati locali
                        }
                    }
                    offline_issues.append(issue_data)
                
                # Chiamiamo direttamente il metodo di gestione dei dati caricati
                self._on_data_loaded(offline_issues)
                self.view.jira_grid_view.title_label.setText("Jira (Modalità Offline)")
                self.all_results_loaded = True  # Previene il caricamento infinito
                
                # Aggiungiamo un messaggio informativo
                self.view.jira_grid_view.show_info(
                    "Modalità offline attiva: vengono mostrati solo i ticket preferiti salvati localmente.\n"
                    "Quando la connessione sarà ripristinata, potrai caricare tutti i ticket."
                )
                
                return
            except Exception as e:
                self._logger.error(f"Errore nel caricamento dei dati offline: {e}")
                self.view.jira_grid_view.show_error(
                    f"Errore nel caricamento dei dati offline: {str(e)}\n"
                    "Riprova quando la connessione sarà disponibile."
                )
                self.is_loading = False
                return

        # Modalità online: carica i dati da Jira come di consueto
        # Create a dedicated thread for this load operation and keep references
        thread = QThread()
        worker = JiraWorker(self.jira_service, jql, self.start_at, favorite_keys=favorite_keys)
        worker.moveToThread(thread)

        # Wire up signals
        thread.started.connect(worker.run)
        # Connect signals for success and failure
        worker.finished.connect(self._on_data_loaded)
        worker.error.connect(self._on_load_failed)

        # Ensure the thread and worker are cleaned up when finished or on error
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Track thread and worker so they are not garbage-collected
        self._active_threads.append(thread)
        self._active_workers.append(worker)

        # Remove thread and worker from tracking when thread finishes
        def _on_thread_finished(t=thread, w=worker):
            try:
                if t in self._active_threads:
                    self._active_threads.remove(t)
            except Exception:
                pass
            try:
                if w in self._active_workers:
                    self._active_workers.remove(w)
            except Exception:
                pass

        thread.finished.connect(_on_thread_finished)

        thread.start()

        # Log that a background load started
        try:
            self._logger.debug("Started Jira load thread for JQL: %s (start_at=%s)", jql, self.start_at)
        except Exception:
            pass


    def _on_data_loaded(self, issues: list):
        """Slot to handle successfully loaded Jira issue data."""
        try:
            self._logger.debug("_on_data_loaded called with %s issues", len(issues) if issues is not None else 0)
        except Exception:
            pass

        self.is_loading = False
        self.view.jira_grid_view.show_loading(False)

        if not issues:
            self.all_results_loaded = True
            if not self.current_issues:
                self.view.jira_grid_view.show_error("No issues found for the current filter.")
            return

        self.start_at += len(issues)
        self.current_issues.extend(issues)
        
        # Get all local times at once to avoid multiple DB calls in a loop
        local_times = self.db_service.get_all_local_times()

        # Temporarily disconnect the filter signal to avoid re-filtering during population
        self.view.jira_grid_view.search_box.textChanged.disconnect(self._filter_grid)
        
        for issue in issues:
            self._add_issue_to_grid(issue, local_times)

        # Reconnect and apply current filter
        self.view.jira_grid_view.search_box.textChanged.connect(self._filter_grid)
        self._filter_grid(self.view.jira_grid_view.search_box.text())


    def _on_load_failed(self, error_message: str):
        """Slot to handle data loading failures."""
        self.is_loading = False
        # Log the error so it is visible in file/console
        try:
            self._logger.error("Jira data load failed: %s", error_message)
        except Exception:
            pass
        # Show error in UI (defensively - some InfoBar implementations may not expose the same API)
        try:
            self.view.jira_grid_view.show_error(error_message)
        except Exception:
            try:
                # Fallback: use a simple message box so the user still sees the error
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Errore", str(error_message))
            except Exception:
                # As a last resort, update the loading overlay if present
                try:
                    self.view.jira_grid_view.loading_overlay.setVisible(False)
                except Exception:
                    pass

    def _add_issue_to_grid(self, issue_data: dict, local_times: dict):
        """Adds a single issue to the grid view's table."""
        grid = self.view.jira_grid_view
        table = grid.table
        row_position = table.rowCount()
        table.insertRow(row_position)
        
        jira_key = issue_data['key']
        
        # Calculate total time
        jira_seconds = issue_data.get('fields', {}).get('timespent') or 0
        local_seconds = local_times.get(jira_key, 0)
        total_seconds = jira_seconds + local_seconds
        
        # Format time for display
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}m"

        # Get status for coloring
        status_name = issue_data.get('fields', {}).get('status', {}).get('name', '')
        
        # Get priority information
        priority_data = issue_data.get('fields', {}).get('priority', {})
        priority_name = priority_data.get('name', '')
        
        # Create items
        key_item = QTableWidgetItem(jira_key)
        title_item = QTableWidgetItem(issue_data.get('fields', {}).get('summary', ''))
        status_item = QTableWidgetItem(status_name)
        priority_item = QTableWidgetItem(priority_name)
        time_item = QTableWidgetItem(time_str)
        
        # Apply status color if available
        color_hex = self.db_service.get_status_color(status_name)
        if color_hex:
            from PyQt6.QtGui import QColor, QBrush
            color = QColor(color_hex)
            # Use a lighter version of the color for better text visibility
            color.setAlpha(40)  # Semi-transparent
            brush = QBrush(color)
            key_item.setBackground(brush)
            title_item.setBackground(brush)
            status_item.setBackground(brush)
            priority_item.setBackground(brush)
            time_item.setBackground(brush)
        
        # Add items to table
        table.setItem(row_position, 0, key_item)
        table.setItem(row_position, 1, title_item)
        table.setItem(row_position, 2, status_item)
        
        # Priority column - create combobox for local editing
        priority_combo = self._create_priority_combo(jira_key, priority_name)
        table.setCellWidget(row_position, 3, priority_combo)
        
        table.setItem(row_position, 4, time_item)
        
        # Favorite button logic
        from qfluentwidgets import TransparentToolButton
        
        fav_button = TransparentToolButton()
        fav_button.setCheckable(True)
        is_fav = jira_key in self.db_service.get_all_favorites()
        fav_button.setChecked(is_fav)
        fav_button.setText("★" if is_fav else "☆")
        fav_button.clicked.connect(lambda _, key=jira_key, btn=fav_button: self._toggle_favorite(key, btn))
        table.setCellWidget(row_position, 5, fav_button)
        
    def _create_priority_combo(self, jira_key: str, current_priority: str = ""):
        """Create a priority combobox for the given Jira key."""
        from PyQt6.QtWidgets import QComboBox
        
        priority_combo = QComboBox()
        priority_combo.addItem("", "")
        priority_combo.addItem("Highest", "1")
        priority_combo.addItem("High", "2")
        priority_combo.addItem("Medium", "3")
        priority_combo.addItem("Low", "4")
        priority_combo.addItem("Lowest", "5")
        
        # Get local priority override if exists
        local_priority = self.db_service.get_local_priority(jira_key)
        if local_priority:
            # Use local priority
            priority_name = local_priority.get('name', '')
            index = priority_combo.findText(priority_name)
            if index >= 0:
                priority_combo.setCurrentIndex(index)
        elif current_priority:
            # Use current priority from Jira
            index = priority_combo.findText(current_priority)
            if index >= 0:
                priority_combo.setCurrentIndex(index)
        
        # Connect change signal
        priority_combo.currentTextChanged.connect(
            lambda text, key=jira_key: self._on_priority_changed(key, text)
        )
        
        return priority_combo
        
    def _on_priority_changed(self, jira_key: str, priority_name: str):
        """Handle priority change in the grid combobox."""
        try:
            # Get priority ID for the name
            priority_id = self._get_priority_id_for_name(priority_name)
            
            # Save the local priority override
            if priority_name and priority_id:
                self.db_service.set_local_priority(jira_key, priority_id, priority_name)
            else:
                self.db_service.remove_local_priority(jira_key)
                
            # Add to sync queue if auto_sync is enabled and we're online
            auto_sync = self.app_settings.get_setting("auto_sync", "false").lower() == "true"
            if auto_sync and self.is_jira_available and priority_id:
                import json
                payload = json.dumps({
                    "jira_key": jira_key,
                    "priority_id": priority_id
                })
                self.db_service.add_to_sync_queue("UPDATE_PRIORITY", payload)
                    
        except Exception as e:
            self._logger.error(f"Error updating priority for {jira_key}: {e}")
            
    def _get_priority_id_for_name(self, priority_name: str) -> str:
        """Get the priority ID for a given priority name."""
        priority_map = {
            "Highest": "1",
            "High": "2", 
            "Medium": "3",
            "Low": "4",
            "Lowest": "5"
        }
        return priority_map.get(priority_name, "")

    def _toggle_favorite(self, jira_key: str, button: QPushButton):
        """Toggles the favorite status of an issue."""
        if self.db_service.is_favorite(jira_key):
            self.db_service.remove_favorite(jira_key)
            button.setText("☆")
            button.setChecked(False)
        else:
            self.db_service.add_favorite(jira_key)
            button.setText("★")
            button.setChecked(True)
        
        # If the favorite filter is active, we need to refresh the view
        if self.view.jira_grid_view.favorites_btn.isChecked():
            self._on_favorites_toggled(True)
            
    def _reconnect_favorite_buttons(self):
        """Reconnect all favorite buttons and priority comboboxes after sorting is completed."""
        try:
            table = self.view.jira_grid_view.table
            
            # Find the favorite and priority column indices
            favorite_col_index = -1
            priority_col_index = -1
            visible_columns = self.view.jira_grid_view.get_visible_columns()
            for i, col in enumerate(visible_columns):
                col_id = col.get('id')
                if col_id == 'favorite':
                    favorite_col_index = i
                elif col_id == 'priority':
                    priority_col_index = i
            
            # Reconnect all widgets
            for row in range(table.rowCount()):
                # Get the Jira key from the first column
                key_item = table.item(row, 0)
                if not key_item:
                    continue
                    
                jira_key = key_item.text()
                
                # Reconnect favorite button
                if favorite_col_index >= 0:
                    fav_button = table.cellWidget(row, favorite_col_index)
                    if fav_button:
                        # Disconnect any existing connections
                        try:
                            fav_button.clicked.disconnect()
                        except TypeError:
                            pass  # No connections to disconnect
                        
                        # Reconnect with the correct jira_key
                        fav_button.clicked.connect(lambda _, key=jira_key, btn=fav_button: self._toggle_favorite(key, btn))
                
                # Reconnect priority combobox
                if priority_col_index >= 0:
                    priority_combo = table.cellWidget(row, priority_col_index)
                    if priority_combo and hasattr(priority_combo, 'currentTextChanged'):
                        # Disconnect any existing connections
                        try:
                            priority_combo.currentTextChanged.disconnect()
                        except TypeError:
                            pass  # No connections to disconnect
                        
                        # Reconnect with the correct jira_key
                        priority_combo.currentTextChanged.connect(
                            lambda text, key=jira_key: self._on_priority_changed(key, text)
                        )
                    
        except Exception as e:
            self._logger.error(f"Error reconnecting widgets: {e}")
            import traceback
            self._logger.error(traceback.format_exc())


    def _on_scroll(self, value):
        """
        Handles the scroll event to trigger infinite scrolling.
        Req: 2.3.4 (infinite scroll)
        """
        scroll_bar = self.view.jira_grid_view.table.verticalScrollBar()
        # Load more when the user is within 10% of the bottom
        if value >= scroll_bar.maximum() * 0.9 and not self.is_loading:
            self.load_jira_issues(append=True)

    def _show_settings_dialog(self):
        """Opens the settings dialog."""
        from views.config_dialog import ConfigDialog
        from controllers.config_controller import ConfigController
        
        # Create dialog without parent for true independence
        config_dialog = ConfigDialog(parent=None)
        
        # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
        try:
            config_dialog.setWindowFlag(Qt.WindowType.Window, True)
            config_dialog.setModal(False)
        except Exception:
            pass
            
        config_controller = ConfigController(
            config_dialog, 
            self.jira_service, 
            self.app_settings, 
            self.db_service.credential_service
        )
        
        # Apply changes immediately when settings are saved
        try:
            config_controller.settings_saved.connect(self._apply_always_on_top)
        except Exception:
            pass
            
        # Track the dialog window
        self._open_dialog_windows.append(config_dialog)
        from functools import partial
        config_dialog.destroyed.connect(partial(self._on_dialog_window_closed, config_dialog))
        
        # Set DB service
        config_controller.set_db_service(self.db_service)
        
        # Show the dialog now
        config_dialog.show()
        config_dialog.raise_()
        config_dialog.activateWindow()
        
        # Finish controller setup (might do other initialization)
        config_controller.run()
        
        # Re-apply settings after dialog is shown in case defaults need to be applied
        try:
            self._apply_always_on_top()
        except Exception:
            pass
        
    def _filter_grid(self, text: str):
        """
        Filters the grid rows based on the search text.
        Req: 2.3.2 (search bar)
        """
        table = self.view.jira_grid_view.table
        search_term = text.lower()
        for row in range(table.rowCount()):
            key_item = table.item(row, 0)
            title_item = table.item(row, 1)
            
            if not key_item:
                continue
                
            # Check if item text contains the search term
            key_match = search_term in key_item.text().lower()
            title_match = title_item and search_term in title_item.text().lower()

            # Also consider favorite status if the favorites filter is active
            is_favorite = self.db_service.is_favorite(key_item.text())
            show_only_favorites = self.view.jira_grid_view.favorites_btn.isChecked()

            should_be_visible = (key_match or title_match) and (not show_only_favorites or is_favorite)

            if should_be_visible:
                table.setRowHidden(row, False)
            else:
                table.setRowHidden(row, True)

    def _append_search_filter_to_jql(self, jql: str | None, search_text: str) -> str:
        """
        Append a search filter to a JQL query using Jira's contains operator (~).
        The search is appended as: AND (summary ~ "text" OR description ~ "text" OR comment ~ "text")
        Preserves an existing ORDER BY clause by inserting the filter before it.
        If no base JQL is provided, returns only the filter clause so the loader can use it.
        """
        if not search_text:
            return jql or ""

        s = search_text.strip()
        if not s:
            return jql or ""

        # Allow users to use SQL-style '%' as a wildcard in the search box by mapping
        # '%' -> '*' (Lucene wildcard) before escaping. Jira's text search (~) understands
        # Lucene syntax and uses '*' as a wildcard; '%' is not recognized by JQL.
        # Note: leading wildcards can be expensive on server-side searches.
        try:
            s = s.replace('%', '*')
        except Exception:
            pass

        # Basic escaping for quotes and backslashes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')

        # Determine if the search term looks like an issue key (e.g. PROJ-123)
        key_like = False
        try:
            # Accept formats like ABC-123, or project.key-123 (conservative)
            if re.match(r'^[A-Za-z0-9._]+-\d+$', s):
                key_like = True
        except Exception:
            key_like = False

        if key_like:
            # When the user typed an apparent issue key, use exact match for key (operator '='),
            # because Jira does not allow '~' on the key field on some instances.
            clause = (
                f'(key = "{escaped}" OR summary ~ "{escaped}" '
                f'OR description ~ "{escaped}" OR comment ~ "{escaped}")'
            )
        else:
            # Do not use '~' on key to avoid server-side errors; search in textual fields only
            # If the user didn't include any wildcard, wrap the term with '*' so it matches
            # substrings (SQL-style behavior). Preserve explicit wildcards if provided.
            try:
                if '*' not in s:
                    escaped = f'*{escaped}*'
            except Exception:
                pass

            clause = (
                f'(summary ~ "{escaped}" OR description ~ "{escaped}" OR comment ~ "{escaped}")'
            )

        base = (jql or "").strip()
        if not base:
            return clause

        # Preserve ORDER BY if present
        m = re.search(r"\bORDER\s+BY\b", base, flags=re.IGNORECASE)
        if m:
            idx = m.start()
            before = base[:idx].strip()
            order = base[idx:].strip()
            return f"{before} AND {clause} {order}"

        return f"{base} AND {clause}"

    def _apply_custom_jql(self):
        """Applies the custom JQL from the input field."""
        custom_jql = self.view.jira_grid_view.get_jql_text()
        if custom_jql:
            # Quando si applica una JQL personalizzata, disattiva il filtro dei preferiti
            if self.view.jira_grid_view.favorites_btn.isChecked():
                self.view.jira_grid_view.favorites_btn.setChecked(False)
                self._on_favorites_toggled(False)
            
            # Save the last used JQL query
            self.app_settings.set_setting('last_used_jql', custom_jql)
            
            # Add JQL to history
            self.db_service.add_jql_history(custom_jql)
            
            # Combine the custom JQL with the current search/filter box using a LIKE (~)
            search_filter = self.view.jira_grid_view.search_box.text()
            combined_jql = self._append_search_filter_to_jql(custom_jql, search_filter)

            # Load issues with the combined JQL (do not overwrite saved/custom jql history)
            self.load_jira_issues(append=False, custom_jql=custom_jql, send_jql=combined_jql)

    def _on_search_requested(self):
        """Trigger a server-side search using the current JQL and the search box text.

        This is invoked when the user presses Enter in the search box. It will combine the
        active JQL (from the JQL input or last-used JQL) with the search text and reload
        issues from Jira so the search is performed server-side rather than only filtering
        the existing in-memory table.
        """
        try:
            search_text = self.view.jira_grid_view.search_box.text().strip()
        except Exception:
            search_text = ""

        # Determine base JQL (prefer what the user has in the JQL input, fall back to last used)
        base_jql = self.view.jira_grid_view.get_jql_text() or self.app_settings.get_setting(
            'last_used_jql',
            self.app_settings.get_setting('jql_query', 'assignee = currentUser() AND status != "Done"'),
        )

        # If favorites filter is active, disable it because we're performing a broader search
        if self.view.jira_grid_view.favorites_btn.isChecked():
            self.view.jira_grid_view.favorites_btn.setChecked(False)
            self._on_favorites_toggled(False)

        # Build combined JQL and reload issues from server (don't overwrite the input field)
        combined = self._append_search_filter_to_jql(base_jql, search_text)
        self.load_jira_issues(append=False, custom_jql=base_jql, send_jql=combined)
            
    def _show_jql_history_dialog(self):
        """Shows the JQL history dialog."""
        try:
            self._logger.debug("Opening JQL history dialog...")
            jql_history_controller = JqlHistoryController(self.db_service, from_grid=True)
            
            # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
            try:
                jql_history_controller.view.setWindowFlag(Qt.WindowType.Window, True)
                jql_history_controller.view.setModal(False)
            except Exception:
                pass
                
            jql_history_controller.view.jql_selected.connect(self._on_jql_selected_from_history)
            
            # Track the dialog window
            self._open_dialog_windows.append(jql_history_controller.view)
            from functools import partial
            jql_history_controller.view.destroyed.connect(partial(self._on_dialog_window_closed, jql_history_controller.view))
            
            # Show the view now
            jql_history_controller.view.show()
            jql_history_controller.view.raise_()
            jql_history_controller.view.activateWindow()
            
            # Finish controller setup (might do other initialization)
            jql_history_controller.run()
            
            self._logger.debug("JQL history dialog opened successfully")
        except Exception as e:
            self._logger.error(f"Error opening JQL history dialog: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
        
    def _show_notes_manager_dialog(self):
        """Shows the notes manager dialog."""
        try:
            from views.notes_manager_dialog import NotesManagerDialog
            notes_dialog = NotesManagerDialog(self.db_service, self.app_settings, parent=None)  # No parent for top-level
            
            # Connect the signals
            notes_dialog.all_notes_requested.connect(self._show_notes_grid_dialog)
            notes_dialog.open_jira_detail_requested.connect(self._open_detail_from_key)
            notes_dialog.start_timer_requested.connect(self._start_timer_from_notes)
            
            # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
            try:
                notes_dialog.setWindowFlag(Qt.WindowType.Window, True)
                notes_dialog.setModal(False)
            except Exception:
                pass
            
            # Track the dialog window
            self._open_dialog_windows.append(notes_dialog)
            from functools import partial
            notes_dialog.destroyed.connect(partial(self._on_dialog_window_closed, notes_dialog))
            
            # Show the dialog now
            notes_dialog.show()
            notes_dialog.raise_()
            notes_dialog.activateWindow()
            
        except Exception as e:
            self._logger.error(f"Error opening notes manager dialog: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            
    def _show_notes_grid_dialog(self):
        """Shows the grid of all notes."""
        try:
            from views.notes_grid_dialog import NotesGridDialog
            grid_dialog = NotesGridDialog(self.db_service, parent=None)
            
            # Connect signals for opening Jira detail view and starting timer
            grid_dialog.open_jira_detail_requested.connect(self._open_detail_from_key)
            grid_dialog.start_timer_requested.connect(self._start_timer_from_notes)
            
            # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
            try:
                grid_dialog.setWindowFlag(Qt.WindowType.Window, True)
                grid_dialog.setModal(False)
            except Exception:
                pass
            
            # Track the dialog window
            self._open_dialog_windows.append(grid_dialog)
            from functools import partial
            grid_dialog.destroyed.connect(partial(self._on_dialog_window_closed, grid_dialog))
            
            # Show the dialog now
            grid_dialog.show()
            grid_dialog.raise_()
            grid_dialog.activateWindow()
            
        except Exception as e:
            self._logger.error(f"Error opening notes grid dialog: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            
    def _open_detail_from_key(self, jira_key):
        """Opens a detail view for a Jira issue identified by key."""
        if not jira_key or not jira_key.strip():
            return
            
        jira_key = jira_key.strip()
        self._logger.info(f"Opening detail for: {jira_key}. Currently open: {list(self.open_detail_windows.keys())}")
        
        # Set flag to prevent automatic closures during opening
        self._opening_detail_window = True
        
        try:
            # Check if a window for this issue is already open
            if jira_key in self.open_detail_windows:
                self._logger.info(f"Window for {jira_key} already open, activating...")
                self.open_detail_windows[jira_key].activateWindow()
                return
                
            # Limit the number of open detail windows to prevent too many open at once
            MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
            if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
                # Close the oldest detail window
                oldest_key = next(iter(self.open_detail_windows))
                self._logger.info(f"Reached limit ({MAX_DETAIL_WINDOWS}), closing oldest: {oldest_key}")
                self._close_detail_window(oldest_key)
                
            # Create a new detail view
            from views.jira_detail_view import JiraDetailView
            from controllers.jira_detail_controller import JiraDetailController

            detail_window = JiraDetailView(jira_key, parent=None)  # No parent for top-level
            
            # Ensure this widget is a top-level window (not an embedded child)
            try:
                detail_window.setWindowFlag(Qt.WindowType.Window, True)
            except Exception:
                pass
                
            detail_controller = JiraDetailController(
                detail_window, 
                self.jira_service, 
                self.db_service,
                jira_key
            )
            
            # Store controller on the window to keep it alive
            detail_window.controller = detail_controller 
            
            detail_controller._load_data()
            self.open_detail_windows[jira_key] = detail_window
            self._logger.info(f"Added {jira_key} to tracking. Open windows: {list(self.open_detail_windows.keys())}")
            # Usiamo solo il segnale window_closed e non destroyed per evitare doppie chiamate
            # detail_window.destroyed.connect(lambda: self._on_detail_window_closed(jira_key))
            detail_controller.window_closed.connect(self._on_detail_window_closed)
            detail_controller.timer_started.connect(self._on_timer_started)
            detail_controller.timer_stopped.connect(self._on_timer_stopped)
            detail_controller.time_updated.connect(self._on_time_updated)
            
            # Adjust window flags for proper stacking
            self._adjust_window_flags_for_detail(detail_window)
            
            # Show the window
            detail_window.show()
            detail_window.raise_()
            detail_window.activateWindow()
        
        finally:
            # Always reset the flag
            self._opening_detail_window = False
        
    def _on_jql_selected_from_history(self, query):
        """Applies a JQL query selected from the history dialog."""
        # Update the JQL input field
        self.view.jira_grid_view.set_jql_text(query)
        
        # Save the last used JQL query
        self.app_settings.set_setting('last_used_jql', query)
        
        # Apply the query
        self._apply_custom_jql()
        
    def _on_jql_combo_changed(self, index):
        """Handles changes in the JQL combo box selection."""
        if index < 0:
            return
            
        # Get the selected item data
        combo = self.view.jira_grid_view.jql_combo
        selected_data = combo.itemData(index)
        current_text = combo.currentText()
        
        # If "Gestisci cronologia e preferiti..." is selected, show the dialog
        if selected_data is None and current_text == "📚 Gestisci cronologia e preferiti...":
            # Temporarily disconnect the signal to avoid recursion
            combo.currentIndexChanged.disconnect(self._on_jql_combo_changed)
            
            # Show the dialog
            self._show_jql_history_dialog()
            
            # Reset to first item or clear selection after dialog closes
            if combo.count() > 1:  # More than just the management option
                combo.setCurrentIndex(0)
            else:
                combo.setCurrentText("")
            
            # Reconnect the signal
            combo.currentIndexChanged.connect(self._on_jql_combo_changed)
            
        elif selected_data is not None:
            # A favorite query was selected, set it in the input field and save as last used
            self.view.jira_grid_view.set_jql_text(selected_data)
            self.app_settings.set_setting('last_used_jql', selected_data)
            self._apply_custom_jql()
    
    def _populate_jql_favorites(self):
        """Populates the JQL combo box with favorite queries."""
        favorites = self.db_service.get_favorite_jqls()
        self.view.jira_grid_view.populate_jql_favorites(favorites)

    def _on_favorites_toggled(self, checked=None):
        """Reloads the issue list, applying the favorite filter if checked."""
        # Se checked non è fornito, ottieni lo stato dal pulsante
        if checked is None:
            checked = self.view.jira_grid_view.favorites_btn.isChecked()
        else:
            # Se checked è fornito, imposta lo stato del pulsante
            self.view.jira_grid_view.favorites_btn.setChecked(checked)
        
        # Salva lo stato del filtro nei settings
        self.app_settings.set_setting('favorites_filter_enabled', 'true' if checked else 'false')
        
        # Inizializza favorite_keys a None (verrà impostato solo se checked è True)
        favorite_keys = None
        
        # Aggiorna l'aspetto del pulsante
        if checked:
            # Cambia il titolo per indicare che stiamo visualizzando i preferiti
            self.view.jira_grid_view.title_label.setText("Jira Favorite")
            
            # Cambia il testo del pulsante per indicare che è attivo
            self.view.jira_grid_view.favorites_btn.setText("★")
            # Cambia il colore del pulsante per indicare che è attivo
            self.view.jira_grid_view.favorites_btn.setStyleSheet("""
                TransparentToolButton {
                    background-color: rgba(52, 152, 219, 0.2);
                    border: 1px solid rgba(52, 152, 219, 0.5);
                    border-radius: 4px;
                }
            """)
            
            favorite_keys = self.db_service.get_all_favorites()
            if not favorite_keys:
                self.view.jira_grid_view.clear_table()
                self.view.jira_grid_view.show_error("Non hai ticket preferiti.")
                self.all_results_loaded = True # Prevent scroll loading
                return
        else:
            # Ripristina il titolo originale della vista
            self.view.jira_grid_view.title_label.setText("Griglia Jira")
            
            # Ripristina il testo del pulsante
            self.view.jira_grid_view.favorites_btn.setText("☆")
            # Ripristina il colore del pulsante normale
            self.view.jira_grid_view.favorites_btn.setStyleSheet("")

        # Trigger a full reload
        self.load_jira_issues(append=False, favorite_keys=favorite_keys)

    def _adjust_window_flags_for_detail(self, detail_window):
        """Ensure detail_window appears above main when main is always-on-top.

        We avoid destructive flag resets. Sequence:
        - First try a non-invasive approach:
          * mark the detail window with WindowStaysOnTopHint, show/raise it and activate it
          * reapply always-on-top to main then re-raise the detail to ensure stacking
        - If that path fails, fall back to temporarily clearing the main's on-top, showing
          the detail and reapplying main's on-top afterwards.
        """
        try:
            from PyQt6.QtCore import Qt, QTimer
            from services.ui_utils import apply_always_on_top

            # Non-invasive attempt: mark detail as temporary always-on-top and show it
            try:
                try:
                    logger.debug("Attempt non-invasive raise: main flags=%s, main_opacity=%s",
                                 int(self.view.windowFlags()),
                                 self.view.windowOpacity() if hasattr(self.view, 'windowOpacity') else None)
                except Exception:
                    pass

                # Ensure detail is top-level and not frameless/translucent
                try:
                    detail_window.setWindowFlag(Qt.WindowType.Window, True)
                except Exception:
                    pass
                try:
                    # Clear frameless hint using non-destructive API where available
                    try:
                        detail_window.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
                    except Exception:
                        # Fallback to bitmask change if needed
                        df = detail_window.windowFlags() & ~Qt.WindowType.FramelessWindowHint
                        detail_window.setWindowFlags(df)
                except Exception:
                    pass
                try:
                    detail_window.setAttribute(detail_window.WA_TranslucentBackground, False)
                except Exception:
                    pass
                try:
                    detail_window.setWindowOpacity(1.0)
                except Exception:
                    pass

                # Give the detail window an on-top hint and show it
                try:
                    detail_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                except Exception:
                    pass

                detail_window.show()
                detail_window.raise_()
                detail_window.activateWindow()

                # After a short delay reapply main always-on-top and then re-raise the detail
                def _reapply_and_raise_detail():
                    try:
                        # Reapply flags but do not force a raise on main; we'll re-raise the detail
                        from services.ui_utils import apply_always_on_top
                        apply_always_on_top(self.view, self.app_settings, raise_window=False)
                    except Exception:
                        logger.exception('Failed to reapply always-on-top on main (non-invasive path)')
                    try:
                        # ensure the detail stays above by raising it again
                        detail_window.raise_()
                        detail_window.activateWindow()
                    except Exception:
                        pass

                QTimer.singleShot(200, _reapply_and_raise_detail)
                return
            except Exception:
                logger.exception('Non-invasive raise failed, falling back to temporary main toggle')

            # Fallback: temporarily clear always-on-top on main, normalize detail and show it,
            # then reapply main always-on-top after a short delay.
            try:
                main_flags = self.view.windowFlags()
                try:
                    logger.debug("Fallback: Main before adjust: flags=%s, opacity=%s, translucent=%s",
                                 int(self.view.windowFlags()),
                                 self.view.windowOpacity() if hasattr(self.view, 'windowOpacity') else None,
                                 self.view.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) if hasattr(self.view, 'testAttribute') else None)
                except Exception:
                    pass
                # Remove the always-on-top hint using a non-destructive API where possible
                try:
                    try:
                        self.view.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
                    except Exception:
                        main_flags = main_flags & ~Qt.WindowType.WindowStaysOnTopHint
                        self.view.setWindowFlags(main_flags)
                    # Process pending events so the flag change takes effect without
                    # forcing a show()/raise which would steal focus.
                    QApplication.processEvents()
                except Exception:
                    logger.exception('Failed to clear always-on-top on main (fallback)')
            except Exception:
                logger.exception('Failed to clear always-on-top on main (fallback)')

            # ensure detail is a normal window (no translucent/frameless styles)
            try:
                detail_flags = detail_window.windowFlags()
                try:
                    logger.debug("Detail before adjust (fallback): flags=%s, opacity=%s, translucent=%s",
                                 int(detail_window.windowFlags()),
                                 detail_window.windowOpacity() if hasattr(detail_window, 'windowOpacity') else None,
                                 detail_window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) if hasattr(detail_window, 'testAttribute') else None)
                except Exception:
                    pass
                # clear frameless and translucent hints if present using non-destructive API
                try:
                    detail_window.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
                except Exception:
                    detail_flags = detail_flags & ~Qt.WindowType.FramelessWindowHint
                    detail_window.setWindowFlags(detail_flags)
                try:
                    detail_window.setAttribute(detail_window.WA_TranslucentBackground, False)
                except Exception:
                    # attribute may not exist on all widgets
                    pass
                try:
                    detail_window.setWindowOpacity(1.0)
                except Exception:
                    pass
            except Exception:
                logger.exception('Failed to prepare detail window flags (fallback)')

            # show and raise the detail window
            try:
                detail_window.show()
                try:
                    logger.debug("Detail after show (fallback): flags=%s, opacity=%s, translucent=%s",
                                 int(detail_window.windowFlags()),
                                 detail_window.windowOpacity() if hasattr(detail_window, 'windowOpacity') else None,
                                 detail_window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) if hasattr(detail_window, 'testAttribute') else None)
                except Exception:
                    pass
                detail_window.raise_()
                detail_window.activateWindow()
            except Exception:
                logger.exception('Failed to show/raise/activate detail window (fallback)')

            # reapply always-on-top after a short delay
            def _reapply():
                try:
                    # Reapply flags but avoid raising main which could cover the detail
                    from services.ui_utils import apply_always_on_top
                    apply_always_on_top(self.view, self.app_settings, raise_window=False)
                except Exception:
                    logger.exception('Failed to reapply always-on-top on main (fallback)')

            QTimer.singleShot(150, _reapply)
        except Exception:
            logger.exception('Unexpected error in _adjust_window_flags_for_detail')

    def _open_detail_view(self, model_index):
        """Opens the detail view for the clicked issue."""
        row = model_index.row()
        key_item = self.view.jira_grid_view.table.item(row, 0)
        if not key_item:
            return

        issue_key = key_item.text()
        self._logger.info(f"Double-click opening detail for: {issue_key}. Currently open: {list(self.open_detail_windows.keys())}")

        # Set flag to prevent automatic closures during opening
        self._opening_detail_window = True
        
        try:
            # Check if a window for this issue is already open
            if issue_key in self.open_detail_windows:
                self._logger.info(f"Window for {issue_key} already open via double-click, activating...")
                self.open_detail_windows[issue_key].activateWindow()
                return
                
            # Limit the number of open detail windows to prevent too many open at once
            MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
            if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
                # Close the oldest detail window
                oldest_key = next(iter(self.open_detail_windows))
                self._logger.info(f"Reached limit ({MAX_DETAIL_WINDOWS}), closing oldest: {oldest_key}")
                self._close_detail_window(oldest_key)

            # Create a new detail view
            from views.jira_detail_view import JiraDetailView
            from controllers.jira_detail_controller import JiraDetailController

            detail_window = JiraDetailView(issue_key, parent=self.view)
            # Ensure this widget is a top-level window (not an embedded child)
            try:
                detail_window.setWindowFlag(Qt.WindowType.Window, True)
            except Exception:
                pass
            detail_controller = JiraDetailController(
                detail_window, 
                self.jira_service, 
                self.db_service,
                issue_key
            )

            # Store controller on the window to keep it alive
            detail_window.controller = detail_controller 

            detail_controller._load_data()
            self.open_detail_windows[issue_key] = detail_window
            self._logger.info(f"Added {issue_key} to tracking. Open windows: {list(self.open_detail_windows.keys())}")
            # Usiamo solo il segnale window_closed e non destroyed per evitare doppie chiamate
            # detail_window.destroyed.connect(lambda: self._on_detail_window_closed(issue_key))
            detail_controller.window_closed.connect(self._on_detail_window_closed)
            detail_controller.timer_started.connect(self._on_timer_started)
            detail_controller.timer_stopped.connect(self._on_timer_stopped)
            detail_controller.time_updated.connect(self._on_time_updated)

            # Initialize priority combo box with available priorities
            from controllers.priority_config_controller import PriorityConfigController
            if not hasattr(self, 'priority_controller'):
                self.priority_controller = PriorityConfigController(
                    self.db_service,
                    self.jira_service
                )
            
            # Populate priorities in the detail view
            priorities = self.priority_controller.get_available_priorities()
            detail_controller.populate_priority_combo(priorities)

            # Adjust window flags for proper stacking
            self._adjust_window_flags_for_detail(detail_window)
            
            # Show the window
            detail_window.show()
            detail_window.raise_()
            detail_window.activateWindow()
        
        finally:
            # Always reset the flag
            self._opening_detail_window = False

    def _show_last_active_jira(self):
        """Opens the detail view for the last active Jira issue."""
        last_active_key = self.app_settings.get_setting('last_active_jira')
        if not last_active_key:
            # Maybe show a message to the user? For now, just log it.
            # No last active Jira persisted — log and show a friendly message to the user
            try:
                self._logger.info("No last active Jira found.")
            except Exception:
                pass
            try:
                # Prefer a GUI message so the user understands why nothing opened
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self.view, "Nessun ticket attivo", "Non è stato trovato alcun ticket attivo di recente.")
            except Exception:
                # Fall back to logging if GUI message fails
                try:
                    self._logger.debug("Unable to show information dialog for missing last active Jira")
                except Exception:
                    pass
            return

        # This logic is duplicated from _open_detail_view.
        # We can simulate a model index or call a new shared method.
        # For simplicity, let's just open it directly.
        
        # Check if a window for this issue is already open
        if last_active_key in self.open_detail_windows:
            self.open_detail_windows[last_active_key].activateWindow()
            return
            
        # Limit the number of open detail windows to prevent too many open at once
        MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
        if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
            # Close the oldest detail window
            oldest_key = next(iter(self.open_detail_windows))
            self._close_detail_window(oldest_key)

        from views.jira_detail_view import JiraDetailView
        from controllers.jira_detail_controller import JiraDetailController
        # Parent to main window for consistent stacking
        detail_window = JiraDetailView(last_active_key, parent=self.view)
        try:
            detail_window.setWindowFlag(Qt.WindowType.Window, True)
        except Exception:
            pass
        detail_controller = JiraDetailController(
            detail_window, 
            self.jira_service, 
            self.db_service,
            last_active_key
        )
        
        detail_window.controller = detail_controller 
        
        detail_controller._load_data()
        self.open_detail_windows[last_active_key] = detail_window
        # Usiamo solo il segnale window_closed e non destroyed per evitare doppie chiamate
        # detail_window.destroyed.connect(lambda: self._on_detail_window_closed(last_active_key))
        detail_controller.window_closed.connect(self._on_detail_window_closed)
        detail_controller.timer_started.connect(self._on_timer_started)
        detail_controller.timer_stopped.connect(self._on_timer_stopped)
        detail_controller.time_updated.connect(self._on_time_updated)
        
        # Adjust window flags for proper stacking
        self._adjust_window_flags_for_detail(detail_window)
        
        # Show the window
        detail_window.show()
        detail_window.raise_()
        detail_window.activateWindow()


    def _on_timer_started(self, started_key: str):
        """Slot that is called when a timer starts in any detail window."""
        # Pause all other timers
        for key, window in self.open_detail_windows.items():
            if key != started_key:
                # Access controller via the stored attribute
                if hasattr(window, 'controller') and window.controller.is_running:
                    window.controller.pause_timer()
        
        self._active_timer_key = started_key
        self.app_settings.set_setting('last_active_jira', started_key)

    def _on_timer_stopped(self, jira_key: str):
        """Handles when a timer is fully stopped."""
        if self._active_timer_key == jira_key:
            self._active_timer_key = None
            self._active_timer_seconds = 0
            self._update_widget_display()
            
    def _on_timer_stopped_with_note(self, jira_key: str, seconds: int, note: str):
        """Handle when a timer is stopped in the mini timer dialog."""
        # Unset active timer
        if jira_key == self._active_timer_key:
            self._active_timer_key = None
            self._active_timer_seconds = 0
            self._update_widget_display()
            
        # Add the worklog entry if there is time tracked
        if seconds > 0:
            try:
                from datetime import datetime, timedelta, timezone
                from jira import JIRAError
                
                # Calculate start time based on now minus tracked seconds
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(seconds=seconds)
                
                # Add worklog to database
                self.db_service.add_local_worklog(
                    jira_key=jira_key,
                    start_time=start_time,
                    duration_seconds=seconds,
                    comment=note if note else None
                )
                
                # Reset the timer in the database
                self.db_service.reset_local_time(jira_key)
                
                # Verifica se il ticket è fittizio prima di aggiungerlo alla coda di sincronizzazione
                is_fictional = False
                if self.jira_service.is_connected():
                    try:
                        # Verifica se il ticket esiste su Jira
                        self.jira_service.get_issue(jira_key)
                    except JIRAError as e:
                        # Se è un errore 4xx, consideriamo il ticket come fittizio
                        if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                            is_fictional = True
                            self._logger.warning(f"Non sincronizzato worklog per ticket fittizio: {jira_key}")
                
                # Add to sync queue if auto_sync is enabled AND the ticket is not fictional
                auto_sync = self.app_settings.get_setting("auto_sync", "false").lower() == "true"
                if auto_sync and not is_fictional:
                    import json
                    payload = json.dumps({
                        "jira_key": jira_key,
                        "start_time": start_time.isoformat(),
                        "seconds": seconds,
                        "comment": note if note else ""
                    })
                    self.db_service.add_to_sync_queue("ADD_WORKLOG", payload)
                    self._logger.debug(f"Worklog added to sync queue for {jira_key}")
                elif is_fictional:
                    # Aggiungiamo un tag alle note per indicare che il ticket è fittizio (se non è già specificato)
                    fictional_tag = "[TICKET FITTIZIO]"
                    final_note = note
                    if not note or fictional_tag not in note:
                        final_note = f"{fictional_tag} {note if note else ''}"
                        
                    # Aggiorniamo il commento del worklog locale con il tag
                    self.db_service.update_local_worklog_comment(
                        jira_key=jira_key, 
                        start_time=start_time, 
                        comment=final_note
                    )
                    self._logger.info(f"Worklog salvato localmente per ticket fittizio: {jira_key}")
                    
                self._logger.debug(f"Worklog added for {jira_key}: {seconds}s with note: {note} (fittizio: {is_fictional})")
            except Exception as e:
                self._logger.error(f"Error adding worklog: {e}")

    def _on_time_updated(self, jira_key: str, total_seconds: int):
        """Receives time updates from the active timer."""
        if self._active_timer_key == jira_key:
            self._active_timer_seconds = total_seconds
            self._update_widget_display()

    def _ensure_detail_windows_visible(self):
        """Assicura che tutte le finestre di dettaglio siano visibili."""
        self._logger.debug(f"[DEBUG] Assicuro che tutte le {len(self.open_detail_windows)} finestre di dettaglio siano visibili")
        for key, window in self.open_detail_windows.items():
            if window.isHidden():
                self._logger.debug(f"[DEBUG] Finestra {key} era nascosta, la rendo visibile")
                window.show()
                window.raise_()
    
    def _get_open_dialog_windows(self):
        """Get list of currently open dialog windows."""
        windows = []
        try:
            # Add any open detail windows
            detail_windows = list(self.open_detail_windows.values())
            windows.extend(detail_windows)
            # Add tracked dialog windows
            windows.extend(self._open_dialog_windows)
            self._logger.debug(f"[DEBUG] _get_open_dialog_windows: Finestre dettaglio={len(detail_windows)}, Altri dialoghi={len(self._open_dialog_windows)}")
            # Verifica stato finestre di dettaglio
            for key, window in self.open_detail_windows.items():
                self._logger.debug(f"[DEBUG] _get_open_dialog_windows - Stato finestra {key}: IsVisible={window.isVisible()}, IsActive={window.isActiveWindow()}")
                
            # Assicuriamoci che le finestre di dettaglio siano sempre visibili
            self._ensure_detail_windows_visible()
            
        except Exception as e:
            self._logger.exception(f"[DEBUG] Errore in _get_open_dialog_windows: {e}")
        return windows

    def _on_dialog_window_closed(self, dialog_window):
        """Remove a dialog window from tracking when it's closed."""
        try:
            if dialog_window in self._open_dialog_windows:
                self._open_dialog_windows.remove(dialog_window)
        except Exception as e:
            self._logger.error(f"Error removing dialog window from tracking: {e}")

    def _on_detail_window_closed(self, jira_key: str):
        """Removes the detail window from the tracking dictionary when it's closed."""
        self._logger.debug(f"[DEBUG] _on_detail_window_closed chiamato per: {jira_key}")
        self._logger.debug(f"[DEBUG] Finestre aperte prima della chiusura: {list(self.open_detail_windows.keys())}")
        self._logger.debug(f"[DEBUG] Backtrace:", stack_info=True)
        
        # Proteggiamo contro le chiamate doppie
        # Se riceviamo un segnale destroyed dopo che la finestra è già stata rimossa dal dizionario
        if jira_key in self.open_detail_windows:
            del self.open_detail_windows[jira_key]
            self._logger.debug(f"[DEBUG] Finestra di dettaglio {jira_key} rimossa dal tracking. Finestre rimaste: {list(self.open_detail_windows.keys())}")
        else:
            self._logger.debug(f"[DEBUG] La finestra per {jira_key} era già stata rimossa o non era nel dizionario.")
    
    def _manage_detail_windows_limit(self):
        """Manages the limit of open detail windows, closing the oldest if necessary."""
        MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
        if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
            # Close the oldest detail window
            oldest_key = next(iter(self.open_detail_windows))
            self._close_detail_window(oldest_key)
            
    def _close_detail_window(self, jira_key):
        """Closes a specific detail window."""
        try:
            if jira_key in self.open_detail_windows:
                self._logger.debug(f"[DEBUG] _close_detail_window chiamato per: {jira_key}")
                window = self.open_detail_windows[jira_key]
                self._logger.debug(f"[DEBUG] Stato finestra prima della chiusura: IsVisible={window.isVisible()}, IsHidden={window.isHidden()}")
                
                # Chi sta chiamando la chiusura?
                import traceback
                self._logger.debug(f"[DEBUG] Backtrace della chiusura:\n{traceback.format_stack()}")
                
                # Controllare che non ci siano chiusure durante la selezione della griglia
                selected = self.view.jira_grid_view.table.selectedItems()
                if selected:
                    row = selected[0].row()
                    key_item = self.view.jira_grid_view.table.item(row, 0)
                    if key_item:
                        selected_key = key_item.text()
                        self._logger.debug(f"[DEBUG] Chiusura finestra mentre è selezionato: {selected_key}")
                        if selected_key == jira_key:
                            self._logger.warning(f"[DEBUG] ATTENZIONE: Stiamo chiudendo la stessa finestra che è selezionata nella griglia!")
                
                self._logger.debug(f"[DEBUG] Chiamando window.close() per {jira_key}")
                window.close()  # This will trigger the removal from the dictionary
                self._logger.debug(f"[DEBUG] window.close() eseguita per {jira_key}")
        except Exception as e:
            self._logger.error(f"Error closing detail window for {jira_key}: {e}")
            self._logger.exception(f"[DEBUG] Dettaglio errore per {jira_key}")
            
    def _close_all_detail_windows(self):
        """Closes all currently open detail windows."""
        # Don't close windows if we're in the middle of opening a new one
        if self._opening_detail_window:
            self._logger.info("Skipping close_all_detail_windows - currently opening a new window")
            return
            
        try:
            self._logger.info(f"Closing all detail windows: {list(self.open_detail_windows.keys())}")
            # Create a copy of the keys since we'll be modifying the dictionary
            keys_to_close = list(self.open_detail_windows.keys())
            
            for key in keys_to_close:
                try:
                    window = self.open_detail_windows[key]
                    # Call close() on the window to ensure controller cleanup is performed
                    window.close()
                except Exception as e:
                    self._logger.error(f"Error closing detail window for {key}: {e}")
        except Exception as e:
            self._logger.error(f"Error in _close_all_detail_windows: {e}")

    # --- Mini Widget Methods ---

    def _on_window_state_changed(self, state):
        """Shows or hides the mini widget when the main window is minimized/restored."""
        if state == Qt.WindowState.WindowMinimized:
            # Check if mini widget is enabled in settings
            mini_widget_enabled = self.app_settings.get_setting("mini_widget_enabled", "true").lower() == "true"
            if mini_widget_enabled:
                # Show the mini widget when window is minimized (as per requirements)
                try:
                    screen = QApplication.primaryScreen()
                    if screen is not None:
                        if not self.mini_widget_view.isVisible():
                            self.mini_widget_controller.show(screen)
                    else:
                        try:
                            self._logger.debug("Primary screen not available; skipping mini widget show")
                        except Exception:
                            pass
                except Exception:
                    try:
                        self._logger.exception('Error while accessing primary screen')
                    except Exception:
                        pass

                # Update display immediately
                self._update_widget_display()
        else:
            self.mini_widget_controller.hide()

    def _on_main_window_closing(self):
        """Handles the main window closing event by hiding the mini widget."""
        # Stop the widget update timer
        if hasattr(self, 'widget_update_timer'):
            self.widget_update_timer.stop()
        
        # Stop the sync timer
        if hasattr(self, 'sync_timer'):
            self.sync_timer.stop()
        
        # Stop network monitoring
        if hasattr(self, 'network_service'):
            self.network_service.stop_monitoring()
        
        # Hide the mini widget
        self.mini_widget_controller.hide()
        
        # Stop notification checks if running
        try:
            if hasattr(self, 'notification_controller'):
                self.notification_controller.stop_notification_checks()
        except Exception:
            pass

        # Close any open detail windows (which will also stop their workers)
        try:
            for key, win in list(self.open_detail_windows.items()):
                try:
                    # Ask the window to close which triggers controller cleanup
                    win.close()
                except Exception:
                    pass
        except Exception:
            pass

        # Debug: dump active threads status to help diagnose "Destroyed while thread is still running"
        try:
            for t in list(self._active_threads):
                try:
                    self._logger.debug("Active thread at shutdown: name=%s running=%s isFinished=%s", 
                                       getattr(t, 'objectName', lambda: None)(), getattr(t, 'isRunning', lambda: False)(), getattr(t, 'isFinished', lambda: False)())
                except Exception:
                    try:
                        self._logger.debug("Active thread at shutdown: %s (could not query state)", str(t))
                    except Exception:
                        pass
        except Exception:
            pass

        # Gracefully stop any active threads started by this controller
        try:
            # First, attempt to stop worker objects if they expose a stop/terminate API
            try:
                for w in list(self._active_workers):
                    try:
                        # Prefer cooperative stop if available
                        if hasattr(w, 'stop'):
                            try:
                                w.stop()
                            except Exception:
                                pass
                        if hasattr(w, 'requestInterruption'):
                            try:
                                w.requestInterruption()
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            # Then attempt to stop threads safely
            for thread in list(self._active_threads):
                try:
                    # Ask the thread to quit (for event loops)
                    try:
                        thread.quit()
                    except Exception:
                        pass

                    # Wait briefly for cooperative shutdown
                    try:
                        if not thread.wait(3000):
                            # If still running, attempt cooperative interruption
                            try:
                                thread.requestInterruption()
                            except Exception:
                                pass
                            # Wait a bit longer
                            thread.wait(2000)
                    except Exception:
                        pass

                    # If the thread is still running after cooperative attempts, force terminate
                    try:
                        if thread.isRunning():
                            try:
                                thread.terminate()
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def _restore_main_window(self):
        """Restores the main window from the widget."""
        self.mini_widget_controller.hide()
        self.view.setWindowState(Qt.WindowState.WindowNoState)
        self.view.activateWindow()
        # After restoring main, ensure any dialog windows do not keep an always-on-top
        # hint that would prevent the main window from appearing above them.
        try:
            self._on_main_activated()
        except Exception:
            pass

    def _start_timer_from_widget(self, jira_key: str):
        """Starts a timer for a favorite issue selected from the widget."""
        # If a detail window is already open for this key, just start its timer
        if jira_key in self.open_detail_windows:
            controller = self.open_detail_windows[jira_key].controller
            if not controller.is_running:
                controller.start_timer()
        else:
            # Limit the number of open detail windows to prevent too many open at once
            MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
            if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
                # Close the oldest detail window
                oldest_key = next(iter(self.open_detail_windows))
                self._close_detail_window(oldest_key)
            
            # If not open, create it and show it so the user can see the timer
            from views.jira_detail_view import JiraDetailView
            from controllers.jira_detail_controller import JiraDetailController

            # Parent to main window so it can be raised above the container
            detail_window = JiraDetailView(jira_key, parent=self.view)
            try:
                detail_window.setWindowFlag(Qt.WindowType.Window, True)
            except Exception:
                pass
            detail_controller = JiraDetailController(
                detail_window, self.jira_service, self.db_service, jira_key
            )
            detail_window.controller = detail_controller
            self.open_detail_windows[jira_key] = detail_window
            # Usiamo solo il segnale window_closed e non destroyed per evitare doppie chiamate
            # detail_window.destroyed.connect(lambda: self._on_detail_window_closed(jira_key))
            detail_controller.window_closed.connect(self._on_detail_window_closed)
            detail_controller.timer_started.connect(self._on_timer_started)
            detail_controller.timer_stopped.connect(self._on_timer_stopped)
            detail_controller.time_updated.connect(self._on_time_updated)
            
            # Load data and show the window; ensure always-on-top is applied
            detail_controller._load_data()
            try:
                from services.ui_utils import apply_always_on_top
                apply_always_on_top(detail_window, app_settings=self.app_settings)
            except Exception:
                pass
            detail_window.show()
            
            # Start the timer
            detail_controller.start_timer()
            
    def _start_timer_from_notes(self, jira_key: str):
        """Starts a timer for a Jira issue selected from the notes manager using the mini timer dialog.
        
        This method will start a timer for any Jira key, even if it doesn't exist on the server.
        This is useful for tracking time against fictional or future Jira tickets that are mentioned
        in notes but don't yet exist in Jira.
        """
        # Prima verifichiamo se c'è già un timer attivo per questa issue
        if jira_key == self._active_timer_key and jira_key in self.open_detail_windows:
            # Mostra e attiva la finestra già esistente
            self.open_detail_windows[jira_key].show()
            self.open_detail_windows[jira_key].activateWindow()
            return
            
        # Limit the number of open detail windows to prevent too many open at once
        MAX_DETAIL_WINDOWS = 3  # Allow up to 3 detail windows open simultaneously
        if len(self.open_detail_windows) >= MAX_DETAIL_WINDOWS:
            # Close the oldest detail window
            oldest_key = next(iter(self.open_detail_windows))
            self._close_detail_window(oldest_key)
            
        # Utilizziamo il nuovo MiniTimerController con la stessa interfaccia del mini widget
        try:
            from controllers.mini_timer_controller import MiniTimerController
            from jira import JIRAError
            
            # Prima di avviare il timer, verifichiamo se il ticket esiste sul server
            # ma solo se siamo connessi. Se non esiste, lo consideriamo un ticket fittizio.
            is_fictional = False
            try:
                if self.jira_service.is_connected():
                    try:
                        # Tentiamo di recuperare i dettagli del ticket (genera JIRAError se non esiste)
                        self.jira_service.get_issue(jira_key)
                    except JIRAError as e:
                        # Se otteniamo un 404 o altro errore client (4xx), 
                        # il ticket non esiste sul server, ma lo gestiamo come fittizio
                        if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                            self._logger.warning(f"Timer avviato per ticket fittizio: {jira_key} (status: {e.status_code})")
                            is_fictional = True
                        else:
                            # Errore server (5xx) o altro errore significativo
                            raise e
            except Exception as e:
                # Log the error but continue - we'll just create a timer anyway
                self._logger.warning(f"Impossibile verificare l'esistenza del ticket {jira_key}: {e}. Procedo comunque.")
                
            # Creiamo un controller per il mini timer
            mini_timer_controller = MiniTimerController(jira_key, self.db_service)
            
            # Se il ticket è fittizio, aggiungiamo un avviso nella nota del timer
            if is_fictional:
                # Aggiungiamo un avviso che questo è un ticket fittizio
                mini_timer_controller.view.set_note_hint("Ticket fittizio - non esiste su Jira")
                mini_timer_controller.view.setWindowTitle(f"Timer: {jira_key} (Fittizio)")
            
            # Connessione dei segnali
            mini_timer_controller.timer_started.connect(self._on_timer_started)
            mini_timer_controller.timer_stopped.connect(self._on_timer_stopped_with_note)
            
            # Applichiamo le impostazioni di visualizzazione
            try:
                from services.ui_utils import apply_always_on_top
                apply_always_on_top(mini_timer_controller.view, app_settings=self.app_settings)
            except Exception as e:
                self._logger.error(f"Error applying window flags: {e}")
            
            # Iniziamo il timer e mostriamo la finestra
            mini_timer_controller.run()
            
            # Aggiungiamo alle finestre aperte
            self.open_detail_windows[jira_key] = mini_timer_controller.view
            self.open_detail_windows[jira_key].controller = mini_timer_controller
            
            # Utilizziamo una funzione parziale per il collegamento del segnale destroyed
            # per evitare problemi di riferimento alla variabile jira_key
            from functools import partial
            destroy_handler = partial(self._on_detail_window_closed, jira_key)
            mini_timer_controller.view.destroyed.connect(destroy_handler)
            
            self._logger.debug(f"Mini timer started for {jira_key} from notes (fittizio: {is_fictional})")
            
        except Exception as e:
            self._logger.error(f"Error starting mini timer from notes: {e}")
            import traceback
            self._logger.error(traceback.format_exc())

    def _play_active_timer(self):
        """Starts the timer for the active issue from the mini widget."""
        if self._active_timer_key and self._active_timer_key in self.open_detail_windows:
            controller = self.open_detail_windows[self._active_timer_key].controller
            if not controller.is_running:
                controller.start_timer()

    def _pause_active_timer(self):
        """Pauses the timer for the active issue from the mini widget."""
        if self._active_timer_key and self._active_timer_key in self.open_detail_windows:
            controller = self.open_detail_windows[self._active_timer_key].controller
            if controller.is_running:
                controller.pause_timer()

    def _stop_active_timer(self):
        """Stops the timer for the active issue from the mini widget."""
        if self._active_timer_key and self._active_timer_key in self.open_detail_windows:
            controller = self.open_detail_windows[self._active_timer_key].controller
            controller._stop_timer() # This handles saving the time as well

    def _update_widget_display(self):
        """Updates the mini widget with the current timer info."""
        if not hasattr(self, 'mini_widget_controller'):
            return
        
        if self._active_timer_key:
            hours = self._active_timer_seconds // 3600
            minutes = (self._active_timer_seconds % 3600) // 60
            seconds = self._active_timer_seconds % 60
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.mini_widget_controller.update_display(self._active_timer_key, time_str)
        else:
            self.mini_widget_controller.update_display(None, "00:00:00")

    def eventFilter(self, watched, event):
        """Intercept window activation events on the main view so we can lower dialogs
        that were temporarily given WindowStaysOnTopHint. This helps when the user
        explicitly activates the main window (clicking its taskbar entry, etc.)."""
        try:
            from PyQt6.QtWidgets import QTableWidget
            from PyQt6.QtCore import QEvent
            from PyQt6.QtGui import QMouseEvent

            # Log any rilevanti eventi che potrebbero causare la chiusura delle finestre
            if event.type() == QEvent.Type.WindowActivate:
                self._logger.debug(f"[DEBUG] WindowActivate event ricevuto da {watched}")
                # Assicuriamoci che le finestre di dettaglio siano visibili in caso di attivazione di qualsiasi finestra
                self._ensure_detail_windows_visible()
            elif event.type() == QEvent.Type.FocusIn:
                self._logger.debug(f"[DEBUG] FocusIn event ricevuto da {watched}")
            elif event.type() == QEvent.Type.MouseButtonPress:
                self._logger.debug(f"[DEBUG] MouseButtonPress event ricevuto da {watched}")
                # Log specifico per i click sulla tabella
                if isinstance(watched, QTableWidget) or (hasattr(watched, 'table') and watched is self.view.jira_grid_view.table):
                    mouse_event = QMouseEvent(event)
                    pos = mouse_event.pos()
                    self._logger.debug(f"[DEBUG] Click sulla tabella rilevato a posizione ({pos.x()}, {pos.y()})")
                    self._logger.debug(f"[DEBUG] Finestre di dettaglio aperte: {list(self.open_detail_windows.keys())}")
                    
                    # Tracciamento dello stato delle finestre di dettaglio
                    for key, window in self.open_detail_windows.items():
                        self._logger.debug(f"[DEBUG] Stato finestra {key}: IsVisible={window.isVisible()}, IsHidden={window.isHidden()}, IsModal={window.isModal()}, IsActive={window.isActiveWindow()}")

                    # Assicuriamoci che le finestre di dettaglio rimangano visibili anche dopo il click sulla tabella
                    self._ensure_detail_windows_visible()
                    
                    # Tracciamento stack
                    import traceback
                    self._logger.debug(f"[DEBUG] Stack trace al click:\n{traceback.format_stack()}")
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if isinstance(watched, QTableWidget) or (hasattr(watched, 'table') and watched is self.view.jira_grid_view.table):
                    self._logger.debug(f"[DEBUG] MouseButtonRelease sulla tabella")
            elif event.type() == QEvent.Type.MouseButtonDblClick:
                if isinstance(watched, QTableWidget) or (hasattr(watched, 'table') and watched is self.view.jira_grid_view.table):
                    self._logger.debug(f"[DEBUG] MouseButtonDblClick sulla tabella")
            
            if watched is self.view and event.type() == QEvent.Type.WindowActivate:
                try:
                    self._on_main_activated()
                except Exception:
                    pass
        except Exception as e:
            self._logger.exception(f"[DEBUG] Errore durante l'eventFilter: {e}")
        # Continue normal event processing
        return super().eventFilter(watched, event)

    def _on_main_activated(self):
        """Bring main to front and ensure dialogs remain open when main is activated.
        
        When the main window is activated (clicked), we ensure it comes to the front
        without closing any other dialogs. We also make sure dialogs don't have 
        WindowStaysOnTopHint which would prevent main from appearing above them.

        Contract:
        - Inputs: none (uses self.view and tracked dialog lists)
        - Outputs: main window raised/activated; dialogs remain open and visible
        - Error modes: best-effort (exceptions are caught and logged)
        """
        self._logger.debug(f"[DEBUG] _on_main_activated chiamato. Finestre di dettaglio aperte: {list(self.open_detail_windows.keys())}")
        try:
            # First ensure all dialog windows remain visible and non-modal
            # This is critical to prevent them from being closed when main is activated
            try:
                from PyQt6.QtCore import Qt
                open_windows = self._get_open_dialog_windows()
                self._logger.debug(f"[DEBUG] Numero di finestre di dialogo aperte: {len(open_windows)}")
                # Tracciamento dettagli finestre di dettaglio
                for key, window in self.open_detail_windows.items():
                    self._logger.debug(f"[DEBUG] _on_main_activated - Stato finestra {key}: IsVisible={window.isVisible()}, IsHidden={window.isHidden()}, IsModal={window.isModal()}, IsActive={window.isActiveWindow()}")
                
                for win in open_windows:
                    try:
                        # Make dialog non-modal if it isn't already
                        try:
                            prev_modal = win.isModal()
                            win.setModal(False)
                            self._logger.debug(f"[DEBUG] Cambiato modal da {prev_modal} a False per {win}")
                        except Exception as e:
                            self._logger.debug(f"[DEBUG] Errore nel cambiare modal state: {e}")
                            pass
                            
                        # Remove WindowStaysOnTopHint but don't recreate the window
                        # This allows main to appear above when needed
                        try:
                            win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
                        except Exception:
                            try:
                                # Fallback to bitwise operation only if setWindowFlag isn't available
                                # BUT IMPORTANTLY: we split the operation to ensure visibility is preserved
                                flags = win.windowFlags()
                                if bool(flags & Qt.WindowType.WindowStaysOnTopHint):
                                    # Only if the flag is actually set, change it
                                    flags = flags & ~Qt.WindowType.WindowStaysOnTopHint
                                    # Remember the visibility state
                                    was_visible = win.isVisible()
                                    self._logger.debug(f"[DEBUG] Modificando window flag: Finestra {win} visibile: {was_visible}")
                                    win.setWindowFlags(flags)
                                    # Restore visibility if it was changed
                                    if was_visible and not win.isVisible():
                                        self._logger.debug(f"[DEBUG] La finestra {win} è stata nascosta dopo setWindowFlags, la rendo visibile")
                                        win.show()
                                    
                                    # Doppio controllo sulla visibilità dopo le modifiche
                                    self._logger.debug(f"[DEBUG] Stato finestra dopo setWindowFlags: IsVisible={win.isVisible()}")
                            except Exception as e:
                                self._logger.debug(f"[DEBUG] Errore nella modifica delle flag di finestra: {e}")
                                pass
                    except Exception as e:
                        self._logger.debug(f"[DEBUG] Errore nella gestione della finestra di dialogo: {e}")
                        pass
            except Exception as e:
                self._logger.exception(f'[DEBUG] Error preparing dialog windows: {e}')
                pass

            # Now raise the main window
            from services.ui_utils import apply_always_on_top
            try:
                apply_always_on_top(self.view, self.app_settings, raise_window=True)
            except Exception:
                pass

            # Salviamo lo stato di visibilità di tutte le finestre di dettaglio
            self._logger.debug(f"[DEBUG] Prima di processEvents - Finestre di dettaglio aperte: {list(self.open_detail_windows.keys())}")
            for key, window in self.open_detail_windows.items():
                # Forza la visibilità prima del processEvents per evitare che diventino invisibili
                if window.isHidden():
                    self._logger.debug(f"[DEBUG] Forzando la visibilità della finestra {key} prima di processEvents")
                    window.show()
                self._logger.debug(f"[DEBUG] Prima di processEvents - Stato finestra {key}: IsVisible={window.isVisible()}, IsHidden={window.isHidden()}")

            # Allow the window system to process these changes immediately
            try:
                from PyQt6.QtWidgets import QApplication
                self._logger.debug(f"[DEBUG] Chiamando QApplication.processEvents()")
                QApplication.processEvents()
            except Exception as e:
                self._logger.debug(f"[DEBUG] Errore in processEvents: {e}")
                pass
                
            # Verifica stato finestre di dettaglio dopo processEvents e ripristina la visibilità
            self._logger.debug(f"[DEBUG] Dopo processEvents - Finestre di dettaglio aperte: {list(self.open_detail_windows.keys())}")
            for key, window in self.open_detail_windows.items():
                self._logger.debug(f"[DEBUG] Dopo processEvents - Stato finestra {key}: IsVisible={window.isVisible()}, IsHidden={window.isHidden()}")
                
                # Ripristina SEMPRE la visibilità di tutte le finestre di dettaglio dopo processEvents
                if window.isHidden():
                    self._logger.debug(f"[DEBUG] Ripristino visibilità per la finestra {key}")
                    window.show()
                    window.raise_()
                    # Non attiviamo per non rubare il focus dalla finestra principale
                    # window.activateWindow()
                
            # Log successful operation at debug level
            try:
                self._logger.debug(f"[DEBUG] Main window activated and raised; {len(self._get_open_dialog_windows())} dialog(s) remain open")
            except Exception as e:
                self._logger.debug(f"[DEBUG] Errore nel logging finale: {e}")
                pass
        except Exception:
            logger.exception('Error while bringing main to front')
            
    def _update_sync_status(self):
        """Updates the sync status indicator with current counts."""
        # Get counts of pending and failed operations (be defensive if db_service is a test dummy)
        try:
            pending_ops = self.db_service.get_pending_sync_operations()
        except Exception:
            try:
                # maybe it's a property returning an int
                pending_ops = getattr(self.db_service, 'pending_ops', [])
            except Exception:
                pending_ops = []

        try:
            failed_ops = self.db_service.get_failed_sync_operations()
        except Exception:
            try:
                failed_ops = getattr(self.db_service, 'failed_ops', [])
            except Exception:
                failed_ops = []

        # Update the indicator (ensure lengths are ints)
        try:
            p_len = len(pending_ops) if hasattr(pending_ops, '__len__') else int(pending_ops or 0)
        except Exception:
            p_len = 0
        try:
            f_len = len(failed_ops) if hasattr(failed_ops, '__len__') else int(failed_ops or 0)
        except Exception:
            f_len = 0

        try:
            self.view.update_sync_status(p_len, f_len)
        except Exception:
            pass
        
    def _show_sync_queue_dialog(self):
        """Shows the sync queue management dialog."""
        try:
            sync_queue_controller = SyncQueueController(self.db_service, self.jira_service, parent=None)
            
            # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
            try:
                sync_queue_controller.view.setWindowFlag(Qt.WindowType.Window, True)
                sync_queue_controller.view.setModal(False)
            except Exception:
                pass
                
            sync_queue_controller.sync_operation_changed.connect(self._update_sync_status)
            
            # Track the dialog window
            self._open_dialog_windows.append(sync_queue_controller.view)
            from functools import partial
            sync_queue_controller.view.destroyed.connect(partial(self._on_dialog_window_closed, sync_queue_controller.view))
            
            # Show the view now
            sync_queue_controller.view.show()
            sync_queue_controller.view.raise_()
            sync_queue_controller.view.activateWindow()
            
            # Finish controller setup (might do other initialization)
            sync_queue_controller.run()
            
        except Exception as e:
            self._logger.error(f"Error opening sync queue dialog: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            
    def _show_notifications_dialog(self):
        """Shows the notifications dialog."""
        try:
            from views.notifications_dialog import NotificationsDialog
            
            notifications_dialog = NotificationsDialog(
                self.notification_controller,
                self.jira_service,
                parent=None  # No parent for top-level
            )
            
            # Ensure dialog is top-level, non-modal, and will not be closed when main is activated
            try:
                notifications_dialog.setWindowFlag(Qt.WindowType.Window, True)
                notifications_dialog.setModal(False)
            except Exception:
                pass
            
            # Track the dialog window
            self._open_dialog_windows.append(notifications_dialog)
            from functools import partial
            notifications_dialog.destroyed.connect(partial(self._on_dialog_window_closed, notifications_dialog))
            
            # Load notification colors from settings
            if hasattr(self, 'app_settings'):
                notifications_dialog.load_notification_colors(self.app_settings)
            
            # Connect signal to open issue detail
            notifications_dialog.open_issue_detail.connect(self._open_issue_from_history)
            
            # Mark notifications as read when dialog is closed
            notifications_dialog.accepted.connect(self.notification_controller.mark_all_as_read)
            
            # Show the dialog now
            notifications_dialog.show()
            notifications_dialog.raise_()
            notifications_dialog.activateWindow()
            
        except Exception as e:
            self._logger.error(f"Error opening notifications dialog: {e}")
            import traceback
            self._logger.error(traceback.format_exc())

    def _open_issue_from_history(self, jira_key: str):
        """Opens a detail view for an issue selected from history."""
        # Simply delegate to our main method that handles this correctly
        self._open_detail_from_key(jira_key)
        
    # --- Network status handling methods ---
    
    def _on_internet_connection_changed(self, is_connected: bool):
        """Handles changes in internet connection state."""
        self.is_internet_available = is_connected
        self._logger.info(f"Stato connessione internet cambiato: {'disponibile' if is_connected else 'non disponibile'}")
        
        # Update the UI indicator
        self.view.update_network_status(self.is_internet_available, self.is_jira_available)
        
        if is_connected:
            # If we have regained internet, check if we can connect to JIRA as well
            if not self.is_jira_available:
                self._try_reconnect_jira()
        else:
            # If internet is gone, JIRA is gone too
            self.is_jira_available = False
            self.view.update_network_status(False, False)
            
            # Show a brief message to inform the user
            self._show_offline_notification("Connessione internet persa", 
                "L'applicazione continuerà a funzionare in modalità offline.\n"
                "I dati saranno salvati localmente e sincronizzati quando la connessione sarà ripristinata.")
            
    def _on_jira_connection_changed(self, is_connected: bool):
        """Handles changes in JIRA connection state."""
        old_state = self.is_jira_available
        self.is_jira_available = is_connected
        self._logger.info(f"Stato connessione JIRA cambiato: {'disponibile' if is_connected else 'non disponibile'}")
        
        # Update the UI indicator
        self.view.update_network_status(self.is_internet_available, self.is_jira_available)
        
        # If JIRA just came back online
        if is_connected and not old_state:
            # Show a message
            self._show_offline_notification("Connessione a JIRA ripristinata", 
                "L'applicazione è ora in modalità online.\n"
                "Le modifiche locali possono essere sincronizzate con il server.")
            
            # Try to sync pending operations if auto-sync is enabled
            auto_sync = self.app_settings.get_setting("auto_sync", "false").lower() == "true"
            if auto_sync:
                # Trigger sync (this would normally happen periodically, but we trigger it immediately)
                self._process_sync_queue()
        
        # If JIRA just went offline
        elif not is_connected and old_state:
            # Show a message
            self._show_offline_notification("Connessione a JIRA persa", 
                "L'applicazione continuerà a funzionare in modalità parzialmente offline.\n"
                "I dati saranno salvati localmente e sincronizzati quando la connessione a JIRA sarà ripristinata.")
    
    def _try_reconnect_jira(self):
        """Attempts to reconnect to JIRA."""
        try:
            # Recupera le credenziali
            jira_url = self.app_settings.get_setting("JIRA_URL", "")
            
            # Recupera il PAT
            from services.credential_service import CredentialService
            cred_service = CredentialService()
            pat = cred_service.get_pat(jira_url)
            
            if jira_url and pat:
                # Tenta la riconnessione
                self._logger.info(f"Tentativo di riconnessione a JIRA: {jira_url}")
                self.jira_service.connect(jira_url, pat)
                self.is_jira_available = True
                self._logger.info("Riconnessione a JIRA riuscita")
                
                # Aggiorna l'indicatore
                self.view.update_network_status(self.is_internet_available, self.is_jira_available)
                
                # Informo l'utente
                self._show_offline_notification("Connessione a JIRA ripristinata", 
                    "L'applicazione è tornata in modalità online.\n"
                    "Le modifiche locali possono essere sincronizzate con il server.")
                
                return True
        except Exception as e:
            self._logger.warning(f"Tentativo di riconnessione a JIRA fallito: {e}")
        
        return False
    
    def _check_connection_manually(self):
        """Triggered when the user requests a manual connection check."""
        # Mostra un messaggio di attesa
        self._logger.info("Verifica manuale della connessione richiesta")
        
        try:
            from PyQt6.QtWidgets import QMessageBox
            wait_msg = QMessageBox(self.view)
            wait_msg.setWindowTitle("Verifica connessione")
            wait_msg.setText("Verifica della connessione in corso...")
            wait_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            wait_msg.show()
            
            # Esegue controllo della connessione
            self.network_service.check_connection()
            
            # Chiudi il messaggio di attesa
            wait_msg.close()
            
            # Mostra il risultato
            result_msg = QMessageBox(self.view)
            result_msg.setWindowTitle("Stato connessione")
            
            if self.is_internet_available and self.is_jira_available:
                result_msg.setText("✅ Connessione a internet e JIRA disponibile")
                result_msg.setIcon(QMessageBox.Icon.Information)
            elif self.is_internet_available:
                result_msg.setText("⚠️ Connessione a internet disponibile, ma JIRA non raggiungibile")
                result_msg.setIcon(QMessageBox.Icon.Warning)
                result_msg.setInformativeText("Possibili cause:\n- Server JIRA non disponibile\n- Problemi con le credenziali\n- Problemi di rete interni")
            else:
                result_msg.setText("❌ Nessuna connessione a internet")
                result_msg.setIcon(QMessageBox.Icon.Critical)
                result_msg.setInformativeText("Controlla la connessione di rete")
            
            result_msg.exec()
            
        except Exception as e:
            self._logger.error(f"Errore durante la verifica manuale della connessione: {e}")
            try:
                wait_msg.close()
            except Exception:
                pass
    
    def _show_offline_notification(self, title, message):
        """Shows a non-modal notification about network status changes."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self.view)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Make it non-modal so it doesn't block the application
            msg.setWindowModality(Qt.WindowModality.NonModal)
            msg.show()
        except Exception as e:
            self._logger.error(f"Errore nel mostrare la notifica offline: {e}")
    
    def _process_sync_queue(self):
        """Processes the sync queue when connection is restored."""
        # TODO: This would normally be done by a sync worker
        # For this implementation, we'll trigger it when connection is restored
        # and if auto-sync is enabled
        pass
