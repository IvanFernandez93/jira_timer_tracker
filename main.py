import sys
import traceback
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtCore import QSettings
from qfluentwidgets import FluentTranslator, Theme, setTheme, isDarkTheme

from views.main_window import MainWindow
from views.config_dialog import ConfigDialog

from controllers.main_controller import MainController
from controllers.config_controller import ConfigController

from services.db_service import DatabaseService
from services.app_settings import AppSettings
from services.credential_service import CredentialService
from services.jira_service import JiraService

# Configurazione del logging
def setup_logging(app_settings=None):
    """Configurazione del sistema di logging."""
    # Crea la directory dei log se non esiste
    log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'JiraTimeTracker', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Nome del file di log con timestamp
    log_file = os.path.join(log_dir, f'jira_tracker_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    # Determina il livello di log appropriato basandosi sulle impostazioni
    log_level = logging.ERROR  # Livello predefinito, errori sempre visibili
    # Defaults for rotating file handler
    max_bytes = 5 * 1024 * 1024  # 5 MB default
    backup_count = 5

    use_filter = False
    # Se app_settings è disponibile, leggi le configurazioni
    if app_settings:
        # Allow explicit log level (e.g., 'DEBUG','INFO','WARNING','ERROR')
        lvl = app_settings.get_setting('log_level')
        if lvl:
            try:
                log_level = getattr(logging, lvl.upper(), logging.ERROR)
            except Exception:
                log_level = logging.ERROR

        # Optional rotating handler settings
        try:
            max_bytes = int(app_settings.get_setting('log_max_bytes') or max_bytes)
        except Exception:
            max_bytes = max_bytes
        try:
            backup_count = int(app_settings.get_setting('log_backup_count') or backup_count)
        except Exception:
            backup_count = backup_count

        # If explicit level not set, fallback to filters for individual levels
        if not lvl:
            # Crea un filtro personalizzato basato sulle impostazioni
            class LogLevelFilter(logging.Filter):
                def __init__(self, app_settings):
                    super().__init__()
                    self.app_settings = app_settings

                def filter(self, record):
                    # Gli errori e i log critici sono sempre visibili
                    if record.levelno >= logging.ERROR:
                        return True

                    # Per gli altri livelli, controlla le impostazioni
                    if record.levelno == logging.INFO:
                        return self.app_settings.get_setting("log_info", "true").lower() == "true"
                    elif record.levelno == logging.DEBUG:
                        return self.app_settings.get_setting("log_debug", "false").lower() == "true"
                    elif record.levelno == logging.WARNING:
                        return self.app_settings.get_setting("log_warning", "true").lower() == "true"

                    return True  # Per sicurezza, permetti tutti gli altri livelli

            use_filter = True

    # Configura il logger
    logger = logging.getLogger('JiraTimeTracker')
    logger.setLevel(log_level)

    # Rimuovi gli handler esistenti se presenti (per evitare duplicazioni)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Rotating file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s'))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s'))

    if app_settings and use_filter:
        log_filter = LogLevelFilter(app_settings)
        console_handler.addFilter(log_filter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Avoid propagating to root handlers
    logger.propagate = False

    # Also configure the root logger so module-level loggers (logging.getLogger(__name__))
    # propagate to the same handlers and therefore show up on console/file.
    root_logger = logging.getLogger()
    # Remove existing handlers on root to avoid duplicates when reconfiguring
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return logger

# Gestore delle eccezioni globale
def exception_handler(exc_type, exc_value, exc_traceback):
    """Gestore globale delle eccezioni non catturate."""
    # Registra l'errore nei log
    logger = logging.getLogger('JiraTimeTracker')
    logger.critical("Eccezione non gestita:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Mostra un messaggio all'utente
    error_msg = f"{exc_type.__name__}: {exc_value}"
    error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    msg_box = QMessageBox()
    try:
        # Ensure the message box is shown on top of other windows
        msg_box.setWindowFlag(QMessageBox.WindowType.WindowStaysOnTopHint, True)
    except Exception:
        # setWindowFlag may not be available on some Qt wrappers; ignore safely
        pass
    msg_box.setWindowTitle("Errore nell'applicazione")
    msg_box.setText("Si è verificato un errore imprevisto nell'applicazione.")
    msg_box.setInformativeText(error_msg)
    msg_box.setDetailedText(error_details)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.exec()

def main():
    # Configurazione iniziale del logging (prima di caricare le impostazioni)
    logger = setup_logging()
    
    # Imposta il gestore delle eccezioni globale
    sys.excepthook = exception_handler
    
    app = QApplication(sys.argv)
    app.setOrganizationName("JiraTimeTracker")
    app.setApplicationName("JiraTimeTracker")
    
    # Initialize the theme based on saved settings or system preference
    settings = QSettings()
    use_dark = settings.value('theme/dark', None)
    
    # If no saved preference, use system theme
    if use_dark is None:
        # Default to system theme if not set
        from PyQt6.QtGui import QPalette
        use_dark = app.style().standardPalette().color(QPalette.ColorRole.Window).lightness() < 128
    else:
        use_dark = bool(int(use_dark))  # Convert from QVariant to bool
    
    # Apply theme
    setTheme(Theme.DARK if use_dark else Theme.LIGHT)

    # Internationalization
    translator = FluentTranslator()
    app.installTranslator(translator)

    # Initialize icons now that QApplication is ready
    from qfluentwidgets import init_icons
    init_icons()

    # 1. Initialize all services
    db_service = DatabaseService()
    db_service.initialize_db()

    app_settings = AppSettings(db_service)
    # Forza il livello di log a DEBUG per debug temporaneo
    app_settings.set_setting('log_level', 'DEBUG')
    cred_service = CredentialService()

    # Read retry/log configuration from settings (with sensible defaults)
    def _parse_int(value, default):
        try:
            return int(value)
        except Exception:
            return default

    def _parse_float(value, default):
        try:
            return float(value)
        except Exception:
            return default

    max_retries = _parse_int(app_settings.get_setting('jira/max_retries'), 3)
    base_retry_delay = _parse_float(app_settings.get_setting('jira/base_retry_delay'), 0.5)
    max_delay = _parse_float(app_settings.get_setting('jira/max_delay'), 30.0)

    # Parse non-retryable statuses if provided (comma-separated)
    non_retry_csv = app_settings.get_setting('jira/non_retryable_statuses')
    non_retryable_statuses = None
    if non_retry_csv:
        try:
            non_retryable_statuses = [int(s.strip()) for s in non_retry_csv.split(',') if s.strip()]
        except Exception:
            non_retryable_statuses = None

    # Instantiate JiraService with configured retry policy
    jira_service = JiraService(
        max_retries=max_retries,
        base_retry_delay=base_retry_delay,
        max_delay=max_delay,
        non_retryable_statuses=non_retryable_statuses,
    )
    
    # Riconfigura il logging con le impostazioni caricate
    logger = setup_logging(app_settings)
    logger.info("Applicazione avviata con impostazioni di logging configurate")

    # 2. Check for initial configuration (req 2.1.1)
    jira_url = app_settings.get_setting("JIRA_URL")
    pat = cred_service.get_pat(jira_url)

    if not jira_url or not pat:
        config_dialog = ConfigDialog()
        config_controller = ConfigController(config_dialog, jira_service, app_settings, cred_service)
        config_controller.set_db_service(db_service)
        result = config_controller.run()

        if result == QDialog.DialogCode.Rejected:
            sys.exit(0) # User cancelled configuration, so we exit.
        
        # Re-fetch credentials after they've been saved
        jira_url = app_settings.get_setting("JIRA_URL")
        pat = cred_service.get_pat(jira_url)

    # 3. Attempt to connect to Jira on startup
    try:
        logger.info(f"Connecting to {jira_url}...")
        jira_service.connect(jira_url, pat)
        logger.info("Connection successful.")
    except Exception as e:
        logger.error(f"Could not connect to Jira on startup: {e}", exc_info=True)
        # Mostra un messaggio di errore non bloccante
        try:
            warning_box = QMessageBox()
            try:
                warning_box.setWindowFlag(QMessageBox.WindowType.WindowStaysOnTopHint, True)
            except Exception:
                pass
            warning_box.setIcon(QMessageBox.Icon.Warning)
            warning_box.setWindowTitle("Errore di connessione")
            warning_box.setText(f"Impossibile connettersi a Jira: {str(e)}\n\nL'applicazione funzionerà in modalità disconnessa.")
            warning_box.exec()
        except Exception:
            # Final fallback: log and continue (do not crash the app because of UI errors)
            logger.exception('Failed to show connection warning dialog')
    
    # 4. Setup main window and controller (MVC)
    main_window = MainWindow()
    main_controller = MainController(main_window, db_service, jira_service, app_settings)
    main_controller.show_initial_view() # Show default view (req 2.3.5)
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
