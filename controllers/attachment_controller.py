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
        import logging
        logger = logging.getLogger('JiraTimeTracker')
        
        # Get locally cached attachments
        local_attachments = self.attachment_service.get_local_attachments(jira_key)
        local_by_id = {a['attachment_id']: a for a in local_attachments}
        
        # Fetch remote attachments from Jira API
        remote_attachments = []
        try:
            # Get Jira issue with attachments
            issue = await self.attachment_service.jira_service.get_issue(jira_key)
            if issue and 'fields' in issue and 'attachment' in issue['fields']:
                remote_attachments = issue['fields']['attachment']
                logger.debug(f"Found {len(remote_attachments)} remote attachments for {jira_key}")
            else:
                logger.debug(f"No attachments found for issue {jira_key}")
        except Exception as e:
            logger.error(f"Error fetching remote attachments for {jira_key}: {e}")
            
        # Combine local and remote attachments, prioritizing local versions
        result = []
        
        # First add all remote attachments, marking which ones we have locally
        for attachment in remote_attachments:
            attachment_id = attachment.get('id')
            local_info = local_by_id.get(attachment_id)
            
            if local_info:
                # We have this attachment locally, use our local info
                jira_attachment = {
                    'id': attachment_id,
                    'filename': attachment.get('filename', local_info['file_name']),
                    'size': attachment.get('size', local_info['file_size']),
                    'mimeType': attachment.get('mimeType', local_info['mime_type']),
                    'author': attachment.get('author', {'displayName': 'Unknown User'}),
                    'created': attachment.get('created', local_info['downloaded_at']),
                    'is_cached': True,
                    'local_path': local_info['file_path']
                }
            else:
                # This is a remote-only attachment
                jira_attachment = {
                    'id': attachment_id,
                    'filename': attachment.get('filename', 'Unknown file'),
                    'size': attachment.get('size', 0),
                    'mimeType': attachment.get('mimeType', ''),
                    'author': attachment.get('author', {'displayName': 'Unknown User'}),
                    'created': attachment.get('created', ''),
                    'is_cached': False,
                    'local_path': None
                }
                
            result.append(jira_attachment)
            
        # Now add any local attachments that weren't in the remote list
        # (This can happen if we have old attachments that were deleted in Jira)
        remote_ids = {a.get('id') for a in remote_attachments}
        for attachment_id, attachment in local_by_id.items():
            if attachment_id not in remote_ids:
                jira_attachment = {
                    'id': attachment_id,
                    'filename': attachment['file_name'],
                    'size': attachment['file_size'],
                    'mimeType': attachment['mime_type'],
                    'author': {'displayName': 'Local User'},
                    'created': attachment['downloaded_at'],
                    'is_cached': True,
                    'local_path': attachment['file_path'],
                    'possibly_deleted': True  # Mark as potentially deleted remotely
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