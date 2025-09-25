"""
Advanced Note Management System with optimized performance and error handling.
This module provides a robust, high-performance note management layer.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)

@dataclass
class NoteState:
    """Represents the current state of a note."""
    note_id: Optional[int]
    is_draft: bool
    is_committed: bool
    is_new: bool
    last_saved: Optional[str]
    last_committed: Optional[str]
    
    @property
    def state_name(self) -> str:
        """Get the current state name."""
        if self.is_new:
            return 'new'
        elif self.is_draft:
            return 'draft'
        else:
            return 'committed'

@dataclass
class NoteData:
    """Encapsulates note data with validation."""
    jira_key: str
    title: str
    content: str
    tags: str
    is_fictitious: bool
    
    def validate(self) -> Tuple[bool, str]:
        """Validate note data."""
        if not self.title.strip():
            return False, "Il titolo è obbligatorio"
        if len(self.title) > 200:
            return False, "Il titolo è troppo lungo (max 200 caratteri)"
        if len(self.content) > 50000:
            return False, "Il contenuto è troppo lungo (max 50000 caratteri)"
        return True, ""

class NoteManager(QObject):
    """
    Advanced note management with performance optimizations and error handling.
    Manages the complete lifecycle of notes with state tracking.
    """
    
    # Signals for UI updates
    note_state_changed = pyqtSignal(object)  # NoteState
    note_saved = pyqtSignal(int, str)  # note_id, message
    note_error = pyqtSignal(str)  # error_message
    
    def __init__(self, db_service, git_service):
        super().__init__()
        self.db_service = db_service
        self.git_service = git_service
        self.current_note_state = None
        self._note_cache = {}  # Performance cache
        self._setup_auto_save_timer()
        
    def _setup_auto_save_timer(self):
        """Setup auto-save timer for draft notes."""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save_draft)
        self.auto_save_timer.setInterval(5000)  # 5 seconds
        
    def load_note(self, note_id: int) -> Tuple[bool, Optional[Dict], Optional[NoteState]]:
        """
        Load a note and determine its state.
        Returns: (success, note_data, note_state)
        """
        try:
            # Check cache first for performance
            if note_id in self._note_cache:
                note = self._note_cache[note_id]
            else:
                note = self.db_service.get_note_by_id(note_id)
                if note:
                    self._note_cache[note_id] = note
            
            if not note:
                return False, None, None
            
            # Determine note state
            state = self._determine_note_state(note)
            self.current_note_state = state
            
            return True, note, state
            
        except Exception as e:
            logger.error(f"Error loading note {note_id}: {e}")
            self.note_error.emit(f"Errore nel caricamento della nota: {e}")
            return False, None, None
    
    def _determine_note_state(self, note: Dict) -> NoteState:
        """Determine the current state of a note."""
        is_draft = note.get('is_draft', False)
        has_commit = bool(note.get('last_commit_hash'))
        
        return NoteState(
            note_id=note['id'],
            is_draft=is_draft,
            is_committed=not is_draft and has_commit,
            is_new=False,  # Existing note
            last_saved=note.get('draft_saved_at'),
            last_committed=note.get('last_commit_hash')
        )
    
    def create_new_note(self, note_data: NoteData) -> Tuple[bool, Optional[int], Optional[NoteState]]:
        """
        Create a new note as draft.
        Returns: (success, note_id, note_state)
        """
        try:
            # Validate data
            valid, error_msg = note_data.validate()
            if not valid:
                self.note_error.emit(error_msg)
                return False, None, None
            
            # Create note as draft
            note_id = self.db_service.save_note_as_draft(
                jira_key=note_data.jira_key,
                title=note_data.title,
                content=note_data.content,
                tags=note_data.tags,
                is_fictitious=note_data.is_fictitious
            )
            
            if note_id:
                # Clear cache
                self._invalidate_cache()
                
                # Create new state
                state = NoteState(
                    note_id=note_id,
                    is_draft=True,
                    is_committed=False,
                    is_new=False,  # Now saved
                    last_saved=datetime.now(timezone.utc).isoformat(),
                    last_committed=None
                )
                
                self.current_note_state = state
                self.note_saved.emit(note_id, "Nuova nota creata come bozza")
                self.note_state_changed.emit(state)
                
                return True, note_id, state
            
            return False, None, None
            
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            self.note_error.emit(f"Errore nella creazione della nota: {e}")
            return False, None, None
    
    def save_draft(self, note_id: int, note_data: NoteData) -> bool:
        """Save note as draft with validation and error handling."""
        try:
            # Validate data
            valid, error_msg = note_data.validate()
            if not valid:
                self.note_error.emit(error_msg)
                return False
            
            # Save draft
            success = self.db_service.save_note_as_draft(
                note_id=note_id,
                content=note_data.content,
                tags=note_data.tags,
                is_fictitious=note_data.is_fictitious
            )
            
            if success:
                # Update cache
                if note_id in self._note_cache:
                    self._note_cache[note_id].update({
                        'content': note_data.content,
                        'tags': note_data.tags,
                        'is_fictitious': note_data.is_fictitious,
                        'is_draft': True,
                        'draft_saved_at': datetime.now(timezone.utc).isoformat()
                    })
                
                # Update state
                if self.current_note_state and self.current_note_state.note_id == note_id:
                    self.current_note_state.last_saved = datetime.now(timezone.utc).isoformat()
                    self.note_state_changed.emit(self.current_note_state)
                
                self.note_saved.emit(note_id, "Bozza salvata")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving draft {note_id}: {e}")
            self.note_error.emit(f"Errore nel salvare la bozza: {e}")
            return False
    
    def commit_note(self, note_id: int, commit_message: str) -> bool:
        """Commit note to git with full validation and error handling."""
        try:
            # Get current note data
            note = self.db_service.get_note_by_id(note_id)
            if not note:
                self.note_error.emit("Nota non trovata")
                return False
            
            # Validate note data
            note_data = NoteData(
                jira_key=note['jira_key'] or 'GENERAL',
                title=note['title'],
                content=note['content'],
                tags=note['tags'] or '',
                is_fictitious=note.get('is_fictitious', False)
            )
            
            valid, error_msg = note_data.validate()
            if not valid:
                self.note_error.emit(error_msg)
                return False
            
            # Prepare metadata for git
            metadata = {
                'jira_key': note_data.jira_key,
                'title': note_data.title,
                'tags': note_data.tags,
                'created_at': note['created_at'],
                'is_fictitious': note_data.is_fictitious
            }
            
            # Commit to git
            commit_hash = self.git_service.commit_note(
                note_data.jira_key,
                note_data.title,
                note_data.content,
                metadata,
                commit_message
            )
            
            if commit_hash:
                # Mark as committed in database
                success = self.db_service.commit_note(note_id, commit_hash)
                
                if success:
                    # Update cache
                    if note_id in self._note_cache:
                        self._note_cache[note_id].update({
                            'is_draft': False,
                            'last_commit_hash': commit_hash
                        })
                    
                    # Update state
                    if self.current_note_state and self.current_note_state.note_id == note_id:
                        self.current_note_state.is_draft = False
                        self.current_note_state.is_committed = True
                        self.current_note_state.last_committed = commit_hash
                        self.note_state_changed.emit(self.current_note_state)
                    
                    self.note_saved.emit(note_id, f"Nota committata: {commit_hash[:8]}")
                    return True
            
            self.note_error.emit("Errore nel commit git")
            return False
            
        except Exception as e:
            logger.error(f"Error committing note {note_id}: {e}")
            self.note_error.emit(f"Errore nel commit: {e}")
            return False
    
    def convert_to_draft(self, note_id: int) -> bool:
        """Convert a committed note back to draft state."""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            conn = self.db_service.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE Annotations SET IsDraft = 1, DraftSavedAt = ?, UpdatedAt = ? WHERE Id = ?',
                (current_time, current_time, note_id)
            )
            conn.commit()
            conn.close()
            
            # Update cache
            if note_id in self._note_cache:
                self._note_cache[note_id].update({
                    'is_draft': True,
                    'draft_saved_at': current_time
                })
            
            # Update state
            if self.current_note_state and self.current_note_state.note_id == note_id:
                self.current_note_state.is_draft = True
                self.current_note_state.is_committed = False
                self.current_note_state.last_saved = current_time
                self.note_state_changed.emit(self.current_note_state)
            
            self.note_saved.emit(note_id, "Nota convertita in bozza")
            return True
            
        except Exception as e:
            logger.error(f"Error converting note to draft {note_id}: {e}")
            self.note_error.emit(f"Errore nella conversione: {e}")
            return False
    
    def start_auto_save(self):
        """Start auto-save timer for current draft."""
        if self.current_note_state and self.current_note_state.is_draft:
            self.auto_save_timer.start()
    
    def stop_auto_save(self):
        """Stop auto-save timer."""
        self.auto_save_timer.stop()
    
    def _auto_save_draft(self):
        """Auto-save current draft (to be connected by UI)."""
        # This will be implemented by the UI layer
        pass
    
    def _invalidate_cache(self):
        """Clear the note cache."""
        self._note_cache.clear()
    
    def get_note_history(self, jira_key: str, title: str) -> List[Dict]:
        """Get git history for a note."""
        try:
            return self.git_service.get_note_history(jira_key, title)
        except Exception as e:
            logger.error(f"Error getting note history: {e}")
            return []