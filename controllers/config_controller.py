from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from services.jira_service import JiraService
from services.app_settings import AppSettings
from services.credential_service import CredentialService
from controllers.status_color_controller import StatusColorController
from controllers.jql_history_controller import JqlHistoryController
from PyQt6.QtCore import pyqtSignal

class ConfigController:
    # Emitted after settings are saved successfully
    settings_saved = pyqtSignal()
    def __init__(self, view, jira_service: JiraService, app_settings: AppSettings, cred_service: CredentialService):
        self.view = view
        self.jira_service = jira_service
        self.app_settings = app_settings
        self.cred_service = cred_service
        self.db_service = None  # This will be set by the caller
        self._connect_signals()

    def set_db_service(self, db_service):
        """Sets the database service for this controller."""
        self.db_service = db_service

    def _connect_signals(self):
        # We disconnect the default 'accept' and connect our own validation logic
        self.view.button_box.accepted.disconnect()
        self.view.button_box.accepted.connect(self._on_save)
        
        # Connect status color configuration button
        self.view.status_color_btn.clicked.connect(self._open_status_color_dialog)
        
        # Connect JQL history button
        self.view.jql_history_btn.clicked.connect(self._open_jql_history_dialog)
        
        # Connect sync queue button
        self.view.sync_queue_btn.clicked.connect(self._open_sync_queue_dialog)

    def run(self):
        # Pre-fill the URL if it already exists
        jira_url = self.app_settings.get_setting("JIRA_URL")
        if jira_url:
            self.view.jira_url_input.setText(jira_url)
            
            # Pre-fill PAT if it exists for this URL
            pat = self.cred_service.get_pat(jira_url)
            if pat:
                self.view.pat_input.setText(pat)
        
        # Pre-fill JQL if it exists
        jql = self.app_settings.get_setting("jql_query")
        if jql:
            self.view.jql_input.setPlainText(jql)
            
        # Set auto-sync state
        auto_sync = self.app_settings.get_setting("auto_sync", "false").lower() == "true"
        self.view.set_auto_sync(auto_sync)
        # Set always-on-top state
        always_on_top = self.app_settings.get_setting("always_on_top", "false").lower() == "true"
        try:
            self.view.set_always_on_top(always_on_top)
        except Exception:
            pass
        
        # Set mini widget enabled state
        mini_widget_enabled = self.app_settings.get_setting("mini_widget_enabled", "true").lower() == "true"
        try:
            self.view.set_mini_widget_enabled(mini_widget_enabled)
        except Exception:
            pass
            
        # Set timezone
        timezone = self.app_settings.get_setting("timezone", "local")
        try:
            # Set the timezone combo to the saved value
            for i in range(self.view.timezone_combo.count()):
                if self.view.timezone_combo.itemData(i) == timezone:
                    self.view.timezone_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass
        
        # Set logging checkboxes based on saved settings
        self.view.log_info_checkbox.setChecked(self.app_settings.get_setting("log_info", "true").lower() == "true")
        self.view.log_debug_checkbox.setChecked(self.app_settings.get_setting("log_debug", "false").lower() == "true")
        self.view.log_warning_checkbox.setChecked(self.app_settings.get_setting("log_warning", "true").lower() == "true")
        
        # Load notification colors
        self.view.load_notification_colors(self.app_settings)
        
        return self.view.exec()

    def _on_save(self):
        self.view.clear_error()
        config = self.view.get_values()
        url = config["url"]
        pat = config["pat"]
        jql = config["jql"]
        auto_sync = config["auto_sync"]
        log_info = config["log_info"]
        log_debug = config["log_debug"]
        log_warning = config["log_warning"]
        notification_unread_color = config.get("notification_unread_color", "#FF6B6B")
        notification_read_color = config.get("notification_read_color", "#FFD93D")
        always_on_top = config.get("always_on_top", False)
        mini_widget_enabled = config.get("mini_widget_enabled", True)

        save_button = self.view.button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setEnabled(False)

        try:
            # Controlla se sono stati modificati URL o PAT
            current_url = self.app_settings.get_setting("JIRA_URL")
            current_pat = self.cred_service.get_pat(current_url) if current_url else None

            url_changed = url != current_url
            pat_changed = pat != current_pat

            # Testa la connessione solo se URL o PAT sono stati modificati
            if url_changed or pat_changed:
                if not url or not pat:
                    self.view.show_error("Jira URL e PAT non possono essere vuoti.")
                    return

                # Test connection solo se necessario
                self.jira_service.connect(url, pat)

                # Save URL and PAT
                self.app_settings.set_setting("JIRA_URL", url)
                self.cred_service.set_pat(url, pat)

            # Save JQL query if provided
            if jql:
                self.app_settings.set_setting("jql_query", jql)

                # Also add to JQL history if database service is available
                if self.db_service:
                    self.db_service.add_jql_history(jql)

            # Save auto-sync setting
            self.app_settings.set_setting("auto_sync", str(auto_sync).lower())

            # Save log level settings
            self.app_settings.set_setting("log_info", str(log_info).lower())
            self.app_settings.set_setting("log_debug", str(log_debug).lower())
            self.app_settings.set_setting("log_warning", str(log_warning).lower())
            
            # Imposta anche il livello di log esplicito in base alle caselle selezionate
            if log_debug:
                self.app_settings.set_setting("log_level", "DEBUG")
            elif log_info:
                self.app_settings.set_setting("log_level", "INFO")
            elif log_warning:
                self.app_settings.set_setting("log_level", "WARNING")
            else:
                self.app_settings.set_setting("log_level", "ERROR")
            # Save always-on-top setting
            self.app_settings.set_setting("always_on_top", str(bool(always_on_top)).lower())
            
            # Save mini widget enabled setting
            self.app_settings.set_setting("mini_widget_enabled", str(bool(mini_widget_enabled)).lower())
            
            # Save notification colors
            self.app_settings.set_setting("notification_unread_color", notification_unread_color)
            self.app_settings.set_setting("notification_read_color", notification_read_color)
            
            # Save timezone setting
            timezone = config.get("timezone", "local")
            self.app_settings.set_setting("timezone", timezone)

            # Notifica all'utente che le impostazioni di logging saranno applicate al prossimo avvio
            import logging
            logging.info("Impostazioni salvate con successo")

            self.view.show_info("Successo", "Impostazioni salvate con successo.")
            self.view.accept()
            # Emit signal to notify other controllers (e.g., MainController) that settings changed
            try:
                self.settings_saved.emit()
            except Exception:
                pass

        except Exception as e:
            self.view.show_error(f"Errore durante il salvataggio: {str(e)}")
        finally:
            save_button.setEnabled(True)
            
    def _open_status_color_dialog(self):
        """Opens the status color configuration dialog."""
        if not self.db_service:
            self.view.show_error("Servizio database non disponibile.")
            return
        # Parent dialogs to the main window to ensure correct stacking
        parent = self.view if hasattr(self, 'view') else None
        color_controller = StatusColorController(self.db_service, parent=parent)
        color_controller.run()
        # No need to handle the result as changes are saved directly to the database
        
    def _open_jql_history_dialog(self):
        """Opens the JQL history and favorites dialog."""
        if not self.db_service:
            self.view.show_error("Servizio database non disponibile.")
            return
        jql_history_controller = JqlHistoryController(self.db_service)
        # Connect the jql_selected signal to update the JQL input
        jql_history_controller.view.jql_selected.connect(self._on_jql_selected)
        jql_history_controller.run()
        
    def _on_jql_selected(self, query):
        """Handle when a JQL query is selected from history/favorites."""
        self.view.jql_input.setPlainText(query)
        
    def _open_sync_queue_dialog(self):
        """Opens the sync queue management dialog."""
        if not self.db_service:
            self.view.show_error("Servizio database non disponibile.")
            return
        from controllers.sync_queue_controller import SyncQueueController
        parent = self.view if hasattr(self, 'view') else None
        sync_queue_controller = SyncQueueController(self.db_service, self.jira_service, parent=parent)
        sync_queue_controller.run()
