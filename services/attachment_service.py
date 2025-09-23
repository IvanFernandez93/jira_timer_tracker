"""
Service for managing file attachments from Jira.
Handles downloading, saving, and tracking of file attachments.
"""

import os
import hashlib
import logging
import mimetypes
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger('JiraTimeTracker')

class AttachmentService:
    """
    Service for managing file attachments from Jira.
    
    This service:
    - Downloads files from Jira attachments
    - Computes and verifies file hashes to detect changes
    - Keeps track of downloaded files
    - Manages the local storage of attachments
    """
    
    def __init__(self, db_service, jira_service, app_settings=None):
        """
        Initialize the attachment service.
        
        Args:
            db_service: Database service for persistent storage
            jira_service: Jira service for retrieving attachments
            app_settings: Application settings (optional)
        """
        self.db_service = db_service
        self.jira_service = jira_service
        self.app_settings = app_settings
        
        # Set up the attachments directory
        self._setup_attachments_dir()
        
    def _setup_attachments_dir(self):
        """Set up the directory where attachments will be stored."""
        try:
            # Determine the base attachment directory
            if self.app_settings:
                # Use the configured attachments directory if available
                attachments_dir = self.app_settings.get_setting("attachments_dir")
                if attachments_dir and os.path.isdir(attachments_dir):
                    self.attachments_dir = attachments_dir
                    return
                    
            # Fall back to default directory in AppData
            from PyQt6.QtCore import QStandardPaths
            data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            self.attachments_dir = os.path.join(data_dir, "attachments")
            
            # Create the attachments directory if it doesn't exist
            if not os.path.exists(self.attachments_dir):
                os.makedirs(self.attachments_dir, exist_ok=True)
                
            # Save the default path to settings if available
            if self.app_settings:
                self.app_settings.set_setting("attachments_dir", self.attachments_dir)
                
            logger.debug(f"Using attachments directory: {self.attachments_dir}")
        except Exception as e:
            logger.error(f"Failed to set up attachments directory: {e}")
            # Fall back to current directory/attachments
            self.attachments_dir = os.path.join(os.getcwd(), "attachments")
            if not os.path.exists(self.attachments_dir):
                os.makedirs(self.attachments_dir, exist_ok=True)
    
    def compute_file_hash(self, file_path: str) -> str:
        """
        Compute a SHA-256 hash of a file's contents.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 hash of the file as a hexadecimal string
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files efficiently
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute file hash for {file_path}: {e}")
            return ""
            
    def get_attachment_path(self, jira_key: str, attachment_id: str, file_name: str) -> str:
        """
        Get the local path where an attachment should be stored.
        
        Args:
            jira_key: The Jira issue key
            attachment_id: The Jira attachment ID
            file_name: The original file name
            
        Returns:
            The local path where the file should be stored
        """
        # Create a subdirectory for each Jira issue to organize attachments
        issue_dir = os.path.join(self.attachments_dir, jira_key)
        os.makedirs(issue_dir, exist_ok=True)
        
        # Use attachment ID in filename to ensure uniqueness
        safe_filename = self._sanitize_filename(file_name)
        return os.path.join(issue_dir, f"{attachment_id}_{safe_filename}")
        
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to ensure it's valid on the filesystem.
        
        Args:
            filename: The original file name
            
        Returns:
            A sanitized version of the filename
        """
        # Replace invalid characters with underscores
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Ensure the filename isn't too long
        if len(filename) > 240:  # Leave room for path
            name, ext = os.path.splitext(filename)
            filename = name[:240-len(ext)] + ext
            
        return filename
        
    def check_attachment_exists(self, jira_key: str, attachment_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if an attachment has already been downloaded.
        
        Args:
            jira_key: The Jira issue key
            attachment_id: The Jira attachment ID
            
        Returns:
            A tuple of (exists, attachment_info)
        """
        # Check if the attachment is in the database
        attachment_info = self.db_service.get_file_attachment(jira_key, attachment_id)
        if not attachment_info:
            return False, None
            
        # Check if the file actually exists at the recorded path
        file_path = attachment_info['file_path']
        if not os.path.isfile(file_path):
            logger.warning(f"Attachment file not found at {file_path} despite database record")
            return False, attachment_info
            
        # Update the last checked timestamp
        self.db_service.update_attachment_last_checked(jira_key, attachment_id)
        
        return True, attachment_info
        
    async def download_attachment(self, jira_key: str, attachment_info: Dict[str, Any], 
                                force_download: bool = False) -> Optional[str]:
        """
        Download an attachment from Jira.
        
        Args:
            jira_key: The Jira issue key
            attachment_info: Dictionary with attachment metadata from Jira API
            force_download: If True, download even if we already have it
            
        Returns:
            The local path to the downloaded file, or None on failure
        """
        try:
            attachment_id = attachment_info.get('id')
            filename = attachment_info.get('filename', 'unknown_file')
            file_size = attachment_info.get('size', 0)
            mime_type = attachment_info.get('mimeType')
            
            # Check if we already have this attachment
            if not force_download:
                exists, db_info = self.check_attachment_exists(jira_key, attachment_id)
                if exists:
                    logger.debug(f"Attachment {attachment_id} already downloaded at {db_info['file_path']}")
                    return db_info['file_path']
            
            # Determine where to save the file
            file_path = self.get_attachment_path(jira_key, attachment_id, filename)
            
            # Download the file from Jira
            success = await self.jira_service.download_attachment(
                attachment_id=attachment_id,
                file_path=file_path
            )
            
            if not success:
                logger.error(f"Failed to download attachment {attachment_id}")
                return None
                
            # Compute the file hash
            file_hash = self.compute_file_hash(file_path)
            
            # Check if the hash matches an existing record
            exists, db_info = self.check_attachment_exists(jira_key, attachment_id)
            if exists and db_info['file_hash'] == file_hash:
                # Hash hasn't changed, we can use the existing file
                logger.debug(f"File hash unchanged for {attachment_id}")
                return db_info['file_path']
            
            # Save/update the attachment record
            self.db_service.add_file_attachment(
                jira_key=jira_key,
                attachment_id=attachment_id,
                file_name=filename,
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type
            )
            
            logger.info(f"Successfully downloaded attachment {filename} for {jira_key}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return None
            
    def get_local_attachments(self, jira_key: str) -> List[Dict[str, Any]]:
        """
        Get all locally downloaded attachments for a Jira issue.
        
        Args:
            jira_key: The Jira issue key
            
        Returns:
            A list of attachment info dictionaries
        """
        attachments = self.db_service.get_file_attachments_by_jira_key(jira_key)
        
        # Add additional information
        for attachment in attachments:
            # Check if file exists
            file_path = attachment['file_path']
            attachment['exists'] = os.path.isfile(file_path)
            
            # Get file extension and icon information
            _, ext = os.path.splitext(file_path)
            attachment['extension'] = ext.lower()
            
            # Try to determine a friendly mime type description
            mime_type = attachment['mime_type']
            if mime_type:
                if '/' in mime_type:
                    main_type = mime_type.split('/')[0]
                    attachment['type_category'] = main_type
                else:
                    attachment['type_category'] = 'unknown'
            else:
                # Try to guess from extension
                guessed_type = mimetypes.guess_type(file_path)[0]
                if guessed_type:
                    attachment['mime_type'] = guessed_type
                    attachment['type_category'] = guessed_type.split('/')[0]
                else:
                    attachment['type_category'] = 'unknown'
                
        return attachments
        
    def delete_attachment(self, jira_key: str, attachment_id: str) -> bool:
        """
        Delete a locally downloaded attachment.
        
        Args:
            jira_key: The Jira issue key
            attachment_id: The Jira attachment ID
            
        Returns:
            True if the attachment was deleted successfully
        """
        try:
            # Get the attachment info
            attachment_info = self.db_service.get_file_attachment(jira_key, attachment_id)
            if not attachment_info:
                logger.warning(f"Attachment {attachment_id} not found in database")
                return False
                
            # Delete the file
            file_path = attachment_info['file_path']
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"Deleted attachment file: {file_path}")
            
            # Remove from database
            self.db_service.delete_file_attachment(jira_key, attachment_id)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting attachment {attachment_id}: {e}")
            return False
            
    def open_attachment(self, file_path: str) -> bool:
        """
        Open an attachment file with the system's default application.
        
        Args:
            file_path: Path to the attachment file
            
        Returns:
            True if the file was opened successfully
        """
        try:
            if not os.path.isfile(file_path):
                logger.error(f"Attachment file not found: {file_path}")
                return False
                
            # Use the appropriate method based on the OS
            import platform
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                import subprocess
                subprocess.call(['open', file_path])
            else:  # Linux and other Unix-like
                import subprocess
                subprocess.call(['xdg-open', file_path])
                
            return True
        except Exception as e:
            logger.error(f"Error opening attachment: {e}")
            return False