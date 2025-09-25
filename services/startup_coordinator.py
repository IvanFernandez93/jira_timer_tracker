"""
Coordinatore dell'avvio dell'applicazione per gestire il caricamento asincrono
e garantire un'esperienza utente fluida con controlli immediati.
"""
import logging
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QApplication

class BackgroundDataLoader(QThread):
    """Thread separato per il caricamento dei dati in background"""
    
    # Segnali per comunicare il progresso
    data_loaded = pyqtSignal(dict)  # Dati caricati con successo
    loading_failed = pyqtSignal(str)  # Errore durante il caricamento
    progress_updated = pyqtSignal(str, int)  # Nome task, percentuale
    
    def __init__(self, jira_service, db_service, app_settings):
        super().__init__()
        self.jira_service = jira_service
        self.db_service = db_service
        self.app_settings = app_settings
        self.logger = logging.getLogger(__name__)
        self._should_stop = False
    
    def stop_loading(self):
        """Ferma il caricamento in corso"""
        self._should_stop = True
        self.quit()
        self.wait()
    
    def run(self):
        """Esegue il caricamento dei dati in background"""
        try:
            self.logger.info("Avvio caricamento dati in background...")
            
            # 1. Caricamento dati offline dal database locale
            if self._should_stop:
                return
                
            self.progress_updated.emit("Caricamento dati offline...", 25)
            offline_data = self._load_offline_data()
            
            # 2. Tentativo connessione JIRA
            if self._should_stop:
                return
                
            self.progress_updated.emit("Connessione a JIRA...", 50)
            jira_connected = self._attempt_jira_connection()
            
            # 3. Caricamento dati JIRA se disponibili
            online_data = None
            if jira_connected and not self._should_stop:
                self.progress_updated.emit("Caricamento dati JIRA...", 75)
                online_data = self._load_jira_data()
            
            # 4. Finalizzazione
            if self._should_stop:
                return
                
            self.progress_updated.emit("Completamento...", 100)
            
            # Emetti i dati caricati
            result_data = {
                'offline_data': offline_data,
                'online_data': online_data,
                'jira_connected': jira_connected,
                'timestamp': QApplication.instance().property('startup_time')
            }
            
            self.data_loaded.emit(result_data)
            self.logger.info("Caricamento dati completato con successo")
            
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento: {e}")
            self.loading_failed.emit(str(e))
    
    def _load_offline_data(self) -> Dict[str, Any]:
        """Carica i dati disponibili offline dal database"""
        try:
            # Carica preferiti, cronologia, etc dal DB locale
            favorites = self.db_service.get_all_favorites() if self.db_service else []
            recent_issues = self.db_service.get_recent_issues(limit=50) if self.db_service else []
            
            return {
                'favorites': favorites,
                'recent_issues': recent_issues,
                'cached_data_available': len(favorites) > 0 or len(recent_issues) > 0
            }
        except Exception as e:
            self.logger.warning(f"Errore caricamento dati offline: {e}")
            return {'favorites': [], 'recent_issues': [], 'cached_data_available': False}
    
    def _attempt_jira_connection(self) -> bool:
        """Tenta la connessione a JIRA senza bloccare"""
        try:
            if not self.jira_service:
                return False
                
            # Verifica se abbiamo le credenziali
            jira_url = self.app_settings.get_setting("JIRA_URL") if self.app_settings else None
            if not jira_url:
                self.logger.info("URL JIRA non configurato - modalità offline")
                return False
            
            # Tenta la connessione con timeout breve
            return self.jira_service.test_connection_quick()
            
        except Exception as e:
            self.logger.warning(f"Connessione JIRA fallita: {e}")
            return False
    
    def _load_jira_data(self) -> Optional[Dict[str, Any]]:
        """Carica i dati da JIRA se la connessione è disponibile"""
        try:
            if not self.jira_service or self._should_stop:
                return None
            
            # Carica la JQL di default
            default_jql = self.app_settings.get_setting(
                'jql_query', 
                'assignee = currentUser() AND status != "Done"'
            ) if self.app_settings else 'assignee = currentUser() AND status != "Done"'
            
            # Carica un numero limitato di issues per l'avvio veloce
            issues = self.jira_service.search_issues(
                jql=default_jql,
                start_at=0,
                max_results=20  # Carica solo i primi 20 per l'avvio veloce
            )
            
            return {
                'initial_issues': issues,
                'default_jql': default_jql,
                'has_more_data': len(issues) == 20
            }
            
        except Exception as e:
            self.logger.warning(f"Errore caricamento dati JIRA: {e}")
            return None


