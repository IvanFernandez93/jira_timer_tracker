import socket
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings

logger = logging.getLogger('JiraTimeTracker')

class NetworkService(QObject):
    """
    Servizio per monitorare lo stato della connessione internet e JIRA.
    Fornisce segnali per notificare cambiamenti nello stato della connessione.
    """
    # Segnali per cambiamenti dello stato della connessione
    connection_changed = pyqtSignal(bool)  # True quando la connessione è disponibile, False altrimenti
    jira_connection_changed = pyqtSignal(bool)  # True quando JIRA è disponibile, False altrimenti
    
    def __init__(self, jira_service=None, check_interval=30000):
        """
        Inizializza il servizio di rete.
        
        Args:
            jira_service: Istanza di JiraService per verificare la connessione a JIRA
            check_interval: Intervallo in millisecondi per controllare lo stato della connessione
        """
        super().__init__()
        self.jira_service = jira_service
        self.check_interval = check_interval
        self.is_internet_available = False
        self.is_jira_available = False
        self._last_known_jira_state = False
        self._internet_check_hosts = [
            # DNS Google
            ('8.8.8.8', 53),
            # DNS Cloudflare
            ('1.1.1.1', 53),
            # Fallback al DNS locale se configurato
            (socket.gethostbyname(socket.gethostname()), 53)
        ]
        
        # Avvio il timer per controllare periodicamente la connessione
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_connection)
        self.check_timer.setInterval(check_interval)
        
    def start_monitoring(self):
        """Avvia il monitoraggio della connessione."""
        # Controllo immediato dello stato
        self.check_connection()
        # Avvio del timer per controlli periodici
        self.check_timer.start()
        logger.info("Monitoraggio della connessione avviato")
        
    def stop_monitoring(self):
        """Ferma il monitoraggio della connessione."""
        self.check_timer.stop()
        logger.info("Monitoraggio della connessione fermato")
        
    def check_connection(self):
        """
        Controlla lo stato della connessione internet e JIRA.
        Emette segnali quando lo stato cambia.
        """
        # Controlla connessione internet
        internet_available = self._check_internet_connection()
        
        # Se lo stato è cambiato, emetti il segnale
        if internet_available != self.is_internet_available:
            self.is_internet_available = internet_available
            self.connection_changed.emit(internet_available)
            logger.info(f"Stato connessione internet cambiato: {'disponibile' if internet_available else 'non disponibile'}")
        
        # Se la connessione internet è disponibile, controlla JIRA
        jira_available = False
        if internet_available and self.jira_service:
            # Prima verifica se il DNS può essere risolto
            try:
                socket.gethostbyname("sviluppo.maggiolicloud.it")
                can_resolve_dns = True
            except socket.error:
                can_resolve_dns = False
                logger.warning("Impossibile risolvere il nome host di JIRA (DNS non raggiungibile)")
            
            # Procedi solo se il DNS può essere risolto
            if can_resolve_dns:
                try:
                    if self.jira_service.is_connected():
                        # Test reale della connessione a JIRA
                        try:
                            # Esegui una query minima per verificare che la connessione funzioni
                            # Usa una query che richiede pochi dati, senza consumare troppe risorse
                            # Questa query torna un massimo di 1 risultato
                            self.jira_service.search_issues("created >= now() AND created <= now()", max_results=1)
                            jira_available = True
                        except Exception as e:
                            logger.warning(f"Test connessione JIRA fallito: {e}")
                            jira_available = False
                    else:
                        # Tenta di riconnettersi se le credenziali sono disponibili
                        try:
                            # Recupera le credenziali
                            from PyQt6.QtCore import QSettings
                            settings = QSettings()
                            settings.beginGroup("Jira")
                            jira_url = settings.value("url", "")
                            settings.endGroup()
                            
                            # Recupera il PAT
                            from services.credential_service import CredentialService
                            cred_service = CredentialService()
                            pat = cred_service.get_pat(jira_url)
                            
                            if jira_url and pat:
                                # Tenta la riconnessione
                                logger.info(f"Tentativo di riconnessione a JIRA: {jira_url}")
                                self.jira_service.connect(jira_url, pat)
                                jira_available = True
                                logger.info("Riconnessione a JIRA riuscita")
                        except Exception as e:
                            logger.warning(f"Tentativo di riconnessione a JIRA fallito: {e}")
                            jira_available = False
                except Exception as e:
                    logger.warning(f"Errore nel controllo della connessione JIRA: {e}")
                    jira_available = False
        
        # Se lo stato di JIRA è cambiato, emetti il segnale
        if jira_available != self.is_jira_available:
            self.is_jira_available = jira_available
            self.jira_connection_changed.emit(jira_available)
            logger.info(f"Stato connessione JIRA cambiato: {'disponibile' if jira_available else 'non disponibile'}")
    
    def _check_internet_connection(self) -> bool:
        """
        Controlla se la connessione internet è disponibile.
        
        Returns:
            bool: True se la connessione è disponibile, False altrimenti.
        """
        for host, port in self._internet_check_hosts:
            try:
                socket.setdefaulttimeout(2)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
                return True
            except socket.error:
                continue
        return False