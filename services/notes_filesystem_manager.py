"""
File System Manager per la gestione delle cartelle delle note basate sulle chiavi JIRA.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)

class NotesFileSystemManager:
    """Gestore del file system per le note organizzate per chiave JIRA."""
    
    def __init__(self, base_notes_path: Optional[str] = None):
        """
        Initialize the notes file system manager.
        
        Args:
            base_notes_path: Base path for notes. If None, uses user's Documents/JiraTrackerNotes
        """
        if base_notes_path is None:
            documents_path = Path.home() / "Documents"
            self.base_path = documents_path / "JiraTrackerNotes"
        else:
            self.base_path = Path(base_notes_path)
        
        # Crea la directory base se non esiste
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Notes file system initialized at: {self.base_path}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename removing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for file system
        """
        # Remove invalid characters for Windows/Linux file systems
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_.')
        
        # Ensure it's not empty and not too long
        if not sanitized:
            sanitized = "untitled"
        
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def get_jira_folder_path(self, jira_key: str) -> Path:
        """
        Get the folder path for a specific JIRA key.
        
        Args:
            jira_key: JIRA issue key (e.g., "PROJECT-123")
            
        Returns:
            Path to the JIRA folder
        """
        sanitized_key = self._sanitize_filename(jira_key)
        return self.base_path / sanitized_key
    
    def get_note_file_path(self, jira_key: str, note_title: str, note_id: Optional[int] = None) -> Path:
        """
        Get the full file path for a note.
        
        Args:
            jira_key: JIRA issue key
            note_title: Title of the note
            note_id: Optional note ID for uniqueness
            
        Returns:
            Full path to the note markdown file
        """
        jira_folder = self.get_jira_folder_path(jira_key)
        
        # Sanitize title for filename
        sanitized_title = self._sanitize_filename(note_title)
        
        # Add note ID if provided for uniqueness
        if note_id:
            filename = f"{sanitized_title}_id{note_id}.md"
        else:
            filename = f"{sanitized_title}.md"
        
        return jira_folder / filename
    
    def ensure_jira_folder_exists(self, jira_key: str) -> Path:
        """
        Ensure the JIRA folder exists, create if necessary.
        
        Args:
            jira_key: JIRA issue key
            
        Returns:
            Path to the created/existing JIRA folder
        """
        jira_folder = self.get_jira_folder_path(jira_key)
        jira_folder.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Ensured JIRA folder exists: {jira_folder}")
        return jira_folder
    
    def save_note_to_file(self, jira_key: str, note_title: str, content: str, 
                         note_id: Optional[int] = None, tags: str = "", 
                         is_fictitious: bool = False) -> Tuple[bool, str, Path]:
        """
        Save note content to markdown file in appropriate JIRA folder.
        
        Args:
            jira_key: JIRA issue key  
            note_title: Title of the note
            content: Markdown content of the note
            note_id: Optional note ID
            tags: Tags for the note
            is_fictitious: Whether the note is fictitious
            
        Returns:
            Tuple of (success: bool, message: str, file_path: Path)
        """
        try:
            # Ensure JIRA folder exists
            jira_folder = self.ensure_jira_folder_exists(jira_key)
            
            # Get note file path
            note_file_path = self.get_note_file_path(jira_key, note_title, note_id)
            
            # Prepare markdown content with metadata
            markdown_content = self._prepare_markdown_content(
                title=note_title,
                jira_key=jira_key,
                content=content,
                tags=tags,
                is_fictitious=is_fictitious,
                note_id=note_id
            )
            
            # Write to file
            with open(note_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Note saved to file: {note_file_path}")
            return True, f"Nota salvata in: {note_file_path}", note_file_path
            
        except Exception as e:
            error_msg = f"Errore nel salvataggio del file: {e}"
            logger.error(error_msg)
            return False, error_msg, Path()
    
    def _prepare_markdown_content(self, title: str, jira_key: str, content: str, 
                                tags: str = "", is_fictitious: bool = False, 
                                note_id: Optional[int] = None) -> str:
        """
        Prepare markdown content with metadata header.
        
        Args:
            title: Note title
            jira_key: JIRA key
            content: Note content
            tags: Tags
            is_fictitious: Fictitious flag
            note_id: Note ID
            
        Returns:
            Formatted markdown content with metadata
        """
        from datetime import datetime
        
        # YAML front matter with metadata
        metadata_lines = [
            "---",
            f"title: {title}",
            f"jira_key: {jira_key}",
            f"created: {datetime.now().isoformat()}",
            f"updated: {datetime.now().isoformat()}"
        ]
        
        if note_id:
            metadata_lines.append(f"note_id: {note_id}")
        
        if tags:
            metadata_lines.append(f"tags: {tags}")
        
        if is_fictitious:
            metadata_lines.append(f"fictitious: true")
        
        metadata_lines.append("---")
        metadata_lines.append("")  # Empty line after metadata
        
        # Combine metadata and content
        full_content = "\n".join(metadata_lines) + content
        
        return full_content
    
    def read_note_from_file(self, file_path: Path) -> Tuple[bool, dict]:
        """
        Read note content from markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Tuple of (success: bool, note_data: dict)
        """
        try:
            if not file_path.exists():
                return False, {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML front matter if present
            note_data = self._parse_markdown_metadata(content)
            
            logger.debug(f"Note read from file: {file_path}")
            return True, note_data
            
        except Exception as e:
            logger.error(f"Error reading note from file {file_path}: {e}")
            return False, {}
    
    def _parse_markdown_metadata(self, content: str) -> dict:
        """
        Parse YAML front matter from markdown content.
        
        Args:
            content: Full markdown content
            
        Returns:
            Dictionary with parsed metadata and content
        """
        # Check if content starts with YAML front matter
        if content.startswith('---'):
            try:
                # Split front matter and content
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    markdown_content = parts[2].strip()
                    
                    # Parse YAML manually (simple key: value format)
                    metadata = self._parse_simple_yaml(yaml_content)
                    metadata['content'] = markdown_content
                    
                    return metadata
            except Exception as e:
                logger.warning(f"Error parsing YAML front matter: {e}")
        
        # If no valid YAML front matter, return content only
        return {'content': content}
    
    def _parse_simple_yaml(self, yaml_content: str) -> dict:
        """
        Simple YAML parser for basic key: value pairs.
        
        Args:
            yaml_content: YAML content string
            
        Returns:
            Dictionary with parsed key-value pairs
        """
        metadata = {}
        
        for line in yaml_content.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Convert common types
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                
                metadata[key] = value
        
        return metadata
    
    def list_jira_folders(self) -> list:
        """
        List all JIRA folders in the base directory.
        
        Returns:
            List of JIRA folder names (keys)
        """
        try:
            folders = []
            for item in self.base_path.iterdir():
                if item.is_dir():
                    folders.append(item.name)
            
            return sorted(folders)
            
        except Exception as e:
            logger.error(f"Error listing JIRA folders: {e}")
            return []
    
    def list_notes_for_jira(self, jira_key: str) -> list:
        """
        List all note files for a specific JIRA key.
        
        Args:
            jira_key: JIRA issue key
            
        Returns:
            List of note file paths
        """
        try:
            jira_folder = self.get_jira_folder_path(jira_key)
            
            if not jira_folder.exists():
                return []
            
            note_files = []
            for file_path in jira_folder.iterdir():
                if file_path.is_file() and file_path.suffix == '.md':
                    note_files.append(file_path)
            
            return sorted(note_files)
            
        except Exception as e:
            logger.error(f"Error listing notes for JIRA {jira_key}: {e}")
            return []