class StartupCoordinator(QObject):
    """
    Coordinatore principale dell'avvio che gestisce il caricamento asincrono
    e garantisce che l'interfaccia sia immediatamente utilizzabile.
    """
    
    # Segnali per comunicare con il MainController
    ui_ready = pyqtSignal()  # L'UI è pronta per l'uso
    data_loading_progress = pyqtSignal(str, int)  # Progresso caricamento
    data_loaded = pyqtSignal(dict)  # Dati caricati completamente
    startup_completed = pyqtSignal()  # Avvio completato
    
    def __init__(self, main_controller):
        super().__init__()
        self.main_controller = main_controller
        self.logger = logging.getLogger(__name__)
        self.background_loader = None
        self.startup_timer = QTimer()
        self.startup_timer.setSingleShot(True)
        self.startup_timer.timeout.connect(self._on_startup_timeout)
        
        # Fasi dell'avvio
        self.phases = {
            'ui_initialization': False,
            'offline_data_loaded': False,
            'background_loading_started': False,
            'startup_completed': False
        }
    
    def start_coordinated_startup(self):
        """Avvia il processo di startup coordinato"""
        try:
            self.logger.info("=== Avvio Coordinato dell'Applicazione ===")
            
            # Fase 1: Inizializzazione immediata dell'UI
            self._initialize_immediate_ui()
            
            # Fase 2: Caricamento dati offline rapido
            self._load_immediate_offline_data()
            
            # Fase 3: Avvio caricamento background
            self._start_background_loading()
            
            # Timeout di sicurezza per evitare blocchi infiniti
            self.startup_timer.start(30000)  # 30 secondi max
            
        except Exception as e:
            self.logger.error(f"Errore durante l'avvio coordinato: {e}")
            self._handle_startup_failure(str(e))
    
    def _initialize_immediate_ui(self):
        """Inizializza immediatamente l'UI con controlli utilizzabili"""
        try:
            self.logger.info("Inizializzazione immediata UI...")
            
            # Mostra l'interfaccia principale
            main_window = self.main_controller.view
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            
            # Configura l'UI per la modalità "ready but loading"
            self._setup_immediate_ui_state()
            
            # Segnala che l'UI è pronta
            self.phases['ui_initialization'] = True
            self.ui_ready.emit()
            
            self.logger.info("UI inizializzata e pronta per l'uso")
            
        except Exception as e:
            self.logger.error(f"Errore inizializzazione UI: {e}")
            raise
    
    def _setup_immediate_ui_state(self):
        """Configura l'UI per essere immediatamente utilizzabile"""
        try:
            # Abilita tutti i controlli di navigazione
            main_window = self.main_controller.view
            
            # Abilita la barra di navigazione (se disponibile)
            if hasattr(main_window, 'navigationInterface') and hasattr(main_window.navigationInterface, 'setEnabled'):
                main_window.navigationInterface.setEnabled(True)
            
            # Configura la vista principale senza bloccare i controlli
            grid_view = main_window.jira_grid_view
            
            # Abilita la ricerca e i filtri anche senza dati
            grid_view.search_box.setEnabled(True)
            grid_view.search_box.setPlaceholderText("Cerca nei risultati (caricamento in corso...)")
            
            # Abilita tutti i pulsanti della toolbar
            self._enable_offline_controls()
            
            # Mostra un messaggio di stato discreto
            grid_view.show_status_message("Caricamento dati in corso...", is_loading=True)
            
        except Exception as e:
            self.logger.error(f"Errore setup UI state: {e}")
    
    def _enable_offline_controls(self):
        """Abilita tutti i controlli che funzionano offline"""
        try:
            main_window = self.main_controller.view
            
            # Abilita menu e toolbar
            main_window.setEnabled(True)
            
            # Abilita controlli specifici
            grid_view = main_window.jira_grid_view
            if hasattr(grid_view, 'refresh_btn'):
                grid_view.refresh_btn.setEnabled(True)
            if hasattr(grid_view, 'settings_btn'):
                grid_view.settings_btn.setEnabled(True)
            if hasattr(grid_view, 'notes_btn'):
                grid_view.notes_btn.setEnabled(True)
                
        except Exception as e:
            self.logger.error(f"Errore abilitazione controlli offline: {e}")
    
    def _load_immediate_offline_data(self):
        """Carica immediatamente i dati disponibili offline"""
        try:
            self.logger.info("Caricamento dati offline immediati...")
            
            # Carica cronologia in modo asincrono (non bloccante)
            if hasattr(self.main_controller, 'history_controller'):
                self.main_controller.history_controller.load_history()
            
            # Popola i dropdown dei preferiti
            self.main_controller._populate_jql_favorites()
            
            # Il caricamento dei cached issues viene fatto direttamente in _on_startup_ui_ready
            # Non è necessario farlo qui per evitare duplicazione
            
            self.phases['offline_data_loaded'] = True
            self.logger.info("Dati offline caricati con successo")
            
        except Exception as e:
            self.logger.warning(f"Errore caricamento dati offline: {e}")
            # Non è un errore critico, continua
    
    def _load_cached_issues(self):
        """Carica gli issues dalla cache locale"""
        try:
            if not hasattr(self.main_controller, 'db_service') or not self.main_controller.db_service:
                return []
                
            # Carica gli ultimi issues dalla cache
            recent_issues = self.main_controller.db_service.get_recent_issues(limit=20)
            return recent_issues
            
        except Exception as e:
            self.logger.warning(f"Errore caricamento cache issues: {e}")
            return []
    
    def _start_background_loading(self):
        """Avvia il caricamento dei dati in background"""
        try:
            self.logger.info("Avvio caricamento dati in background...")
            
            # Crea il loader in background
            self.background_loader = BackgroundDataLoader(
                self.main_controller.jira_service,
                self.main_controller.db_service,
                self.main_controller.app_settings
            )
            
            # Connetti i segnali
            self.background_loader.progress_updated.connect(self.data_loading_progress.emit)
            self.background_loader.data_loaded.connect(self._on_background_data_loaded)
            self.background_loader.loading_failed.connect(self._on_background_loading_failed)
            self.background_loader.finished.connect(self._on_background_loading_finished)
            
            # Avvia il thread
            self.background_loader.start()
            self.phases['background_loading_started'] = True
            
            self.logger.info("Caricamento background avviato")
            
        except Exception as e:
            self.logger.error(f"Errore avvio caricamento background: {e}")
            self._handle_startup_failure(str(e))
    
    def _on_background_data_loaded(self, data: Dict[str, Any]):
        """Gestisce i dati caricati in background"""
        try:
            self.logger.info("Dati background caricati con successo")
            
            # Ferma il timeout
            self.startup_timer.stop()
            
            # Aggiorna l'UI con i nuovi dati
            self._update_ui_with_loaded_data(data)
            
            # Segnala il completamento
            self.data_loaded.emit(data)
            self.phases['startup_completed'] = True
            self.startup_completed.emit()
            
        except Exception as e:
            self.logger.error(f"Errore gestione dati caricati: {e}")
    
    def _on_background_loading_failed(self, error_message: str):
        """Gestisce gli errori durante il caricamento background"""
        self.logger.warning(f"Caricamento background fallito: {error_message}")
        
        # Ferma il timeout
        self.startup_timer.stop()
        
        # Continua in modalità offline
        self._complete_offline_startup()
    
    def _on_background_loading_finished(self):
        """Gestisce il completamento del thread di caricamento"""
        if self.background_loader:
            self.background_loader = None
    
    def _update_ui_with_loaded_data(self, data: Dict[str, Any]):
        """Aggiorna l'UI con i dati caricati"""
        try:
            # Aggiorna lo stato della connessione
            jira_connected = data.get('jira_connected', False)
            self.main_controller._update_connection_status(jira_connected)
            
            # Se ci sono dati online, aggiorna la vista
            online_data = data.get('online_data')
            if online_data and online_data.get('initial_issues'):
                issues = online_data['initial_issues']
                self.main_controller._update_issues_display(issues)
                self.logger.info(f"Visualizzati {len(issues)} issues da JIRA")
            
            # Aggiorna lo stato dell'UI
            grid_view = self.main_controller.view.jira_grid_view
            grid_view.hide_loading_status()
            
            if jira_connected:
                grid_view.search_box.setPlaceholderText("Cerca nei risultati...")
            else:
                grid_view.search_box.setPlaceholderText("Cerca nei risultati (modalità offline)")
            
        except Exception as e:
            self.logger.error(f"Errore aggiornamento UI: {e}")
    
    def _complete_offline_startup(self):
        """Completa l'avvio in modalità offline"""
        try:
            self.logger.info("Completamento avvio in modalità offline")
            
            # Aggiorna l'UI per la modalità offline
            self.main_controller._update_connection_status(False)
            
            grid_view = self.main_controller.view.jira_grid_view
            grid_view.hide_loading_status()
            grid_view.search_box.setPlaceholderText("Cerca nei risultati (modalità offline)")
            
            self.phases['startup_completed'] = True
            self.startup_completed.emit()
            
        except Exception as e:
            self.logger.error(f"Errore completamento offline: {e}")
    
    def _on_startup_timeout(self):
        """Gestisce il timeout dell'avvio"""
        self.logger.warning("Timeout durante l'avvio - continuazione in modalità offline")
        
        if self.background_loader:
            self.background_loader.stop_loading()
        
        self._complete_offline_startup()
    
    def _handle_startup_failure(self, error_message: str):
        """Gestisce gli errori critici durante l'avvio"""
        self.logger.error(f"Errore critico durante l'avvio: {error_message}")
        
        try:
            # Tenta comunque di mostrare l'UI di base
            self.main_controller.view.show()
            
            # Mostra messaggio di errore
            grid_view = self.main_controller.view.jira_grid_view
            grid_view.show_error(f"Errore durante l'avvio: {error_message}")
            
        except Exception as e:
            self.logger.critical(f"Fallimento completo dell'avvio: {e}")
    
    def cleanup(self):
        """Pulizia delle risorse"""
        if self.background_loader:
            self.background_loader.stop_loading()
            self.background_loader = None
        
        self.startup_timer.stop()