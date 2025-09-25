#!/usr/bin/env python3
"""
Async History Loader - Caricamento asincrono della cronologia senza bloccare l'UI
"""

import logging
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

class AsyncHistoryWorker(QObject):
    """Worker per caricare i titoli degli issue asincronamente"""
    
    # Signals
    title_loaded = pyqtSignal(str, str, str)  # jira_key, title, status
    batch_completed = pyqtSignal(int)  # numero di titoli caricati in questo batch
    all_completed = pyqtSignal()
    
    def __init__(self, jira_service, db_service, issue_keys: List[str]):
        super().__init__()
        self.jira_service = jira_service
        self.db_service = db_service
        self.issue_keys = issue_keys
        self.logger = logging.getLogger('JiraTimeTracker.AsyncHistoryWorker')
        self._should_stop = False
        
    def load_titles_async(self):
        """Carica i titoli degli issue asincronamente in piccoli batch"""
        try:
            batch_size = 3  # Carica massimo 3 issue per volta per non sovraccaricare
            loaded_count = 0
            
            for i in range(0, len(self.issue_keys), batch_size):
                if self._should_stop:
                    break
                    
                batch_keys = self.issue_keys[i:i + batch_size]
                batch_loaded = 0
                
                for jira_key in batch_keys:
                    if self._should_stop:
                        break
                        
                    try:
                        # Controlla prima se abbiamo il titolo in cache nel database
                        cached_title = self._get_cached_title(jira_key)
                        if cached_title:
                            self.title_loaded.emit(jira_key, cached_title, "")
                            batch_loaded += 1
                            continue
                            
                        # Controlla se l'issue è fittizio prima di fare chiamata API
                        if self.jira_service.is_likely_fictitious_ticket(jira_key):
                            title = f"Issue fittizio: {jira_key}"
                            self.title_loaded.emit(jira_key, title, "")
                            batch_loaded += 1
                            continue
                            
                        # Fai la chiamata API solo se necessario
                        issue_data = self.jira_service.get_issue(jira_key)
                        if issue_data:
                            title = issue_data.get('fields', {}).get('summary', 'Titolo non disponibile')
                            status = issue_data.get('fields', {}).get('status', {}).get('name', '')
                            
                            # Salva in cache per future use
                            self._cache_issue_data(jira_key, title, status)
                            
                            self.title_loaded.emit(jira_key, title, status)
                            batch_loaded += 1
                        else:
                            self.title_loaded.emit(jira_key, "Titolo non disponibile", "")
                            batch_loaded += 1
                            
                    except Exception as e:
                        self.logger.warning(f"Errore caricamento titolo per {jira_key}: {e}")
                        self.title_loaded.emit(jira_key, "Errore caricamento titolo", "")
                        batch_loaded += 1
                        
                    # Piccola pausa per non sovraccaricare
                    QApplication.processEvents()
                
                loaded_count += batch_loaded
                self.batch_completed.emit(batch_loaded)
                
                # Pausa tra i batch per mantenere l'UI responsive
                if i + batch_size < len(self.issue_keys) and not self._should_stop:
                    QThread.msleep(100)  # 100ms di pausa
            
            if not self._should_stop:
                self.all_completed.emit()
                
        except Exception as e:
            self.logger.error(f"Errore nel caricamento asincrono della cronologia: {e}")
            
    def _get_cached_title(self, jira_key: str) -> Optional[str]:
        """Recupera il titolo dalla cache del database"""
        try:
            # Cerca negli issue salvati nel database
            cached_issues = self.db_service.get_recent_issues(limit=100)
            for issue in cached_issues:
                if issue.get('key') == jira_key and issue.get('summary'):
                    return issue['summary']
            return None
        except Exception as e:
            self.logger.debug(f"Errore recupero cache per {jira_key}: {e}")
            return None
            
    def _cache_issue_data(self, jira_key: str, title: str, status: str):
        """Salva i dati dell'issue in cache"""
        try:
            # Qui potresti implementare un sistema di cache più sofisticato
            # Per ora non facciamo nulla per non complicare il database
            pass
        except Exception as e:
            self.logger.debug(f"Errore salvataggio cache per {jira_key}: {e}")
            
    def stop(self):
        """Ferma il worker"""
        self._should_stop = True


class AsyncHistoryLoader(QObject):
    """Loader principale per la gestione asincrona della cronologia"""
    
    # Signals
    title_updated = pyqtSignal(str, str, str)  # jira_key, title, status
    loading_progress = pyqtSignal(int, int)  # loaded, total
    loading_completed = pyqtSignal()
    
    def __init__(self, jira_service, db_service):
        super().__init__()
        self.jira_service = jira_service
        self.db_service = db_service
        self.logger = logging.getLogger('JiraTimeTracker.AsyncHistoryLoader')
        
        self.worker = None
        self.worker_thread = None
        self._loaded_count = 0
        self._total_count = 0
        
    def load_titles_async(self, issue_keys: List[str]):
        """Avvia il caricamento asincrono dei titoli"""
        if not issue_keys:
            self.loading_completed.emit()
            return
            
        self.logger.info(f"Avvio caricamento asincrono di {len(issue_keys)} titoli issue")
        
        # Ferma qualsiasi caricamento precedente
        self.stop_loading()
        
        # Imposta contatori
        self._loaded_count = 0
        self._total_count = len(issue_keys)
        
        # Crea worker e thread
        self.worker = AsyncHistoryWorker(self.jira_service, self.db_service, issue_keys)
        self.worker_thread = QThread()
        
        # Sposta worker nel thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connetti segnali
        self.worker.title_loaded.connect(self._on_title_loaded)
        self.worker.batch_completed.connect(self._on_batch_completed)
        self.worker.all_completed.connect(self._on_loading_completed)
        
        # Connetti thread signals
        self.worker_thread.started.connect(self.worker.load_titles_async)
        self.worker_thread.finished.connect(self._cleanup_thread)
        
        # Avvia il thread
        self.worker_thread.start()
        
    def _on_title_loaded(self, jira_key: str, title: str, status: str):
        """Gestisce il caricamento di un singolo titolo"""
        self.title_updated.emit(jira_key, title, status)
        
    def _on_batch_completed(self, batch_size: int):
        """Gestisce il completamento di un batch"""
        self._loaded_count += batch_size
        self.loading_progress.emit(self._loaded_count, self._total_count)
        
    def _on_loading_completed(self):
        """Gestisce il completamento del caricamento"""
        self.logger.info(f"Caricamento asincrono cronologia completato: {self._loaded_count}/{self._total_count}")
        self.loading_completed.emit()
        self.stop_loading()
        
    def stop_loading(self):
        """Ferma il caricamento in corso"""
        if self.worker:
            self.worker.stop()
            
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(3000)  # Aspetta max 3 secondi
            
    def _cleanup_thread(self):
        """Pulisce le risorse del thread"""
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
            
        if self.worker:
            self.worker.deleteLater()
            self.worker = None