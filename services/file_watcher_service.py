"""
File Watcher Service per monitorare le modifiche esterne ai file delle note.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib

from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher, QTimer
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

@dataclass
class WatchedFile:
    """Informazioni su un file monitorato."""
    file_path: Path
    note_id: int
    last_hash: str
    last_modified: datetime
    jira_key: str
    title: str

class FileWatcherService(QObject):
    """
    Servizio per monitorare le modifiche esterne ai file delle note.
    Rileva quando un file viene modificato esternamente e notifica l'applicazione.
    """
    
    # Segnali emessi quando viene rilevata una modifica
    file_changed_externally = pyqtSignal(int, str, str)  # note_id, file_path, new_content
    file_deleted_externally = pyqtSignal(int, str)       # note_id, file_path
    
    def __init__(self, fs_manager, db_service):
        super().__init__()
        self.fs_manager = fs_manager
        self.db_service = db_service
        
        # File system watcher di PyQt6
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        self.file_watcher.directoryChanged.connect(self._on_directory_changed)
        
        # Mappa dei file monitorati: file_path -> WatchedFile
        self.watched_files: Dict[str, WatchedFile] = {}
        
        # Timer per raggruppare le modifiche multiple
        self.change_timer = QTimer()
        self.change_timer.timeout.connect(self._process_pending_changes)
        self.change_timer.setSingleShot(True)
        self.pending_changes: Set[str] = set()
        
        # Set di percorsi che stiamo ignorando (per evitare loop quando salviamo)
        self.ignored_paths: Set[str] = set()
        
        logger.info("File Watcher Service initialized")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcola l'hash MD5 del contenuto del file."""
        try:
            if not file_path.exists():
                return ""
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def _read_file_content(self, file_path: Path) -> str:
        """Legge il contenuto del file."""
        try:
            if not file_path.exists():
                return ""
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""
    
    def add_note_to_watch(self, note_id: int, jira_key: str, title: str, content: str = None):
        """
        Aggiunge una nota al monitoraggio.
        
        Args:
            note_id: ID della nota nel database
            jira_key: Chiave JIRA (può essere vuota per note generali)  
            title: Titolo della nota
            content: Contenuto attuale (opzionale, per calcolare l'hash)
        """
        try:
            # Ottieni il percorso del file
            file_path = self.fs_manager.get_note_file_path(jira_key, title, note_id)
            file_path_str = str(file_path)
            
            # Calcola l'hash del contenuto attuale
            if content is not None:
                current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            else:
                current_hash = self._calculate_file_hash(file_path)
            
            # Crea l'oggetto WatchedFile
            watched_file = WatchedFile(
                file_path=file_path,
                note_id=note_id,
                last_hash=current_hash,
                last_modified=datetime.now(),
                jira_key=jira_key or "",
                title=title
            )
            
            # Aggiungi alla mappa
            self.watched_files[file_path_str] = watched_file
            
            # Aggiungi al file watcher se il file esiste
            if file_path.exists():
                self.file_watcher.addPath(file_path_str)
                logger.debug(f"Started watching file: {file_path_str}")
            
            # Monitora anche la directory padre per rilevare la creazione del file
            parent_dir = str(file_path.parent)
            if parent_dir not in self.file_watcher.directories():
                self.file_watcher.addPath(parent_dir)
                
        except Exception as e:
            logger.error(f"Error adding note {note_id} to watch: {e}")
    
    def remove_note_from_watch(self, note_id: int):
        """Rimuove una nota dal monitoraggio."""
        try:
            # Trova il file corrispondente alla nota
            file_to_remove = None
            for file_path_str, watched_file in self.watched_files.items():
                if watched_file.note_id == note_id:
                    file_to_remove = file_path_str
                    break
            
            if file_to_remove:
                # Rimuovi dal file watcher
                if file_to_remove in self.file_watcher.files():
                    self.file_watcher.removePath(file_to_remove)
                
                # Rimuovi dalla mappa
                del self.watched_files[file_to_remove]
                logger.debug(f"Stopped watching file: {file_to_remove}")
                
        except Exception as e:
            logger.error(f"Error removing note {note_id} from watch: {e}")
    
    def ignore_next_change(self, file_path: str):
        """
        Ignora il prossimo cambiamento per il file specificato.
        Utile quando salviamo dall'applicazione per evitare loop.
        """
        self.ignored_paths.add(file_path)
        
        # Rimuovi dall'ignore dopo un breve delay
        QTimer.singleShot(1000, lambda: self.ignored_paths.discard(file_path))
    
    def _on_file_changed(self, file_path: str):
        """Callback chiamato quando un file monitorato cambia."""
        try:
            # Se stiamo ignorando questo file, non fare nulla
            if file_path in self.ignored_paths:
                logger.debug(f"Ignoring change for {file_path} (internal save)")
                return
            
            logger.debug(f"File changed detected: {file_path}")
            
            # Aggiungi ai cambiamenti in sospeso
            self.pending_changes.add(file_path)
            
            # Avvia il timer per processare i cambiamenti (raggruppa le modifiche multiple)
            self.change_timer.start(500)  # 500ms delay
            
        except Exception as e:
            logger.error(f"Error handling file change for {file_path}: {e}")
    
    def _on_directory_changed(self, dir_path: str):
        """Callback chiamato quando una directory monitorata cambia."""
        try:
            logger.debug(f"Directory changed: {dir_path}")
            
            # Controlla se sono stati creati nuovi file per le note monitorate
            for file_path_str, watched_file in self.watched_files.items():
                if str(watched_file.file_path.parent) == dir_path:
                    if watched_file.file_path.exists() and file_path_str not in self.file_watcher.files():
                        # File creato, inizia a monitorarlo
                        self.file_watcher.addPath(file_path_str)
                        logger.debug(f"Started watching newly created file: {file_path_str}")
                        
        except Exception as e:
            logger.error(f"Error handling directory change for {dir_path}: {e}")
    
    def _process_pending_changes(self):
        """Processa tutti i cambiamenti in sospeso."""
        try:
            changes_to_process = list(self.pending_changes)
            self.pending_changes.clear()
            
            for file_path_str in changes_to_process:
                self._process_file_change(file_path_str)
                
        except Exception as e:
            logger.error(f"Error processing pending changes: {e}")
    
    def _process_file_change(self, file_path_str: str):
        """Processa il cambiamento di un singolo file."""
        try:
            if file_path_str not in self.watched_files:
                return
            
            watched_file = self.watched_files[file_path_str]
            file_path = Path(file_path_str)
            
            # Controlla se il file esiste ancora
            if not file_path.exists():
                logger.info(f"File deleted externally: {file_path_str}")
                self.file_deleted_externally.emit(watched_file.note_id, file_path_str)
                return
            
            # Calcola il nuovo hash
            new_hash = self._calculate_file_hash(file_path)
            
            # Se l'hash è cambiato, il file è stato modificato
            if new_hash != watched_file.last_hash:
                logger.info(f"File modified externally: {file_path_str}")
                
                # Leggi il nuovo contenuto
                new_content = self._read_file_content(file_path)
                
                # Aggiorna l'hash memorizzato
                watched_file.last_hash = new_hash
                watched_file.last_modified = datetime.now()
                
                # Emetti il segnale
                self.file_changed_externally.emit(watched_file.note_id, file_path_str, new_content)
            
        except Exception as e:
            logger.error(f"Error processing file change for {file_path_str}: {e}")
    
    def update_note_info(self, note_id: int, new_jira_key: str, new_title: str, new_content: str):
        """
        Aggiorna le informazioni di una nota monitorata.
        Utile quando la nota viene rinominata o spostata.
        """
        try:
            # Prima rimuovi dalla watch
            self.remove_note_from_watch(note_id)
            
            # Poi aggiungi con le nuove informazioni
            self.add_note_to_watch(note_id, new_jira_key, new_title, new_content)
            
        except Exception as e:
            logger.error(f"Error updating watch info for note {note_id}: {e}")
    
    def get_watched_files_info(self) -> Dict[int, str]:
        """
        Restituisce le informazioni sui file monitorati.
        Returns: Dict[note_id, file_path]
        """
        return {watched.note_id: str(watched.file_path) for watched in self.watched_files.values()}
    
    def stop_watching_all(self):
        """Ferma il monitoraggio di tutti i file."""
        try:
            for file_path in list(self.file_watcher.files()):
                self.file_watcher.removePath(file_path)
            
            for dir_path in list(self.file_watcher.directories()):
                self.file_watcher.removePath(dir_path)
            
            self.watched_files.clear()
            logger.info("Stopped watching all files")
            
        except Exception as e:
            logger.error(f"Error stopping file watching: {e}")