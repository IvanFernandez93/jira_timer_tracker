from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger('JiraTimeTracker')
from PyQt6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QDialog, QDialogButtonBox, QCheckBox, QHBoxLayout, QColorDialog, QPushButton
from qfluentwidgets import (
    LineEdit, PushButton, BodyLabel, StrongBodyLabel, 
    FluentIcon as FIF, InfoBar, InfoBarPosition, TextEdit,
    SwitchButton, ExpandLayout, ComboBox
)

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.resize(600, 500)  # Make the dialog larger
        
        # Initialize notification colors
        self._unread_color = "#FF6B6B"  # Default red
        self._read_color = "#FFD93D"    # Default yellow
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.connection_tab = QWidget()
        self.jql_tab = QWidget()
        self.appearance_tab = QWidget()
        self.sync_tab = QWidget()
        self.logging_tab = QWidget()
        self.data_paths_tab = QWidget()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.connection_tab, "Connessione")
        self.tab_widget.addTab(self.jql_tab, "JQL Predefinita")
        self.tab_widget.addTab(self.appearance_tab, "Aspetto")
        self.tab_widget.addTab(self.sync_tab, "Sincronizzazione")
        self.tab_widget.addTab(self.logging_tab, "Logging")
        self.tab_widget.addTab(self.data_paths_tab, "Percorsi Dati")
        
        # Add tab widget to dialog
        self.main_layout.addWidget(self.tab_widget)
        
        # Setup each tab
        self._setup_connection_tab()
        self._setup_jql_tab()
        self._setup_appearance_tab()
        self._setup_sync_tab()
        self._setup_logging_tab()
        self._setup_data_paths_tab()
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Salva")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        
        # Connect signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Add button box to layout
        self.main_layout.addWidget(self.button_box)
        
    def _setup_connection_tab(self):
        """Setup the connection tab with Jira URL and PAT inputs."""
        layout = QVBoxLayout(self.connection_tab)
        
        self.error_label = BodyLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setVisible(False)
        
        layout.addWidget(self.error_label)
        layout.addWidget(StrongBodyLabel("Jira URL:"))
        
        self.jira_url_input = LineEdit()
        self.jira_url_input.setPlaceholderText("https://your-jira.atlassian.net")
        self.jira_url_input.setToolTip("L'URL dell'istanza Jira, ad esempio https://azienda.atlassian.net")
        layout.addWidget(self.jira_url_input)
        
        layout.addWidget(StrongBodyLabel("Personal Access Token (PAT):"))
        self.pat_input = LineEdit()
        self.pat_input.setEchoMode(LineEdit.EchoMode.Password)
        self.pat_input.setPlaceholderText("Your Personal Access Token")
        self.pat_input.setToolTip("Token di accesso personale per l'autenticazione su Jira")
        layout.addWidget(self.pat_input)
        
        layout.addStretch()
        
    def _setup_jql_tab(self):
        """Setup the JQL tab with default JQL query editor."""
        layout = QVBoxLayout(self.jql_tab)
        
        layout.addWidget(StrongBodyLabel("JQL Predefinita:"))
        layout.addWidget(BodyLabel("Questa query verrà utilizzata per caricare le issue all'avvio dell'applicazione."))
        
        self.jql_input = TextEdit()
        self.jql_input.setPlaceholderText("assignee = currentUser() AND status != \"Done\" ORDER BY updated DESC")
        self.jql_input.setToolTip("Query JQL che verrà usata per caricare i ticket all'avvio dell'applicazione")
        layout.addWidget(self.jql_input)
        
        # Add button for JQL history and favorites
        self.jql_history_btn = PushButton("Cronologia e Preferiti JQL")
        self.jql_history_btn.setIcon(FIF.HISTORY)
        self.jql_history_btn.setToolTip("Gestisci la cronologia e i preferiti delle query JQL")
        layout.addWidget(self.jql_history_btn)
        
        layout.addStretch()
        
    def _setup_appearance_tab(self):
        """Setup the appearance tab with status color configuration."""
        layout = QVBoxLayout(self.appearance_tab)
        
        layout.addWidget(StrongBodyLabel("Colori degli Stati:"))
        layout.addWidget(BodyLabel("Configura i colori per gli stati specifici di Jira."))
        
        self.status_color_btn = PushButton("Configura Colori Stati")
        self.status_color_btn.setIcon(FIF.BRUSH)
        self.status_color_btn.setToolTip("Personalizza i colori degli stati dei ticket Jira")
        layout.addWidget(self.status_color_btn)
        
        layout.addWidget(StrongBodyLabel("Colori delle Priorità:"))
        layout.addWidget(BodyLabel("Configura i colori per le priorità dei ticket Jira."))
        
        self.priority_color_btn = PushButton("Configura Colori Priorità")
        self.priority_color_btn.setIcon(FIF.FLAG)
        self.priority_color_btn.setToolTip("Personalizza i colori delle priorità dei ticket Jira")
        layout.addWidget(self.priority_color_btn)
        # Column config button
        try:
            self.column_config_btn = PushButton("Configura colonne griglia")
            # Some FluentIcon sets may not include GRID; guard against it
            try:
                self.column_config_btn.setIcon(FIF.GRID)
            except Exception:
                pass
            self.column_config_btn.setToolTip("Configura quali colonne mostrare nella griglia e nella cronologia")
            layout.addWidget(self.column_config_btn)
            self.column_config_btn.clicked.connect(self._open_column_config)
        except Exception:
            pass
            
        # Timezone configuration section
        layout.addWidget(StrongBodyLabel("Configurazione del fuso orario:"))
        layout.addWidget(BodyLabel("Imposta il fuso orario per la visualizzazione delle date."))
        
        # Timezone selection combobox
        timezone_layout = QHBoxLayout()
        timezone_layout.addWidget(BodyLabel("Fuso orario:"))
        
        self.timezone_combo = ComboBox()
        
        # Get timezone options - first the current local timezone, then UTC, then common options
        import datetime
        
        # Add system timezone first (default)
        local_tz = datetime.datetime.now().astimezone().tzinfo
        self.timezone_combo.addItem(f"Sistema ({local_tz})", "local")
        
        # Add UTC
        self.timezone_combo.addItem("UTC", "UTC")
        
        # Add common European timezones
        self.timezone_combo.addItem("Europe/Rome", "Europe/Rome")
        self.timezone_combo.addItem("Europe/Madrid", "Europe/Madrid")
        self.timezone_combo.addItem("Europe/Paris", "Europe/Paris")
        self.timezone_combo.addItem("Europe/London", "Europe/London")
        self.timezone_combo.addItem("Europe/Berlin", "Europe/Berlin")
        
        # Add Americas timezones
        self.timezone_combo.addItem("US/Eastern", "US/Eastern")
        self.timezone_combo.addItem("US/Central", "US/Central")
        self.timezone_combo.addItem("US/Mountain", "US/Mountain")
        self.timezone_combo.addItem("US/Pacific", "US/Pacific")
        
        self.timezone_combo.setToolTip("Seleziona il fuso orario per la visualizzazione delle date")
        timezone_layout.addWidget(self.timezone_combo)
        timezone_layout.addStretch()
        layout.addLayout(timezone_layout)
        
        # Current time display with selected timezone
        timezone_sample_layout = QHBoxLayout()
        timezone_sample_layout.addWidget(BodyLabel("Data e ora attuale con il fuso orario selezionato:"))
        self.timezone_sample_label = BodyLabel("")
        self.timezone_sample_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        timezone_sample_layout.addWidget(self.timezone_sample_label)
        layout.addLayout(timezone_sample_layout)
        
        # Update sample when combo changes
        self.timezone_combo.currentIndexChanged.connect(self._update_timezone_sample)
        
        # Initialize sample
        self._update_timezone_sample()
        
        # Notification colors section
        layout.addWidget(StrongBodyLabel("Colori delle Notifiche:"))
        layout.addWidget(BodyLabel("Configura i colori per evidenziare le notifiche lette e non lette."))
        
        # Unread notifications color
        unread_layout = QHBoxLayout()
        unread_layout.addWidget(BodyLabel("Notifiche non lette:"))
        
        self.unread_color_btn = QPushButton()
        self.unread_color_btn.setFixedSize(30, 30)
        self.unread_color_btn.setStyleSheet("background-color: #FF6B6B; border: 1px solid #ccc; border-radius: 3px;")
        self.unread_color_btn.setToolTip("Seleziona il colore per le notifiche non lette")
        self.unread_color_btn.clicked.connect(lambda: self._select_color(self.unread_color_btn, "unread"))
        unread_layout.addWidget(self.unread_color_btn)
        unread_layout.addStretch()
        layout.addLayout(unread_layout)
        
        # Read notifications color
        read_layout = QHBoxLayout()
        read_layout.addWidget(BodyLabel("Notifiche lette:"))
        
        self.read_color_btn = QPushButton()
        self.read_color_btn.setFixedSize(30, 30)
        self.read_color_btn.setStyleSheet("background-color: #FFD93D; border: 1px solid #ccc; border-radius: 3px;")
        self.read_color_btn.setToolTip("Seleziona il colore per le notifiche lette")
        self.read_color_btn.clicked.connect(lambda: self._select_color(self.read_color_btn, "read"))
        read_layout.addWidget(self.read_color_btn)
        read_layout.addStretch()
        layout.addLayout(read_layout)
        
        layout.addStretch()
        
        # Always-on-top option
        always_layout = QHBoxLayout()
        always_layout.addWidget(BodyLabel("Mantieni l'applicazione in primo piano:"))
        self.always_on_top_switch = SwitchButton("Sempre in primo piano")
        self.always_on_top_switch.setToolTip("Se attivato, l'app e le sue finestre saranno sempre sopra le altre applicazioni")
        always_layout.addWidget(self.always_on_top_switch)
        always_layout.addStretch()
        layout.addLayout(always_layout)
        
        # Mini widget option
        mini_widget_layout = QHBoxLayout()
        mini_widget_layout.addWidget(BodyLabel("Mostra mini widget quando minimizzato:"))
        self.mini_widget_switch = SwitchButton("Abilita mini widget")
        self.mini_widget_switch.setToolTip("Se attivato, mostra un piccolo widget di controllo quando la finestra principale è minimizzata")
        mini_widget_layout.addWidget(self.mini_widget_switch)
        mini_widget_layout.addStretch()
        layout.addLayout(mini_widget_layout)
        
    def _setup_sync_tab(self):
        """Setup the synchronization tab with auto-sync settings."""
        layout = QVBoxLayout(self.sync_tab)
        
        # Auto-sync section
        layout.addWidget(StrongBodyLabel("Impostazioni di Sincronizzazione"))
        layout.addWidget(BodyLabel("Configura come l'applicazione sincronizza i dati con Jira."))
        
        # Auto-sync switch
        auto_sync_layout = QVBoxLayout()
        self.auto_sync_switch = SwitchButton("Abilita sincronizzazione automatica dei dati")
        self.auto_sync_switch.setToolTip("Se attivata, i worklog, commenti e altre operazioni verranno sincronizzati automaticamente quando vengono creati")
        auto_sync_layout.addWidget(self.auto_sync_switch)
        
        # Description for auto-sync
        auto_sync_desc = BodyLabel("Quando attiva, l'applicazione tenterà di inviare i dati a Jira non appena vengono accodati. "
                                   "Se disattivata, i dati verranno solo aggiunti alla coda locale e dovranno essere sincronizzati manualmente.")
        auto_sync_desc.setWordWrap(True)
        auto_sync_layout.addWidget(auto_sync_desc)
        
        layout.addLayout(auto_sync_layout)
        
        # Sync queue management section
        layout.addWidget(StrongBodyLabel("Gestione Coda di Sincronizzazione"))
        self.sync_queue_btn = PushButton("Gestisci Coda di Sincronizzazione")
        # Usa l'icona di sistema invece di FluentIcon per compatibilità
        from PyQt6.QtWidgets import QStyle
        self.sync_queue_btn.setIcon(self.sync_queue_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.sync_queue_btn.setToolTip("Visualizza e gestisci la coda delle operazioni in attesa di sincronizzazione")
        layout.addWidget(self.sync_queue_btn)
        
        layout.addStretch()

    def _setup_logging_tab(self):
        """Setup the logging tab with log level configuration."""
        layout = QVBoxLayout(self.logging_tab)
        
        layout.addWidget(StrongBodyLabel("Configurazione Log"))
        layout.addWidget(BodyLabel("Configura quali tipi di messaggi di log visualizzare nel terminale. I log di errore sono sempre visibili."))
        
        # Checkbox per i vari livelli di log
        self.log_info_checkbox = QCheckBox("Info - Informazioni generali sul funzionamento dell'applicazione")
        self.log_debug_checkbox = QCheckBox("Debug - Informazioni dettagliate utili per il debug")
        self.log_warning_checkbox = QCheckBox("Warning - Avvertimenti che non bloccano l'esecuzione")
        
        # Per impostazione predefinita, mostra info e warning ma non debug
        self.log_info_checkbox.setChecked(True)
        self.log_warning_checkbox.setChecked(True)
        
        layout.addWidget(self.log_info_checkbox)
        layout.addWidget(self.log_debug_checkbox)
        layout.addWidget(self.log_warning_checkbox)
        
        # Aggiungi nota che gli errori sono sempre visibili
        error_note = BodyLabel("Nota: i messaggi di errore (ERROR) e critici (CRITICAL) sono sempre visibili nel log.")
        error_note.setStyleSheet("color: #E74C3C; font-style: italic;")
        layout.addWidget(error_note)
        
        layout.addStretch()
    
    def _setup_data_paths_tab(self):
        """Setup the data paths tab to show where persistent data is stored."""
        from PyQt6.QtCore import QStandardPaths
        import os
        
        layout = QVBoxLayout(self.data_paths_tab)
        
        layout.addWidget(StrongBodyLabel("Percorsi dei Dati Persistenti"))
        layout.addWidget(BodyLabel("Questi sono i percorsi dove l'applicazione salva i dati locali."))
        
        # Database path
        layout.addWidget(StrongBodyLabel("Database SQLite:"))
        db_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        db_full_path = os.path.join(db_path, "jira_tracker.db")
        self.db_path_label = BodyLabel(db_full_path)
        self.db_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.db_path_label.setWordWrap(True)
        layout.addWidget(self.db_path_label)
        
        # Logs path
        layout.addWidget(StrongBodyLabel("Cartella dei Log:"))
        logs_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'JiraTimeTracker', 'logs')
        self.logs_path_label = BodyLabel(logs_path)
        self.logs_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.logs_path_label.setWordWrap(True)
        layout.addWidget(self.logs_path_label)
        
        # App data directory
        layout.addWidget(StrongBodyLabel("Cartella Dati Applicazione:"))
        app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.app_data_path_label = BodyLabel(app_data_path)
        self.app_data_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.app_data_path_label.setWordWrap(True)
        layout.addWidget(self.app_data_path_label)
        
        # Add buttons to open folders
        buttons_layout = QHBoxLayout()
        
        self.open_db_folder_btn = PushButton("Apri Cartella Database")
        self.open_db_folder_btn.setIcon(FIF.FOLDER)
        self.open_db_folder_btn.clicked.connect(lambda: self._open_folder(db_path))
        buttons_layout.addWidget(self.open_db_folder_btn)
        
        self.open_logs_folder_btn = PushButton("Apri Cartella Log")
        self.open_logs_folder_btn.setIcon(FIF.FOLDER)
        self.open_logs_folder_btn.clicked.connect(lambda: self._open_folder(logs_path))
        buttons_layout.addWidget(self.open_logs_folder_btn)
        
        layout.addLayout(buttons_layout)

        # Add small indicators to show if the paths actually exist; disable open buttons if missing
        self._db_exists_label = BodyLabel("")
        self._logs_exists_label = BodyLabel("")
        # Place indicators under the respective labels
        indicator_layout = QHBoxLayout()
        indicator_layout.addWidget(self._db_exists_label)
        indicator_layout.addStretch()
        layout.addLayout(indicator_layout)

        indicator_layout2 = QHBoxLayout()
        indicator_layout2.addWidget(self._logs_exists_label)
        indicator_layout2.addStretch()
        layout.addLayout(indicator_layout2)

        # Update initial button states
        try:
            self._update_path_buttons(db_path, logs_path, app_data_path)
        except Exception:
            pass
        
        # Add info about data persistence
        info_text = BodyLabel("Nota: Questi percorsi sono gestiti automaticamente dal sistema operativo. "
                             "I dati vengono conservati tra le sessioni dell'applicazione.")
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_text)
        
        layout.addStretch()
    
    def _select_color(self, button, color_type):
        """Open color dialog to select notification color."""
        from PyQt6.QtGui import QColor
        
        # Get current color from button style
        current_color = button.palette().button().color()
        
        # Open color dialog
        color = QColorDialog.getColor(current_color, self, f"Seleziona colore per notifiche {color_type}")
        
        if color.isValid():
            # Update button color
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc; border-radius: 3px;")
            
            # Store the color for later retrieval
            if color_type == "unread":
                self._unread_color = color.name()
            else:
                self._read_color = color.name()
    
    def _update_timezone_sample(self):
        """Updates the timezone sample label with the current date/time in the selected timezone."""
        try:
            import datetime
            import pytz
            
            # Get the selected timezone
            tz_data = self.timezone_combo.currentData()
            
            # Handle different timezone formats
            if tz_data == "local":
                # Local timezone
                now = datetime.datetime.now().astimezone()
                tz_name = str(now.tzinfo)
            elif tz_data == "UTC":
                # UTC timezone
                now = datetime.datetime.now(pytz.UTC)
                tz_name = "UTC"
            else:
                # Named timezone
                try:
                    tz = pytz.timezone(tz_data)
                    now = datetime.datetime.now(tz)
                    tz_name = tz_data
                except Exception:
                    # Fallback to local
                    now = datetime.datetime.now().astimezone()
                    tz_name = str(now.tzinfo)
            
            # Format date and time nicely
            formatted_time = now.strftime("%d/%m/%Y %H:%M:%S")
            self.timezone_sample_label.setText(f"{formatted_time} ({tz_name})")
        except ImportError:
            # pytz might not be installed, use simple display
            import datetime
            now = datetime.datetime.now()
            self.timezone_sample_label.setText(f"{now.strftime('%d/%m/%Y %H:%M:%S')} (fuso orario locale)")
        except Exception as e:
            self.timezone_sample_label.setText(f"Errore: {str(e)}")
    
    def get_values(self):
        return {
            "url": self.jira_url_input.text().strip(),
            "pat": self.pat_input.text().strip(),
            "jql": self.jql_input.toPlainText().strip(),
            "auto_sync": self.auto_sync_switch.isChecked(),
            "log_info": self.log_info_checkbox.isChecked(),
            "log_debug": self.log_debug_checkbox.isChecked(),
            "log_warning": self.log_warning_checkbox.isChecked(),
            "notification_unread_color": self._unread_color,
            "notification_read_color": self._read_color,
            "always_on_top": self.get_always_on_top(),
            "mini_widget_enabled": self.get_mini_widget_enabled(),
            "timezone": self.timezone_combo.currentData(),
        }

    def _open_column_config(self):
        try:
            from views.column_config_dialog import ColumnConfigDialog
            import json
            # Load existing grid columns from parent app settings if available
            app_settings = None
            try:
                from services.app_settings import AppSettings
                # We don't have DB service here; controller will pass settings via outer logic
            except Exception:
                pass

            # Fallback: open dialog with default columns for editing
            cols = [
                {"id": "key", "label": "Key", "visible": True, "sortable": True},
                {"id": "title", "label": "Title", "visible": True, "sortable": True},
                {"id": "status", "label": "Status", "visible": True, "sortable": True},
                {"id": "time_spent", "label": "Time Spent", "visible": True, "sortable": True},
                {"id": "favorite", "label": "Favorite", "visible": True, "sortable": False},
            ]

            dlg = ColumnConfigDialog(columns=cols, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_cols = dlg.get_columns()
                # Save to AppSettings via controller (controller will call save_notification_colors etc.)
                try:
                    # If the controller passed an app_settings attribute on this dialog, use it
                    if hasattr(self, 'app_settings') and self.app_settings:
                        self.app_settings.set_setting('grid_columns', json.dumps(new_cols))
                        self.app_settings.set_setting('history_grid_columns', json.dumps(new_cols))
                except Exception:
                    pass
        except Exception:
            pass

    def showEvent(self, event):
        """Apply global always-on-top setting when the dialog is shown."""
        try:
            try:
                logger.debug("ConfigDialog.showEvent: flags=%s, opacity=%s, translucent=%s",
                             int(self.windowFlags()),
                             self.windowOpacity(),
                             self.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
            except Exception:
                pass
            # NOTE: do not call apply_always_on_top() here. Calling setWindowFlags/show
            # from within showEvent can trigger showEvent again and cause a recursion
            # loop. always-on-top is applied by controllers (e.g. ConfigController,
            # MainController) when appropriate.
        except Exception:
            logger.exception('Error in ConfigDialog.showEvent logging')

        super().showEvent(event)


    def set_auto_sync(self, enabled: bool):
        """Set the auto sync switch state."""
        try:
            self.auto_sync_switch.setChecked(bool(enabled))
        except Exception:
            # If switch not available, ignore silently
            pass

    def set_always_on_top(self, enabled: bool):
        """Set the local switch state for always-on-top UI element."""
        try:
            self.always_on_top_switch.setChecked(bool(enabled))
        except Exception:
            pass

    def get_always_on_top(self) -> bool:
        try:
            return bool(self.always_on_top_switch.isChecked())
        except Exception:
            return False

    def set_mini_widget_enabled(self, enabled: bool):
        """Set the local switch state for mini widget enabled UI element."""
        try:
            self.mini_widget_switch.setChecked(bool(enabled))
        except Exception:
            pass

    def get_mini_widget_enabled(self) -> bool:
        try:
            return bool(self.mini_widget_switch.isChecked())
        except Exception:
            return True  # Default to enabled

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def clear_error(self):
        self.error_label.setVisible(False)
        
    def load_notification_colors(self, app_settings):
        """Load notification colors from app settings."""
        if app_settings:
            self._unread_color = app_settings.get_setting("notification_unread_color", "#FF6B6B")
            self._read_color = app_settings.get_setting("notification_read_color", "#FFD93D")
            
            # Update button colors
            self.unread_color_btn.setStyleSheet(f"background-color: {self._unread_color}; border: 1px solid #ccc; border-radius: 3px;")
            self.read_color_btn.setStyleSheet(f"background-color: {self._read_color}; border: 1px solid #ccc; border-radius: 3px;")
    
    def save_notification_colors(self, app_settings):
        """Save notification colors to app settings."""
        if app_settings:
            app_settings.set_setting("notification_unread_color", self._unread_color)
            app_settings.set_setting("notification_read_color", self._read_color)

    def _open_folder(self, path: str):
        """Open a folder in the system file explorer in a cross-platform way.

        This method is used by the ConfigDialog buttons to open the DB/logs/app data
        folders. It is intentionally small and robust: errors are logged and shown
        in the dialog's error label instead of throwing exceptions back to callers.
        """
        import subprocess
        import os
        import sys
        try:
            if not path:
                raise ValueError('Path is empty')

            path = os.path.abspath(os.path.expanduser(path))
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception:
                    logger.exception('Unable to create path: %s', path)
                    self.show_error(f"Impossibile aprire o creare la cartella: {path}")
                    return

            if os.name == 'nt':
                try:
                    os.startfile(path)
                except Exception:
                    try:
                        subprocess.Popen(['explorer', path], shell=False)
                    except Exception:
                        logger.exception('Explorer fallback failed for path: %s', path)
                        try:
                            subprocess.Popen(['cmd', '/c', 'start', '""', path], shell=False)
                        except Exception:
                            logger.exception('cmd start fallback failed for path: %s', path)
                            try:
                                parent = os.path.dirname(path)
                                if parent and os.path.exists(parent):
                                    os.startfile(parent)
                                    return
                            except Exception:
                                logger.exception('Parent-folder fallback also failed for path: %s', path)
                                self.show_error(f"Impossibile aprire la cartella: {path}")
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                try:
                    subprocess.Popen(['xdg-open', path])
                except Exception:
                    for cmd in (('nautilus',), ('dolphin',), ('thunar',)):
                        try:
                            subprocess.Popen(list(cmd) + [path])
                        except Exception:
                            logger.exception('Linux fallback failed for path: %s', path)
                            self.show_error(f"Impossibile aprire la cartella: {path}")
        except Exception:
            logger.exception('Error opening folder: %s', path)
            try:
                self.show_error(f"Impossibile aprire la cartella: {path}")
            except Exception:
                # If show_error fails, there's nothing else to do safely here
                pass

    def _update_path_buttons(self, db_path: str, logs_path: str, app_data_path: str):
        """Update the existence indicators and enable/disable open-folder buttons."""
        import os

        try:
            # DB path may be a directory or a file path; check directory existence
            db_dir = os.path.dirname(db_path) if os.path.isabs(db_path) else db_path
            db_exists = os.path.exists(db_dir)
            logs_exists = os.path.exists(logs_path)
            app_data_exists = os.path.exists(app_data_path)

            # Update labels
            try:
                self._db_exists_label.setText("Percorso trovato" if db_exists else "Non trovato")
                self._db_exists_label.setStyleSheet("color: #28a745;" if db_exists else "color: #E74C3C;")
            except Exception:
                pass

            try:
                self._logs_exists_label.setText("Percorso trovato" if logs_exists else "Non trovato")
                self._logs_exists_label.setStyleSheet("color: #28a745;" if logs_exists else "color: #E74C3C;")
            except Exception:
                pass

            # Enable/disable buttons
            try:
                self.open_db_folder_btn.setEnabled(db_exists)
            except Exception:
                pass

            try:
                self.open_logs_folder_btn.setEnabled(logs_exists)
            except Exception:
                pass

        except Exception:
            # Defensive: if anything goes wrong just leave buttons enabled
            try:
                self.open_db_folder_btn.setEnabled(True)
                self.open_logs_folder_btn.setEnabled(True)
            except Exception:
                pass
