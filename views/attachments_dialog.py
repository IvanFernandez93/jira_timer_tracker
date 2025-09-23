"""
Dialog for viewing and managing attachments for a Jira issue.
"""

import os
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem,
    QWidget, QFileDialog, QMessageBox,
    QMenu, QCheckBox, QProgressBar
)
from PyQt6.QtGui import QIcon, QPixmap, QAction, QCursor
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject

from services.attachment_service import AttachmentService
from qfluentwidgets import FluentIcon

class DownloadWorker(QObject):
    """Worker thread for downloading attachments."""
    
    progress = pyqtSignal(int, int)  # (current_index, total_count)
    download_complete = pyqtSignal(str, bool)  # (attachment_id, success)
    all_downloads_complete = pyqtSignal()
    
    def __init__(self, attachment_service, jira_key, attachments):
        """
        Initialize the worker.
        
        Args:
            attachment_service: The attachment service to use for downloading
            jira_key: The Jira issue key
            attachments: List of attachment info dictionaries from Jira API
        """
        super().__init__()
        self.attachment_service = attachment_service
        self.jira_key = jira_key
        self.attachments = attachments
        self.should_stop = False
        
    async def download(self):
        """Download all attachments."""
        total = len(self.attachments)
        
        for i, attachment in enumerate(self.attachments):
            if self.should_stop:
                break
                
            self.progress.emit(i + 1, total)
            
            try:
                attachment_id = attachment.get('id')
                
                if not attachment_id:
                    self.download_complete.emit("unknown", False)
                    continue
                
                file_path = await self.attachment_service.download_attachment(
                    self.jira_key, 
                    attachment
                )
                
                success = file_path is not None
                self.download_complete.emit(attachment_id, success)
                
            except Exception as e:
                print(f"Error downloading attachment: {e}")
                self.download_complete.emit(
                    attachment.get('id', "unknown"), 
                    False
                )
                
        self.all_downloads_complete.emit()
        
    def stop(self):
        """Stop the download process."""
        self.should_stop = True


