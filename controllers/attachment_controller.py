"""
Controller for managing attachments in the application.
"""

import logging
from typing import Dict, List, Any, Optional

from services.attachment_service import AttachmentService
from views.attachments_dialog import AttachmentsDialog

logger = logging.getLogger('JiraTimeTracker')

class AttachmentController:
    """
    Controller for managing file attachments from Jira issues.
    
    This controller:
    - Opens the attachment dialog
    - Manages synchronization of attachments
    - Handles attachment download requests
    """
    
    def __init__(self, db_service, jira_service, app_settings=None, attachment_service=None):
        """
        Initialize the attachment controller.
        
        Args:
            db_service: Database service for persistent storage
            jira_service: Jira service for retrieving attachments
            app_settings: Application settings (optional)
            attachment_service: Existing AttachmentService instance (optional)
        """
        if attachment_service:
            self.attachment_service = attachment_service
        else:
            self.attachment_service = AttachmentService(
                db_service=db_service,
                jira_service=jira_service,
                app_settings=app_settings
            )
        
    def show_attachments_dialog(self, jira_key: str, parent=None):
        """
        Show the attachments dialog for a Jira issue.
        
        Args:
            jira_key: The Jira issue key
            parent: Parent widget
        """
        dialog = AttachmentsDialog(
            jira_key=jira_key,
            attachment_service=self.attachment_service,
            parent=parent
        )
        dialog.exec()
        
    async def get_issue_attachments(self, jira_key: str) -> List[Dict[str, Any]]:
        """
        Get attachments for a Jira issue, both from Jira and local cache.
        
        Args:
            jira_key: The Jira issue key
            
        Returns:
            List of attachment info dictionaries
        """
        # Get locally cached attachments
        local_attachments = self.attachment_service.get_local_attachments(jira_key)
        local_by_id = {a['attachment_id']: a for a in local_attachments}
        
        # TODO: Implement fetching attachments from Jira API
        # This should be done through the JiraService
        # For now, return the local attachments
        
        result = []
        for attachment_id, attachment in local_by_id.items():
            # Convert from DB format to Jira-like format
            jira_attachment = {
                'id': attachment_id,
                'filename': attachment['file_name'],
                'size': attachment['file_size'],
                'mimeType': attachment['mime_type'],
                'author': {'displayName': 'Local User'},
                'created': attachment['downloaded_at'],
                'is_cached': True,
                'local_path': attachment['file_path']
            }
            result.append(jira_attachment)
        
        return result
        
    async def download_attachment(self, jira_key: str, attachment_info: Dict[str, Any], 
                              force_download: bool = False) -> Optional[str]:
        """
        Download an attachment for a Jira issue.
        
        Args:
            jira_key: The Jira issue key
            attachment_info: Dictionary with attachment metadata from Jira API
            force_download: If True, download even if we already have it
            
        Returns:
            The local path to the downloaded file, or None on failure
        """
        return await self.attachment_service.download_attachment(
            jira_key=jira_key,
            attachment_info=attachment_info,
            force_download=force_download
        )
        
    def open_attachment(self, file_path: str) -> bool:
        """
        Open an attachment with the system's default application.
        
        Args:
            file_path: Path to the attachment file
            
        Returns:
            True if the file was opened successfully
        """
        return self.attachment_service.open_attachment(file_path)
        
    def get_attachments_count(self, jira_key: str) -> int:
        """
        Get the count of locally cached attachments for a Jira issue.
        
        Args:
            jira_key: The Jira issue key
            
        Returns:
            Count of locally cached attachments
        """
        return len(self.attachment_service.get_local_attachments(jira_key))