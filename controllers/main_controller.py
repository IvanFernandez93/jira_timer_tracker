from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QTimer
from PyQt6.QtWidgets import QTableWidgetItem, QPushButton, QApplication
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


class MainController(QObject):
    # Using a signal to decouple the controller from knowing about worker threads
    data_loaded = pyqtSignal(list)
    load_failed = pyqtSignal(str)

    def __init__(self, view, db_service, jira_service, app_settings):
        super().__init__()
        self._logger = logging.getLogger('JiraTimeTracker')
        self.view = view
        self.db_service = db_service
        self.jira_service = jira_service
        self.app_settings = app_settings
        self.open_detail_windows = {}  # Track open detail windows by issue key
        # Track active threads started by this controller so we can shut them down
        self._active_threads: list[QThread] = []
        # Track active worker objects so they are not garbage-collected
        self._active_workers: list[object] = []
        
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
        self._connect_signals()
        
        # Configure grid view with app settings for persistence
        self.view.jira_grid_view.set_app_settings(self.app_settings)
        # Apply always-on-top setting from persisted settings
        self._apply_always_on_top()

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

    def _connect_signals(self):
        """Connect signals from the view to controller slots."""
        # Connect navigation signals from FluentWindow interface
        self.view.lastActiveRequested.connect(self._show_last_active_jira)
        self.view.settingsRequested.connect(self._show_settings_dialog)
        self.view.searchJqlRequested.connect(self._show_jql_history_dialog)
        self.view.notesRequested.connect(self._show_notes_grid_dialog)
        self.view.syncQueueRequested.connect(self._show_sync_queue_dialog)
        self.view.notificationsRequested.connect(self._show_notifications_dialog)

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
        self.view.jira_grid_view.apply_jql_btn.clicked.connect(self._apply_custom_jql)
        self.view.jira_grid_view.jql_combo.currentIndexChanged.connect(self._on_jql_combo_changed)
        self.view.jira_grid_view.favorites_btn.clicked.connect(self._on_favorites_toggled)
        
        # Connect notification button in JiraGridView
        self.view.jira_grid_view.notifications_btn.clicked.connect(self._show_notifications_dialog)

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
        
        self.load_jira_issues()
        
        # Initialize history view
        self.history_controller.load_history()

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
        
        # Create items
        key_item = QTableWidgetItem(jira_key)
        title_item = QTableWidgetItem(issue_data.get('fields', {}).get('summary', ''))
        status_item = QTableWidgetItem(status_name)
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
            time_item.setBackground(brush)
        
        # Add items to table
        table.setItem(row_position, 0, key_item)
        table.setItem(row_position, 1, title_item)
        table.setItem(row_position, 2, status_item)
        table.setItem(row_position, 3, time_item)
        
        # Favorite button logic
        from qfluentwidgets import TransparentToolButton
        
        fav_button = TransparentToolButton()
        fav_button.setCheckable(True)
        is_fav = jira_key in self.db_service.get_all_favorites()
        fav_button.setChecked(is_fav)
        fav_button.setText("★" if is_fav else "☆")
        fav_button.clicked.connect(lambda _, key=jira_key, btn=fav_button: self._toggle_favorite(key, btn))
        table.setCellWidget(row_position, 4, fav_button)

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
        
        # Parent the configuration dialog to the main window so stacking is correct
        config_dialog = ConfigDialog(self.view)
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
        config_controller.set_db_service(self.db_service)
        config_controller.run()
        # Re-apply settings after dialog is closed in case the user saved changes
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
        jql_history_controller = JqlHistoryController(self.db_service, from_grid=True)
        jql_history_controller.view.jql_selected.connect(self._on_jql_selected_from_history)
        jql_history_controller.run()
        
    def _show_notes_grid_dialog(self):
        """Shows the notes grid dialog."""
        from views.notes_grid_dialog import NotesGridDialog
        notes_dialog = NotesGridDialog(self.db_service, parent=self.view)
        notes_dialog.exec()
        
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
        self.load_jira_issues(append=False, favorite_keys=favorite_keys if checked else None)

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
                    # Clear frameless if present
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
                # Remove the always-on-top hint but DO NOT call show() to avoid bringing
                # the main window to the foreground. We'll rely on processEvents() to
                # allow the windowing system to apply flag changes.
                main_flags = main_flags & ~Qt.WindowType.WindowStaysOnTopHint
                try:
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
                # clear frameless and translucent hints if present
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

        if issue_key in self.open_detail_windows:
            self.open_detail_windows[issue_key].activateWindow()
            return

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
        detail_window.destroyed.connect(lambda: self._on_detail_window_closed(issue_key))
        detail_controller.window_closed.connect(self._on_detail_window_closed)
        detail_controller.timer_started.connect(self._on_timer_started)
        detail_controller.timer_stopped.connect(self._on_timer_stopped)
        detail_controller.time_updated.connect(self._on_time_updated)

        # Adjust window flags for proper stacking
        self._adjust_window_flags_for_detail(detail_window)

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
        
        if last_active_key in self.open_detail_windows:
            self.open_detail_windows[last_active_key].activateWindow()
            return

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
        detail_window.destroyed.connect(lambda: self._on_detail_window_closed(last_active_key))
        detail_controller.window_closed.connect(self._on_detail_window_closed)
        detail_controller.timer_started.connect(self._on_timer_started)
        detail_controller.timer_stopped.connect(self._on_timer_stopped)
        detail_controller.time_updated.connect(self._on_time_updated)
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(detail_window, app_settings=self.app_settings)
        except Exception:
            pass

        detail_window.show()
        try:
            from services.ui_utils import apply_always_on_top
            apply_always_on_top(detail_window, app_settings=self.app_settings)
        except Exception:
            pass


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

    def _on_time_updated(self, jira_key: str, total_seconds: int):
        """Receives time updates from the active timer."""
        if self._active_timer_key == jira_key:
            self._active_timer_seconds = total_seconds
            self._update_widget_display()

    def _on_detail_window_closed(self, jira_key: str):
        """Removes the detail window from the tracking dictionary when it's closed."""
        if jira_key in self.open_detail_windows:
            del self.open_detail_windows[jira_key]

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

    def _start_timer_from_widget(self, jira_key: str):
        """Starts a timer for a favorite issue selected from the widget."""
        # If a detail window is already open for this key, just start its timer
        if jira_key in self.open_detail_windows:
            controller = self.open_detail_windows[jira_key].controller
            if not controller.is_running:
                controller.start_timer()
        else:
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
            detail_window.destroyed.connect(lambda: self._on_detail_window_closed(jira_key))
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
        sync_queue_controller = SyncQueueController(self.db_service, self.jira_service, parent=self.view)
        sync_queue_controller.sync_operation_changed.connect(self._update_sync_status)
        sync_queue_controller.run()
            
    def _show_notifications_dialog(self):
        """Shows the notifications dialog."""
        from views.notifications_dialog import NotificationsDialog
        
        notifications_dialog = NotificationsDialog(
            self.notification_controller,
            self.jira_service,
            self.view
        )
        
        # Load notification colors from settings
        if hasattr(self, 'app_settings'):
            notifications_dialog.load_notification_colors(self.app_settings)
        
        # Connect signal to open issue detail
        notifications_dialog.open_issue_detail.connect(self._open_issue_from_history)
        
        # Mark notifications as read when dialog is closed
        notifications_dialog.accepted.connect(self.notification_controller.mark_all_as_read)
        
        # Open the dialog
        notifications_dialog.exec()

    def _open_issue_from_history(self, jira_key: str):
        """Opens a detail view for an issue selected from history."""
        # This method is very similar to _open_detail_view but takes just the key
        if jira_key in self.open_detail_windows:
            self.open_detail_windows[jira_key].activateWindow()
            return
            
        from views.jira_detail_view import JiraDetailView
        from controllers.jira_detail_controller import JiraDetailController

        detail_window = JiraDetailView(jira_key)
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
        detail_window.destroyed.connect(lambda: self._on_detail_window_closed(jira_key))
        detail_controller.window_closed.connect(self._on_detail_window_closed)
        detail_controller.timer_started.connect(self._on_timer_started)
        detail_controller.timer_stopped.connect(self._on_timer_stopped)
        detail_controller.time_updated.connect(self._on_time_updated)
        detail_window.show()