class AttachmentItem(QWidget):
    """Custom widget for displaying an attachment in the list."""
    
    def __init__(self, attachment: Dict[str, Any], parent=None):
        """
        Initialize the attachment item.
        
        Args:
            attachment: Dictionary with attachment metadata
            parent: Parent widget
        """
        super().__init__(parent)
        self.attachment = attachment
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the item UI."""
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # File icon based on type
        icon_label = QLabel()
        icon = self.get_icon_for_attachment()
        if icon:
            pixmap = icon.pixmap(QSize(24, 24))
            icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        
        # Filename
        filename_label = QLabel(self.attachment.get('filename', 'Unknown file'))
        filename_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(filename_label)
        
        # File details
        details = []
        
        # Size
        file_size = self.attachment.get('size', 0)
        if file_size:
            size_str = self.format_size(file_size)
            details.append(size_str)
            
        # Mime type
        mime_type = self.attachment.get('mime_type', '')
        if mime_type:
            details.append(mime_type)
            
        # Author and date
        author = self.attachment.get('author', {}).get('displayName', '')
        date = self.attachment.get('created', '')
        if author and date:
            details.append(f"{author} on {date[:10]}")
        
        details_label = QLabel(' | '.join(details))
        details_label.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(details_label)
        
        # Add a status label for download/cached status
        self.status_label = QLabel()
        self.update_status()
        self.status_label.setStyleSheet("color: green; font-size: 10px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Download button
        self.download_btn = QPushButton()
        self.download_btn.setIcon(FluentIcon.DOWNLOAD)
        self.download_btn.setToolTip("Download attachment")
        self.download_btn.setFixedSize(32, 32)
        layout.addWidget(self.download_btn)
        
        # Set a minimum height for the item
        self.setMinimumHeight(60)
        
    def get_icon_for_attachment(self) -> Optional[QIcon]:
        """
        Get an appropriate icon based on the file type.
        
        Returns:
            A QIcon for the attachment type or None
        """
        mime_type = self.attachment.get('mimeType', '')
        filename = self.attachment.get('filename', '')
        
        # Determine icon based on mime type or extension
        icon_name = 'document'  # Default
        
        if mime_type.startswith('image/'):
            icon_name = 'image'
        elif mime_type.startswith('video/'):
            icon_name = 'video'
        elif mime_type.startswith('audio/'):
            icon_name = 'audio'
        elif mime_type == 'application/pdf':
            icon_name = 'pdf'
        elif mime_type.startswith('text/'):
            icon_name = 'text'
        elif any(ext in filename.lower() for ext in ['.doc', '.docx']):
            icon_name = 'word'
        elif any(ext in filename.lower() for ext in ['.xls', '.xlsx']):
            icon_name = 'excel'
        elif any(ext in filename.lower() for ext in ['.ppt', '.pptx']):
            icon_name = 'powerpoint'
        elif any(ext in filename.lower() for ext in ['.zip', '.rar', '.7z', '.tar', '.gz']):
            icon_name = 'archive'
        
        # Return the corresponding FluentIcon
        if hasattr(FluentIcon, icon_name.upper()):
            return getattr(FluentIcon, icon_name.upper())
        else:
            return FluentIcon.DOCUMENT
            
    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Human-readable size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
    def update_status(self, is_downloaded: bool = False):
        """
        Update the status label.
        
        Args:
            is_downloaded: Whether the file has been downloaded
        """
        if is_downloaded:
            self.status_label.setText("Downloaded")
            self.status_label.setStyleSheet("color: green; font-size: 10px;")
        else:
            self.status_label.setText("Not downloaded")
            self.status_label.setStyleSheet("color: gray; font-size: 10px;")
            
    def set_download_in_progress(self, in_progress: bool = True):
        """
        Show download in progress state.
        
        Args:
            in_progress: Whether download is in progress
        """
        if in_progress:
            self.download_btn.setEnabled(False)
            self.status_label.setText("Downloading...")
            self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        else:
            self.download_btn.setEnabled(True)


class AttachmentsDialog(QDialog):
    """Dialog for managing attachments of a Jira issue."""
    
    def __init__(self, jira_key: str, attachment_service: AttachmentService, parent=None):
        """
        Initialize the attachments dialog.
        
        Args:
            jira_key: The Jira issue key
            attachment_service: The attachment service to use
            parent: Parent widget
        """
        super().__init__(parent)
        self.jira_key = jira_key
        self.attachment_service = attachment_service
        self.attachments = []
        self.local_attachments = {}
        self.download_worker = None
        self.download_thread = None
        
        self.setup_ui()
        self.setWindowTitle(f"Attachments for {jira_key}")
        self.resize(600, 400)
        
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Issue key and title
        header_layout = QHBoxLayout()
        issue_label = QLabel(f"<b>Attachments for {self.jira_key}</b>")
        header_layout.addWidget(issue_label, stretch=1)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(FluentIcon.SYNC)
        refresh_btn.clicked.connect(self.refresh_attachments)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar for downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Attachments list
        self.attachments_list = QListWidget()
        self.attachments_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.attachments_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.attachments_list)
        
        # Only cached checkbox
        self.cached_only_checkbox = QCheckBox("Show only cached attachments")
        self.cached_only_checkbox.stateChanged.connect(self.filter_attachments)
        layout.addWidget(self.cached_only_checkbox)
        
        # Download all and Close buttons
        button_layout = QHBoxLayout()
        
        self.download_all_btn = QPushButton("Download All")
        self.download_all_btn.setIcon(FluentIcon.DOWNLOAD)
        self.download_all_btn.clicked.connect(self.download_all_attachments)
        button_layout.addWidget(self.download_all_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Initial load of attachments
        self.refresh_attachments()
        
    def refresh_attachments(self):
        """Refresh the list of attachments from Jira and local cache."""
        # Load local attachments first
        self.local_attachments = {}
        local_attachments_list = self.attachment_service.get_local_attachments(self.jira_key)
        
        for attachment in local_attachments_list:
            self.local_attachments[attachment['attachment_id']] = attachment
            
        # Now get attachments from Jira
        # This should be done in a background thread, but for simplicity we'll assume
        # the JiraService method is already async or has been wrapped in a worker
        
        # For now, let's use a placeholder method
        self.load_attachments_from_jira()
        
    def load_attachments_from_jira(self):
        """
        Load attachments from Jira. This is a placeholder.
        In a real implementation, this would call JiraService to get attachments.
        """
        # TODO: Replace with actual call to JiraService
        # For now, we'll just display local attachments
        self.attachments = []
        
        for attachment_id, attachment in self.local_attachments.items():
            # Convert from DB format to Jira-like format
            jira_attachment = {
                'id': attachment_id,
                'filename': attachment['file_name'],
                'size': attachment['file_size'],
                'mimeType': attachment['mime_type'],
                'author': {'displayName': 'Local User'},
                'created': attachment['downloaded_at'],
                'is_cached': True
            }
            self.attachments.append(jira_attachment)
            
        self.update_attachments_list()
        
    def update_attachments_list(self):
        """Update the attachments list widget with current attachments."""
        self.attachments_list.clear()
        
        filtered_attachments = self.get_filtered_attachments()
        
        for attachment in filtered_attachments:
            item = QListWidgetItem()
            attachment_widget = AttachmentItem(attachment)
            
            # Configure the download button
            is_cached = attachment.get('is_cached', False)
            if is_cached:
                attachment_widget.update_status(True)
                attachment_widget.download_btn.setIcon(FluentIcon.OPEN)
                attachment_widget.download_btn.setToolTip("Open attachment")
                attachment_widget.download_btn.clicked.connect(
                    lambda checked=False, a=attachment: self.open_attachment(a)
                )
            else:
                attachment_widget.download_btn.clicked.connect(
                    lambda checked=False, a=attachment: self.download_attachment(a)
                )
            
            # Set item size
            item.setSizeHint(attachment_widget.sizeHint())
            
            # Add to list
            self.attachments_list.addItem(item)
            self.attachments_list.setItemWidget(item, attachment_widget)
            
    def get_filtered_attachments(self) -> List[Dict[str, Any]]:
        """
        Get a filtered list of attachments based on current filter settings.
        
        Returns:
            Filtered list of attachments
        """
        if self.cached_only_checkbox.isChecked():
            return [a for a in self.attachments if a.get('is_cached', False)]
        else:
            return self.attachments
            
    def filter_attachments(self):
        """Apply current filter settings to the attachments list."""
        self.update_attachments_list()
        
    def download_attachment(self, attachment):
        """
        Download a single attachment.
        
        Args:
            attachment: The attachment to download
        """
        attachment_id = attachment.get('id')
        if not attachment_id:
            QMessageBox.warning(self, "Error", "Invalid attachment information")
            return
            
        # Find the list item for this attachment
        for i in range(self.attachments_list.count()):
            item = self.attachments_list.item(i)
            widget = self.attachments_list.itemWidget(item)
            if widget.attachment.get('id') == attachment_id:
                widget.set_download_in_progress()
                break
                
        # Start download in a worker thread
        attachments = [attachment]
        self.start_download_worker(attachments)
        
    async def open_attachment(self, attachment):
        """
        Open a downloaded attachment.
        
        Args:
            attachment: The attachment to open
        """
        attachment_id = attachment.get('id')
        if not attachment_id or attachment_id not in self.local_attachments:
            QMessageBox.warning(self, "Error", "Attachment not found locally")
            return
            
        file_path = self.local_attachments[attachment_id]['file_path']
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Error", f"File not found at {file_path}")
            return
            
        success = self.attachment_service.open_attachment(file_path)
        if not success:
            QMessageBox.warning(self, "Error", "Failed to open attachment")
            
    def download_all_attachments(self):
        """Download all attachments for the issue."""
        # Get non-cached attachments
        to_download = [a for a in self.attachments if not a.get('is_cached', False)]
        
        if not to_download:
            QMessageBox.information(self, "Info", "All attachments are already downloaded")
            return
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(to_download))
        
        # Update UI for all attachments being downloaded
        for i in range(self.attachments_list.count()):
            item = self.attachments_list.item(i)
            widget = self.attachments_list.itemWidget(item)
            attachment_id = widget.attachment.get('id')
            
            if attachment_id and not widget.attachment.get('is_cached', False):
                widget.set_download_in_progress()
                
        # Start download worker
        self.start_download_worker(to_download)
        
    def start_download_worker(self, attachments_to_download):
        """
        Start a worker thread for downloading attachments.
        
        Args:
            attachments_to_download: List of attachments to download
        """
        # Stop any existing worker
        if self.download_worker:
            self.download_worker.stop()
            
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait()
            
        # Create new worker and thread
        self.download_worker = DownloadWorker(
            self.attachment_service,
            self.jira_key,
            attachments_to_download
        )
        
        self.download_thread = QThread()
        self.download_worker.moveToThread(self.download_thread)
        
        # Connect signals
        self.download_worker.progress.connect(self.update_download_progress)
        self.download_worker.download_complete.connect(self.on_download_complete)
        self.download_worker.all_downloads_complete.connect(self.on_all_downloads_complete)
        
        self.download_thread.started.connect(self.download_worker.download)
        self.download_thread.finished.connect(self.on_download_thread_finished)
        
        # Start the thread
        self.download_thread.start()
        
        # Disable buttons during download
        self.download_all_btn.setEnabled(False)
        
    def update_download_progress(self, current, total):
        """
        Update the download progress bar.
        
        Args:
            current: Current download index
            total: Total number of downloads
        """
        self.progress_bar.setValue(current)
        
    def on_download_complete(self, attachment_id, success):
        """
        Handle completion of a single download.
        
        Args:
            attachment_id: ID of the downloaded attachment
            success: Whether the download succeeded
        """
        # Find the attachment item and update its status
        for i in range(self.attachments_list.count()):
            item = self.attachments_list.item(i)
            widget = self.attachments_list.itemWidget(item)
            if widget.attachment.get('id') == attachment_id:
                widget.set_download_in_progress(False)
                widget.update_status(success)
                
                if success:
                    widget.download_btn.setIcon(FluentIcon.OPEN)
                    widget.download_btn.setToolTip("Open attachment")
                    widget.download_btn.clicked.disconnect()
                    widget.download_btn.clicked.connect(
                        lambda checked=False, a=widget.attachment: self.open_attachment(a)
                    )
                break
                
    def on_all_downloads_complete(self):
        """Handle completion of all downloads."""
        # Re-enable buttons
        self.download_all_btn.setEnabled(True)
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Refresh attachments list to update cached status
        self.refresh_attachments()
        
    def on_download_thread_finished(self):
        """Handle download thread finishing."""
        self.download_thread = None
        self.download_worker = None
        
    def show_context_menu(self, position):
        """
        Show context menu for attachment items.
        
        Args:
            position: Position where to show the menu
        """
        item = self.attachments_list.itemAt(position)
        if not item:
            return
            
        attachment_widget = self.attachments_list.itemWidget(item)
        if not attachment_widget:
            return
            
        attachment = attachment_widget.attachment
        attachment_id = attachment.get('id')
        is_cached = attachment.get('is_cached', False)
        
        menu = QMenu()
        
        if is_cached and attachment_id in self.local_attachments:
            # Actions for cached attachments
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_attachment(attachment))
            menu.addAction(open_action)
            
            file_path = self.local_attachments[attachment_id]['file_path']
            if os.path.isfile(file_path):
                open_folder_action = QAction("Show in folder", self)
                open_folder_action.triggered.connect(
                    lambda: self.show_in_folder(file_path)
                )
                menu.addAction(open_folder_action)
                
            redownload_action = QAction("Download again", self)
            redownload_action.triggered.connect(
                lambda: self.download_attachment(attachment)
            )
            menu.addAction(redownload_action)
            
            menu.addSeparator()
            
            delete_action = QAction("Delete local copy", self)
            delete_action.triggered.connect(
                lambda: self.delete_attachment(attachment_id)
            )
            menu.addAction(delete_action)
        else:
            # Actions for non-cached attachments
            download_action = QAction("Download", self)
            download_action.triggered.connect(
                lambda: self.download_attachment(attachment)
            )
            menu.addAction(download_action)
            
        # Show the menu
        menu.exec(QCursor.pos())
        
    def show_in_folder(self, file_path):
        """
        Show a file in its containing folder.
        
        Args:
            file_path: Path to the file
        """
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return
            
        # Open file explorer and select the file
        import platform
        system = platform.system()
        
        try:
            if system == 'Windows':
                import subprocess
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            elif system == 'Darwin':  # macOS
                import subprocess
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                import subprocess
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open folder: {e}")
            
    def delete_attachment(self, attachment_id):
        """
        Delete a locally cached attachment.
        
        Args:
            attachment_id: ID of the attachment to delete
        """
        if attachment_id not in self.local_attachments:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this local attachment copy?\n"
            "You can download it again from Jira if needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Delete the attachment
        success = self.attachment_service.delete_attachment(
            self.jira_key,
            attachment_id
        )
        
        if success:
            # Refresh attachments list
            self.refresh_attachments()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete attachment")
            
    def closeEvent(self, event):
        """
        Handle dialog close event.
        
        Args:
            event: Close event
        """
        # Stop any running download worker
        if self.download_worker:
            self.download_worker.stop()
            
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait()
            
        super().closeEvent(event)