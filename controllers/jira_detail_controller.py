from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QDateTime, QUrl, Qt, QThread, pyqtSlot
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QListWidgetItem, QTextEdit, QInputDialog, QLabel
from PyQt6.QtGui import QDesktopServices, QPixmap
import json
import math
from datetime import datetime
import os
import requests
import markdown
import webbrowser

from services.jira_service import JiraService
from views.markdown_editor import MarkdownEditor
import logging

_logger = logging.getLogger('JiraTimeTracker')

class AttachmentDownloadWorker(QThread):
    """Worker thread for downloading attachments asynchronously."""
    
    progress_updated = pyqtSignal(object, int)  # attachment_widget, progress_percentage
    download_finished = pyqtSignal(object, str)  # attachment_widget, file_path
    download_error = pyqtSignal(object, str)     # attachment_widget, error_message
    
    def __init__(self, jira_service, attachment_data, attachment_widget):
        super().__init__()
        self.jira_service = jira_service
        self.attachment_data = attachment_data
        self.attachment_widget = attachment_widget
        self.is_cancelled = False
        self.setObjectName(f"AttachmentDownload-{attachment_data.get('filename', 'unknown')}")
    
    def cancel(self):
        """Cancel the download."""
        self.is_cancelled = True
    
    def run(self):
        """Download the attachment."""
        try:
            if self.is_cancelled:
                return
                
            filename = self.attachment_data.get('filename')
            attachment_id = self.attachment_data.get('id')
            
            if not attachment_id:
                self.download_error.emit(self.attachment_widget, "ID allegato mancante")
                return
            
            # Update status to downloading
            self.progress_updated.emit(self.attachment_widget, 0)
            
            # Determine save path
            from PyQt6.QtCore import QStandardPaths
            download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            save_path = os.path.join(download_dir, filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Use the direct Jira API to download the attachment
            import asyncio
            success = asyncio.run(self.jira_service.download_attachment(attachment_id, save_path))
            
            if not success:
                self.download_error.emit(self.attachment_widget, "Download fallito")
                return
                
            # Report 100% progress
            self.progress_updated.emit(self.attachment_widget, 100)
            
            self.download_finished.emit(self.attachment_widget, save_path)
            
        except Exception as e:
            if not self.is_cancelled:
                self.download_error.emit(self.attachment_widget, str(e))


class ThumbnailDownloadWorker(QThread):
    """Worker thread for downloading and creating image thumbnails."""
    
    thumbnail_ready = pyqtSignal(object, object)  # attachment_widget, QPixmap
    thumbnail_error = pyqtSignal(object, str)     # attachment_widget, error_message
    
    def __init__(self, jira_service, attachment_data, attachment_widget):
        super().__init__()
        self.jira_service = jira_service
        self.attachment_data = attachment_data
        self.attachment_widget = attachment_widget
        self.is_cancelled = False
        self.setObjectName(f"ThumbnailDownload-{attachment_data.get('filename', 'unknown')}")
    
    def cancel(self):
        """Cancel the thumbnail download."""
        self.is_cancelled = True
    
    def run(self):
        """Download image and create thumbnail."""
        try:
            if self.is_cancelled:
                return
                
            filename = self.attachment_data.get('filename')
            attachment_id = self.attachment_data.get('id')
            
            if not attachment_id:
                self.thumbnail_error.emit(self.attachment_widget, "ID allegato mancante")
                return
            
            # Create a temporary file to download the image
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                temp_path = tmp_file.name
            
            # Download the image using Jira API
            import asyncio
            success = asyncio.run(self.jira_service.download_attachment(attachment_id, temp_path))
            
            if not success:
                self.thumbnail_error.emit(self.attachment_widget, "Download thumbnail fallito")
                try:
                    os.unlink(temp_path)
                except:
                    pass
                return
                
            if self.is_cancelled:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                return
            
            # Create QPixmap from the temporary file
            from PyQt6.QtGui import QPixmap
            
            pixmap = QPixmap()
            if pixmap.load(temp_path):
                # Scale to thumbnail size (64x64) maintaining aspect ratio
                thumbnail = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
                self.thumbnail_ready.emit(self.attachment_widget, thumbnail)
            else:
                self.thumbnail_error.emit(self.attachment_widget, "Impossibile caricare l'immagine")
                
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
            
        except Exception as e:
            if not self.is_cancelled:
                self.thumbnail_error.emit(self.attachment_widget, str(e))


class IssueLinksLoaderWorker(QThread):
    """Worker thread for loading issue links asynchronously."""
    
    links_loaded = pyqtSignal(list)  # List of link dictionaries
    links_error = pyqtSignal(str)    # Error message
    
    def __init__(self, jira_service, issue_key):
        super().__init__()
        self.jira_service = jira_service
        self.issue_key = issue_key
        self.is_cancelled = False
        self.setObjectName(f"IssueLinksLoader-{issue_key}")
    
    def cancel(self):
        """Cancel the links loading."""
        self.is_cancelled = True
    
    def run(self):
        """Load issue links and build the links tree."""
        try:
            if self.is_cancelled:
                return
            
            # Get the issue data with expanded issuelinks
            issue_data = self.jira_service.get_issue(self.issue_key)
            
            if self.is_cancelled:
                return
            
            if not issue_data:
                self.links_error.emit("Impossibile caricare i dati dell'issue")
                return
            
            # Extract issue links
            links = issue_data.get('fields', {}).get('issuelinks', [])
            
            # Build the links tree structure
            links_tree = self._build_links_tree(links, issue_data)
            
            if not self.is_cancelled:
                self.links_loaded.emit(links_tree)
            
        except Exception as e:
            if not self.is_cancelled:
                self.links_error.emit(str(e))
    
    def _build_links_tree(self, links, current_issue_data):
        """Build a hierarchical tree structure of issue links."""
        tree_data = []
        
        # Add current issue as root
        current_key = current_issue_data.get('key', 'Unknown')
        current_summary = current_issue_data.get('fields', {}).get('summary', 'No summary')
        current_status = current_issue_data.get('fields', {}).get('status', {}).get('name', 'Unknown')
        
        root_item = {
            'key': current_key,
            'summary': current_summary,
            'status': current_status,
            'type': 'current',
            'children': []
        }
        
        # Process each link
        for link in links:
            if self.is_cancelled:
                return []
                
            link_type = link.get('type', {}).get('name', 'Link')
            outward_issue = link.get('outwardIssue')
            inward_issue = link.get('inwardIssue')
            
            if outward_issue:
                # This issue links TO another issue
                linked_key = outward_issue.get('key', 'Unknown')
                linked_summary = outward_issue.get('fields', {}).get('summary', 'No summary')
                linked_status = outward_issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                
                link_item = {
                    'key': linked_key,
                    'summary': linked_summary,
                    'status': linked_status,
                    'link_type': link_type,
                    'direction': 'outward',
                    'children': []
                }
                
                # Try to load children links for this linked issue
                try:
                    if not self.is_cancelled:
                        child_links = self._load_child_links(linked_key)
                        link_item['children'] = child_links
                except Exception:
                    # If we can't load children, just continue without them
                    pass
                
                root_item['children'].append(link_item)
                
            elif inward_issue:
                # Another issue links TO this issue
                linked_key = inward_issue.get('key', 'Unknown')
                linked_summary = inward_issue.get('fields', {}).get('summary', 'No summary')
                linked_status = inward_issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                
                link_item = {
                    'key': linked_key,
                    'summary': linked_summary,
                    'status': linked_status,
                    'link_type': link_type,
                    'direction': 'inward',
                    'children': []
                }
                
                # Try to load children links for this linked issue
                try:
                    if not self.is_cancelled:
                        child_links = self._load_child_links(linked_key)
                        link_item['children'] = child_links
                except Exception:
                    # If we can't load children, just continue without them
                    pass
                
                root_item['children'].append(link_item)
        
        tree_data.append(root_item)
        return tree_data
    
    def _load_child_links(self, issue_key):
        """Load links for a child issue (limited depth to avoid infinite recursion)."""
        try:
            if self.is_cancelled:
                return []
                
            # Get issue data for the child
            child_issue_data = self.jira_service.get_issue(issue_key)
            
            if not child_issue_data or self.is_cancelled:
                return []
            
            # Get only direct links (no recursion to avoid performance issues)
            child_links = child_issue_data.get('fields', {}).get('issuelinks', [])
            
            children = []
            for link in child_links[:3]:  # Limit to 3 children per issue for performance
                if self.is_cancelled:
                    return []
                    
                link_type = link.get('type', {}).get('name', 'Link')
                outward_issue = link.get('outwardIssue')
                inward_issue = link.get('inwardIssue')
                
                if outward_issue and outward_issue.get('key') != self.issue_key:
                    child_key = outward_issue.get('key', 'Unknown')
                    child_summary = outward_issue.get('fields', {}).get('summary', 'No summary')
                    child_status = outward_issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                    
                    children.append({
                        'key': child_key,
                        'summary': child_summary,
                        'status': child_status,
                        'link_type': link_type,
                        'direction': 'child',
                        'children': []  # No further recursion
                    })
                    
                elif inward_issue and inward_issue.get('key') != self.issue_key:
                    child_key = inward_issue.get('key', 'Unknown')
                    child_summary = inward_issue.get('fields', {}).get('summary', 'No summary')
                    child_status = inward_issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                    
                    children.append({
                        'key': child_key,
                        'summary': child_summary,
                        'status': child_status,
                        'link_type': link_type,
                        'direction': 'child',
                        'children': []  # No further recursion
                    })
            
            return children
            
        except Exception:
            # Return empty list on any error
            return []


class IssueDetailLoaderWorker(QThread):
    """Worker thread for loading issue details asynchronously."""
    
    issue_loaded = pyqtSignal(dict)  # Issue data dictionary
    issue_error = pyqtSignal(str)    # Error message
    
    def __init__(self, jira_service, issue_key):
        super().__init__()
        self.jira_service = jira_service
        self.issue_key = issue_key
        self.is_cancelled = False
        self.setObjectName(f"IssueDetailLoader-{issue_key}")
    
    def cancel(self):
        """Cancel the issue loading."""
        self.is_cancelled = True
    
    def run(self):
        """Load issue details."""
        try:
            if self.is_cancelled:
                return
            
            # Load issue data from Jira
            issue_data = self.jira_service.get_issue(self.issue_key)
            
            if self.is_cancelled:
                return
            
            if issue_data is None:
                self.issue_error.emit(f"Failed to load issue data for {self.issue_key}")
                return
            
            if not self.is_cancelled:
                self.issue_loaded.emit(issue_data)
            
        except Exception as e:
            if not self.is_cancelled:
                self.issue_error.emit(str(e))


class JiraDetailController(QObject):
    """
    Controller to manage the logic for the JiraDetailView.
    """
    timer_started = pyqtSignal(str) # Emits the jira_key when a timer starts
    timer_stopped = pyqtSignal(str) # Emits the jira_key when a timer stops
    time_updated = pyqtSignal(str, int) # Emits the jira_key and seconds when time changes
    window_closed = pyqtSignal(str) # Emits the jira_key when the window is closed

    def __init__(self, view, jira_service, db_service, jira_key):
        super().__init__()
        self.view = view
        self.jira_service = jira_service
        self.db_service = db_service
        self.jira_key = jira_key
        self.priority_controller = None

        self._issue_data = None
        self._attachments_data = []
        self._attachment_widgets = []
        self._download_workers = []
        self._thumbnail_workers = []
        self._links_loader_worker = None
        self._issue_detail_loader_worker = None
        self._active_note_editor = None
        self._current_note_title = None # Track the title of the active note
        
        # Queues for pending downloads
        self._pending_thumbnail_widgets = []
        self._pending_download_widgets = []
        self._max_concurrent_downloads = 3
        
        self._connect_signals()
        self._setup_autosave_timer()  # Setup the timer once

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_display)
        self.timer.setInterval(1000)  # 1 second

        self.is_running = False
        self.total_seconds_tracked = self.db_service.get_local_time(self.jira_key)
        self._update_display()  # Show initial time

    def _connect_signals(self):
        self.view.start_pause_btn.clicked.connect(self._toggle_timer)
        self.view.stop_btn.clicked.connect(self._stop_timer)
        self.view.add_time_btn.clicked.connect(self._add_time_manually)
        
        # Open in Jira button
        self.view.open_jira_btn.clicked.connect(self._open_jira_in_browser)
        
        # Notification button
        self.view.notification_btn.clicked.connect(self._toggle_notification_subscription)
        
        # Priority controls
        self.view.priority_combo.currentIndexChanged.connect(self._update_issue_priority)
        self.view.priority_config_btn.clicked.connect(self._show_priority_config)
        
        # Comment signals
        self.view.add_comment_btn.clicked.connect(self._add_comment)

        # Attachment signals
        self.view.upload_attachment_btn.clicked.connect(self._upload_attachment)
        self.view.download_selected_btn.clicked.connect(self._download_selected_attachments)
        
        # Mentions button
        self.view.show_mentions_btn.clicked.connect(self._show_mentions_grid)
        self.view.download_all_btn.clicked.connect(self._download_all_attachments)
        
        # Additional attachment button for managing attachments through the dialog
        from PyQt6.QtWidgets import QPushButton
        self.view.manage_attachments_btn = QPushButton("Manage Attachments")
        self.view.manage_attachments_btn.setToolTip("Open the attachments management dialog")
        self.view.attachments_layout.addWidget(self.view.manage_attachments_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.view.manage_attachments_btn.clicked.connect(self._show_attachments_dialog)

        # Annotation signals
        self.view.add_note_btn.clicked.connect(self._add_new_note_tab)
        self.view.notes_tab_widget.tabCloseRequested.connect(self._remove_note_tab)
        self.view.notes_tab_widget.currentChanged.connect(self._handle_note_tab_change)
        self.view.notes_tab_widget.tabBar().tabBarDoubleClicked.connect(self._rename_note_tab)
        
        # Time History signals
        self.view.refresh_history_btn.clicked.connect(self._load_time_history)
        self.view.tab_widget.currentChanged.connect(self._handle_tab_change)

        # Window close event
        self.view.closeEvent = self._on_close

    def _load_data(self):
        """
        Loads all necessary data from Jira and the local DB asynchronously.
        """
        try:
            # Record this view in history
            self.db_service.add_view_history(self.jira_key)
            
            # Show loading indicator
            self.view.details_browser.setHtml("<p><i>Loading issue details...</i></p>")
            self.view.comments_browser.setHtml("<p><i>Loading comments...</i></p>")
            
            # Clear existing attachments and show loading
            self._clear_attachment_widgets()
            loading_label = QLabel("Loading attachments...")
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.attachments_layout.addWidget(loading_label)
            
            # Check if Jira is available
            if not self.jira_service.is_connected():
                # Offline mode - use cached data
                cached_issue = self.db_service.get_jira_issue(self.jira_key)
                if cached_issue:
                    # Create a mock issue data structure with cached data
                    self._issue_data = {
                        'key': self.jira_key,
                        'fields': {
                            'summary': cached_issue['summary'],
                            'status': {'name': cached_issue['status']},
                            'priority': {'name': cached_issue['priority']},
                            'description': f"Visualizzazione offline. I dettagli completi saranno disponibili quando la connessione a Jira sarà ripristinata.",
                            'issuetype': {'name': 'Task'},
                            'project': {'name': 'Offline', 'key': ''},
                            'creator': {'displayName': 'Unknown (offline)'},
                            'assignee': {'displayName': 'Unknown (offline)'},
                            'reporter': {'displayName': 'Unknown (offline)'}
                        }
                    }
                    
                    # Populate what we can
                    self._populate_details()
                    self.view.comments_browser.setHtml("<p><i>I commenti non sono disponibili in modalità offline.</i></p>")
                    
                    # Show empty attachments
                    self._clear_attachment_widgets()
                    no_attachments_label = QLabel("Gli allegati non sono disponibili in modalità offline.")
                    no_attachments_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.view.attachments_layout.addWidget(no_attachments_label)
                else:
                    # No cached data available
                    self.view.details_browser.setHtml(f"<p><i>Nessun dato disponibile per {self.jira_key} in modalità offline.</i></p>")
                    self.view.comments_browser.setHtml("<p><i>I commenti non sono disponibili in modalità offline.</i></p>")
                    
                    # Show empty attachments
                    self._clear_attachment_widgets()
                    no_attachments_label = QLabel("Gli allegati non sono disponibili in modalità offline.")
                    no_attachments_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.view.attachments_layout.addWidget(no_attachments_label)
                
                # Load other data that doesn't depend on issue details
                self._populate_annotations()
                self._load_time_history()
                self._update_notification_button()
                return
            
            # Online mode - load from Jira
            # Cancel any existing issue detail loader
            if self._issue_detail_loader_worker:
                self._issue_detail_loader_worker.cancel()
                self._issue_detail_loader_worker.wait()
            
            # Start async issue detail loading
            self._issue_detail_loader_worker = IssueDetailLoaderWorker(self.jira_service, self.jira_key)
            self._issue_detail_loader_worker.issue_loaded.connect(self._on_issue_loaded)
            self._issue_detail_loader_worker.issue_error.connect(self._on_issue_error)
            self._issue_detail_loader_worker.start()
            
            # Load other data that doesn't depend on issue details
            self._populate_annotations()
            self._load_time_history()
            self._update_notification_button()

        except Exception as e:
            self.view.details_browser.setText(f"<b>Error loading issue data:</b><br>{e}")
            print(f"Error in JiraDetailController: {e}")
            # Don't populate other tabs if issue data failed to load
            return

    def _populate_details(self):
        """Populates the 'Details' tab."""
        if not self._issue_data:
            self.view.details_browser.setHtml("<p><i>No issue data available.</i></p>")
            return
            
        fields = self._issue_data.get('fields', {})
        
        # Use raw description field for markdown conversion
        description_md = fields.get('description', 'No description.')
        # Convert Jira's markup to HTML with proper handling of embedded media
        description_html = markdown.markdown(description_md or "", extensions=['tables', 'fenced_code'])
        
        # Process image links to make them viewable
        # Check for image pattern in the description - ![alt text](image_url)
        import re
        image_pattern = r'!\[(.*?)\]\((.*?)\)'
        
        # Process description HTML to replace image markdown with actual <img> tags
        if re.search(image_pattern, description_md or ""):
            for match in re.finditer(image_pattern, description_md or ""):
                alt_text = match.group(1)
                image_url = match.group(2)
                # Create an HTML img tag with the image URL and alt text
                img_tag = f'<img src="{image_url}" alt="{alt_text}" style="max-width:100%;">'
                description_html = description_html.replace(match.group(0), img_tag)

        # Formatta le date di creazione e aggiornamento
        created_date = "N/A"
        updated_date = "N/A"
        
        if fields.get('created'):
            try:
                # Parse the UTC datetime
                dt_object = datetime.fromisoformat(fields.get('created').replace('Z', '+00:00'))
                # Convert to local time
                local_dt = dt_object.astimezone()
                # Format for display with local timezone
                created_date = local_dt.strftime('%d %b %Y at %H:%M')
            except Exception as e:
                _logger.error(f"Error formatting created date: {e}")
                
        if fields.get('updated'):
            try:
                # Parse the UTC datetime
                dt_object = datetime.fromisoformat(fields.get('updated').replace('Z', '+00:00'))
                # Convert to local time
                local_dt = dt_object.astimezone()
                # Format for display with local timezone
                updated_date = local_dt.strftime('%d %b %Y at %H:%M')
            except Exception as e:
                _logger.error(f"Error formatting updated date: {e}")
        
        # Ottieni il creatore
        creator = fields.get('creator', {}).get('displayName', 'Unknown')
        
        # Ottieni il progetto
        project = fields.get('project', {}).get('name', 'N/A')
        project_key = fields.get('project', {}).get('key', '')
        project_html = f"{project} ({project_key})" if project_key else project
        
        # Ottieni i partecipanti (watchers) se disponibili
        watchers_count = fields.get('watches', {}).get('watchCount', 0)
        
        # If there are watchers, get the detailed list
        watchers_html = ""
        if watchers_count > 0 and self.jira_service.is_connected():
            try:
                # Get the issue key
                issue_key = self._issue_data.get('key')
                if issue_key:
                    watchers_list = self.jira_service.get_issue_watchers(issue_key)
                    if watchers_list:
                        # Format watchers list for display
                        watchers_names = [w['name'] for w in watchers_list]
                        watchers_str = ", ".join(watchers_names)
                        watchers_html = f"<p><b>Watchers:</b> {watchers_str}</p>"
                    else:
                        watchers_html = f"<p><b>Watchers:</b> {watchers_count}</p>"
                else:
                    watchers_html = f"<p><b>Watchers:</b> {watchers_count}</p>"
            except Exception as e:
                _logger.error(f"Error getting watchers: {e}")
                watchers_html = f"<p><b>Watchers:</b> {watchers_count}</p>"
        elif watchers_count > 0:
            watchers_html = f"<p><b>Watchers:</b> {watchers_count}</p>"
        
        # Aggiungi gli utenti coinvolti (reporter, assignee, commentatori)
        involved_users = set()
        
        # Reporter
        if fields.get('reporter', {}).get('displayName'):
            involved_users.add(fields.get('reporter', {}).get('displayName'))
            
        # Assignee
        if fields.get('assignee', {}).get('displayName'):
            involved_users.add(fields.get('assignee', {}).get('displayName'))
            
        # Creator (potrebbe essere già incluso come reporter)
        if creator != 'Unknown':
            involved_users.add(creator)
            
        # Commentatori
        comments = self._issue_data.get('fields', {}).get('comment', {}).get('comments', [])
        for comment in comments:
            if comment.get('author', {}).get('displayName'):
                involved_users.add(comment.get('author', {}).get('displayName'))
                
        # Converti il set in una lista ordinata e crea l'HTML
        involved_users_list = sorted(list(involved_users))
        involved_users_html = ", ".join(involved_users_list)

        # Build an HTML string for the details view
        html = f"""
            <h2>{fields.get('summary', 'No Summary')}</h2>
            <hr>
            <p><b>Type:</b> {fields.get('issuetype', {}).get('name', 'N/A')}</p>
            <p><b>Status:</b> {fields.get('status', {}).get('name', 'N/A')}</p>
            <p><b>Priority:</b> {fields.get('priority', {}).get('name', 'N/A')}</p>
            <p><b>Project:</b> {project_html}</p>
            <p><b>Created:</b> {created_date}</p>
            <p><b>Updated:</b> {updated_date}</p>
            <p><b>Creator:</b> {creator}</p>
            <p><b>Assignee:</b> {fields.get('assignee', {}).get('displayName', 'Unassigned')}</p>
            <p><b>Reporter:</b> {fields.get('reporter', {}).get('displayName', 'None')}</p>
            {watchers_html}
            <p><b>Participants:</b> {involved_users_html}</p>
            <hr>
            <h3>Description:</h3>
            {description_html}
        """
        self.view.details_browser.setHtml(html)

    def _populate_comments(self):
        """Populates the 'Comments' tab with formatted HTML."""
        if not self._issue_data:
            self.view.comments_browser.setHtml("<p><i>No issue data available.</i></p>")
            return

        comments = self._issue_data.get('renderedFields', {}).get('comment', {}).get('comments', [])
        
        if not comments:
            self.view.comments_browser.setHtml("<p><i>No comments on this issue.</i></p>")
            return
            
        html_parts = []
        for comment in comments:
            author = comment.get('author', {}).get('displayName', 'Unknown Author')
            # Use 'updated' for more accuracy, fallback to 'created'
            timestamp_str = comment.get('updated', comment.get('created', ''))
            
            # Parse the timestamp and format it nicely, converting from UTC to local time
            try:
                # Parse the UTC datetime
                dt_object = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Convert to local time
                local_dt = dt_object.astimezone()  # Senza argomenti, astimezone converte al fuso orario locale
                
                # Format for display with local timezone
                formatted_date = local_dt.strftime('%d %b %Y at %H:%M')
            except ValueError:
                formatted_date = "on an unknown date"

            body_html = comment.get('body', '<p><i>Empty comment.</i></p>')
            
            # Simple styling for each comment entry
            comment_html = f"""
                <div style="border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 10px;">
                    <p><b>{author}</b> <span style="color: #888;">commented on {formatted_date}</span></p>
                    {body_html}
                </div>
            """
            html_parts.append(comment_html)

        # Join all comments and set the HTML
        full_html = "".join(html_parts)
        self.view.comments_browser.setHtml(full_html)

    def _add_comment(self):
        """Adds a new comment to the sync queue."""
        comment_text = self.view.new_comment_input.toPlainText().strip()
        if not comment_text:
            QMessageBox.warning(self.view, "Empty Comment", "Cannot add an empty comment.")
            return

        payload = {
            "jira_key": self.jira_key,
            "body": comment_text
        }
        
        # Add to sync queue
        self.db_service.add_to_sync_queue("ADD_COMMENT", json.dumps(payload))
        
        # Check if auto-sync is enabled
        from services.app_settings import AppSettings
        # Use the controller's db_service instance when creating AppSettings
        app_settings = AppSettings(self.db_service)
        auto_sync = app_settings.get_setting("auto_sync", "false").lower() == "true"
        
        message = "Il commento è stato aggiunto alla coda di sincronizzazione."
        if auto_sync:
            message += " Sarà sincronizzato automaticamente."
            # TODO: Trigger sync process here
        else:
            message += " Sarà visibile su Jira dopo la prossima sincronizzazione manuale."
        
        QMessageBox.information(self.view, "Commento Aggiunto", message)
        
        # Clear the input field
        self.view.new_comment_input.clear()

    def _populate_attachments(self):
        """Populates the 'Attachments' tab and starts automatic downloads."""
        # Clear existing attachments
        self._clear_attachment_widgets()
        
        if not self._issue_data:
            # Show "no data" message
            no_data_label = QLabel("No issue data available.")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.attachments_layout.addWidget(no_data_label)
            self.view.download_selected_btn.setEnabled(False)
            self.view.download_all_btn.setEnabled(False)
            return
        
        self._attachments_data = self._issue_data.get('fields', {}).get('attachment', [])
        self._attachment_widgets = []
        self._download_workers = []
        self._thumbnail_workers = []
        
        if not self._attachments_data:
            # Show "no attachments" message
            no_attachments_label = QLabel("Nessun allegato presente in questo ticket.")
            no_attachments_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.attachments_layout.addWidget(no_attachments_label)
            self.view.download_selected_btn.setEnabled(False)
            self.view.download_all_btn.setEnabled(False)
            return

        self.view.download_selected_btn.setEnabled(True)
        self.view.download_all_btn.setEnabled(True)
        
        # Limit concurrent downloads to prevent too many threads
        self._pending_thumbnail_widgets = []
        self._pending_download_widgets = []
        
        # Create widgets for each attachment and start downloads/thumbnails with limit
        for i, attachment in enumerate(self._attachments_data):
            filename = attachment.get('filename', 'Unknown')
            size_kb = attachment.get('size', 0) / 1024
            
            # Verifica che l'allegato contenga l'ID per il download
            if not attachment.get('id'):
                _logger.error(f"Attachment is missing ID: {filename}")
                continue
                
            # Create attachment widget
            attachment_widget = self.view.create_attachment_widget(filename, size_kb, attachment)
            self.view.attachments_layout.addWidget(attachment_widget)
            self._attachment_widgets.append(attachment_widget)
            
            # Connect download button
            attachment_widget.download_btn.clicked.connect(
                lambda checked, widget=attachment_widget: self._download_single_attachment(widget)
            )
            
            # Connect open in browser button
            attachment_widget.open_browser_btn.clicked.connect(
                lambda checked, widget=attachment_widget: self._open_attachment_in_browser(widget)
            )
            
            # Connect thumbnail and filename clicks to open in browser
            attachment_widget.thumbnail_label.mousePressEvent = lambda event, widget=attachment_widget: self._handle_attachment_click(event, widget)
            attachment_widget.filename_label.mousePressEvent = lambda event, widget=attachment_widget: self._handle_attachment_click(event, widget)
            
            # Check if this is an image file for thumbnail generation
            file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
            
            if file_extension in image_extensions:
                # Start thumbnail download for images (limit concurrent)
                if len(self._thumbnail_workers) < self._max_concurrent_downloads:
                    self._start_thumbnail_download(attachment_widget)
                else:
                    # Queue for later
                    self._pending_thumbnail_widgets.append(attachment_widget)
                    attachment_widget.thumbnail_label.setText("🖼️")
                    attachment_widget.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f8f8f8; font-size: 24px;")
            else:
                # Start automatic download for non-image files (limit concurrent)
                if len(self._download_workers) < self._max_concurrent_downloads:
                    self._start_attachment_download(attachment_widget)
                else:
                    # Queue for later
                    self._pending_download_widgets.append(attachment_widget)

    def _upload_attachment(self):
        """Opens a file dialog to select a file and adds it to the sync queue."""
        file_path, _ = QFileDialog.getOpenFileName(self.view, "Select File to Upload")
        
        if not file_path:
            return

        payload = {
            "jira_key": self.jira_key,
            "file_path": file_path
        }

        self.db_service.add_to_sync_queue("ADD_ATTACHMENT", json.dumps(payload))

        QMessageBox.information(self.view, "Upload Queued",
                                f"The file '{os.path.basename(file_path)}' has been added to the sync queue.")

    def _clear_attachment_widgets(self):
        """Clear all attachment widgets and cancel any ongoing downloads."""
        # Cancel all download workers
        for worker in self._download_workers:
            worker.cancel()
            worker.wait()
        
        self._download_workers.clear()
        
        # Cancel all thumbnail workers
        for worker in self._thumbnail_workers:
            worker.cancel()
            worker.wait()
        
        self._thumbnail_workers.clear()
        
        # Clear pending queues
        
    def _open_attachment_in_browser(self, attachment_widget):
        """Opens the attachment in the browser."""
        attachment_data = attachment_widget.attachment_data
        content_url = attachment_data.get('content')
        
        if content_url:
            try:
                webbrowser.open(content_url)
            except Exception as e:
                QMessageBox.warning(self.view, "Errore", f"Impossibile aprire l'allegato nel browser: {str(e)}")
                _logger.error(f"Errore nell'apertura dell'allegato nel browser: {e}")
        else:
            QMessageBox.warning(self.view, "Errore", "URL dell'allegato non disponibile")
    
    def _show_mentions_grid(self):
        """Opens a grid view showing tickets with mentions of the current user."""
        try:
            # Check if Jira is connected
            if not self.jira_service.is_connected():
                QMessageBox.warning(self.view, "Connection Error", "Please connect to Jira to show mentions.")
                return
            
            # Get user info to display in the title
            user_info = self.jira_service.jira.myself()
            username = user_info.displayName if hasattr(user_info, 'displayName') else (user_info.name if hasattr(user_info, 'name') else 'Current User')
            
            # Create view and controller for the mentions grid
            from views.mentions_grid_view import MentionsGridView
            from controllers.mentions_grid_controller import MentionsGridController
            
            # Create view
            view = MentionsGridView(parent=self.view)
            view.setWindowTitle(f"Tickets Mentioning {username}")
            
            # Create controller and populate with data
            controller = MentionsGridController(view, self.jira_service)
            controller.load_mentions()
            
            # Show the view as a modal dialog
            view.exec()
            
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Failed to load mentions: {e}")
            _logger.error(f"Error in _show_mentions_grid: {e}")

    def _open_jira_in_browser(self):
        """Opens the current Jira ticket in the default browser."""
        try:
            # Costruisce l'URL del ticket Jira
            issue_url = f"{self.jira_service.jira.server_url}/browse/{self.jira_key}"
            
            # Apre l'URL nel browser predefinito
            webbrowser.open(issue_url)
        except Exception as e:
            QMessageBox.warning(self.view, "Errore", f"Impossibile aprire il ticket nel browser: {str(e)}")
            _logger.error(f"Errore nell'apertura del ticket nel browser: {e}")
    
    def _handle_attachment_click(self, event, attachment_widget):
        """Handle clicks on attachment thumbnail or filename."""
        # Gestire il click sull'etichetta dell'allegato
        self._open_attachment_in_browser(attachment_widget)
        
        # Chiamare il metodo mousePressEvent originale se necessario
        # super(type(attachment_widget.thumbnail_label), attachment_widget.thumbnail_label).mousePressEvent(event)
        self._pending_thumbnail_widgets.clear()
        self._pending_download_widgets.clear()
        
        # Clear all widgets from the layout
        while self.view.attachments_layout.count():
            item = self.view.attachments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._attachment_widgets.clear()

    # --- Annotation Methods ---

    def _populate_annotations(self):
        """Loads all annotations from the DB and creates tabs for them."""
        self.view.notes_tab_widget.clear()
        annotations = self.db_service.get_annotations(self.jira_key)
        
        drafts_to_recover = []
        
        if not annotations:
            self._add_new_note_tab(title="Note 1")
        else:
            for title, content in annotations:
                # Check if there's a draft version newer than the saved content
                draft_content = self.db_service.get_draft(self.jira_key, title)
                
                if draft_content:
                    # Store the info for later processing
                    drafts_to_recover.append((title, draft_content, content))
                    # Create the tab with the saved content for now
                    self._create_note_tab(title, content)
                else:
                    # No draft, just create the tab with saved content
                    self._create_note_tab(title, content)
        
        # Handle drafts after all tabs are created
        if drafts_to_recover:
            # Delay slightly to ensure UI is responsive
            QTimer.singleShot(500, lambda: self._process_drafts(drafts_to_recover))
        
        # Set up the autosave timer for the first tab
        if self.view.notes_tab_widget.count() > 0:
            self._handle_note_tab_change(0)
            
    def _process_drafts(self, drafts_info):
        """Process draft recovery after tabs are created."""
        # Ask once about recovering drafts
        if drafts_info:
            reply = QMessageBox.question(
                self.view, 
                "Recover Drafts", 
                f"Found {len(drafts_info)} unsaved draft(s). Do you want to recover them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Process each draft
                for title, draft_content, _ in drafts_info:
                    # Find the tab with this title
                    for i in range(self.view.notes_tab_widget.count()):
                        if self.view.notes_tab_widget.tabText(i) == title:
                            editor = self.view.notes_tab_widget.widget(i)
                            
                            # Set the draft content
                            if hasattr(editor, 'setMarkdown'):
                                editor.setMarkdown(draft_content)
                            elif hasattr(editor, 'setPlainText'):
                                editor.setPlainText(draft_content)
                            
                            # Immediately save it to the database
                            self._current_note_title = title
                            self._active_note_editor = editor
                            self._save_current_note()
                            
                            break

    def _setup_autosave_timer(self):
        """Create a single-shot autosave timer (debounce) for note editing.

        The timer is started by textChanged signals and will call
        _save_current_note after a short delay.
        """
        try:
            # 2 second debounce for draft save
            self.autosave_timer = QTimer(self)
            self.autosave_timer.setSingleShot(True)
            self.autosave_timer.setInterval(2000)
            self.autosave_timer.timeout.connect(self._save_current_note_draft)
            
            # 10 second debounce for actual save to database
            self.full_save_timer = QTimer(self)
            self.full_save_timer.setSingleShot(True)
            self.full_save_timer.setInterval(10000)  # 10 seconds
            self.full_save_timer.timeout.connect(self._save_current_note)
        except Exception as e:
            # Ensure controller still initializes even if timers are unavailable
            _logger.error(f"Failed to setup autosave timer: {e}")
            if hasattr(self, 'autosave_timer'):
                delattr(self, 'autosave_timer')
            if hasattr(self, 'full_save_timer'):
                delattr(self, 'full_save_timer')

    def _save_current_note_draft(self):
        """Save the currently active note as a draft.
        
        This is triggered more frequently for real-time autosave functionality.
        """
        try:
            if not self._active_note_editor or not self._current_note_title:
                return

            content = self._get_note_content()
            if content:
                # Persist to drafts DB
                self.db_service.save_draft(self.jira_key, self._current_note_title, content)
                # Also start the timer for the full save
                if hasattr(self, 'full_save_timer'):
                    self.full_save_timer.start()
        except Exception as e:
            _logger.error(f"Error saving note draft: {e}")
            # Best-effort save; do not raise from UI timer
            pass
    
    def _get_note_content(self):
        """Helper method to get content from the active note editor."""
        content = ""
        try:
            # MarkdownEditor compatibility
            if hasattr(self._active_note_editor, 'toMarkdown'):
                content = self._active_note_editor.toMarkdown()
            elif hasattr(self._active_note_editor, 'toPlainText'):
                content = self._active_note_editor.toPlainText()
            else:
                # Fallback: try grabbing textCursor contents
                try:
                    content = self._active_note_editor.document().toPlainText()
                except Exception:
                    content = ""
        except Exception as e:
            _logger.error(f"Error getting note content: {e}")
        
        return content
            
    def _save_current_note(self):
        """Save the currently active note to the DB safely.

        Supports both MarkdownEditor and QTextEdit. Uses the
        controller's db_service.save_annotation API.
        """
        try:
            if not self._active_note_editor or not self._current_note_title:
                return

            content = self._get_note_content()
            if content:
                # Persist to DB
                self.db_service.save_annotation(self.jira_key, self._current_note_title, content)
                
                # Delete the draft since we've saved the full version
                try:
                    self.db_service.delete_draft(self.jira_key, self._current_note_title)
                except Exception:
                    pass
                    
                # Mostra un feedback visivo temporaneo che indica che la nota è stata salvata
                self._show_save_indicator()
        except Exception as e:
            _logger.error(f"Error saving note: {e}")
            # Best-effort save; do not raise from UI timer
            pass
    
    def _show_save_indicator(self):
        """Shows a temporary visual indicator that the note was saved."""
        # Implementa un indicatore visibile ma non invasivo che la nota è stata salvata
        try:
            # Ottieni l'indice della scheda corrente
            current_index = self.view.notes_tab_widget.currentIndex()
            if current_index >= 0:
                # Ottieni il testo della scheda
                tab_text = self.view.notes_tab_widget.tabText(current_index)
                # Mostra un indicatore temporaneo nel testo della scheda
                self.view.notes_tab_widget.setTabText(current_index, f"{tab_text} ✓")
                
                # Ripristina il testo originale dopo 2 secondi
                QTimer.singleShot(2000, lambda: self.view.notes_tab_widget.setTabText(current_index, tab_text))
        except Exception:
            pass

    def _create_note_tab(self, title, content):
        """Helper to create a new tab with a markdown editor."""
        editor = MarkdownEditor(show_toolbar=False)
        editor.setMarkdown(content)
        editor.setPlaceholderText("Your private notes (Markdown supported)...")
        
        index = self.view.notes_tab_widget.addTab(editor, title)
        self.view.notes_tab_widget.setCurrentIndex(index)
        return editor

    def _add_new_note_tab(self, title=None):
        """Adds a new, empty note tab and switches to it."""
        if not title:
            new_title, ok = QInputDialog.getText(self.view, "New Note", "Enter title for the new note:")
            if not ok or not new_title.strip():
                return
            title = new_title.strip()

        # Check if a note with this title already exists
        annotations = self.db_service.get_annotations(self.jira_key)
        for ann_title, _ in annotations:
            if ann_title == title:
                QMessageBox.warning(self.view, "Duplicate Note", f"A note with the title '{title}' already exists.")
                return

        # Check if there is a draft version
        draft_content = self.db_service.get_draft(self.jira_key, title)
        initial_content = ""
        
        if draft_content:
            # Ask user if they want to recover the draft
            reply = QMessageBox.question(
                self.view, 
                "Draft Found", 
                f"A draft version of '{title}' was found. Do you want to recover it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                initial_content = draft_content
        
        # Create a new empty note in the database first
        self.db_service.save_annotation(self.jira_key, title, initial_content)

        # Create the editor and add the tab
        editor = self._create_note_tab(title, initial_content)
        
        # Switch to the new tab, which will trigger _handle_note_tab_change
        index = self.view.notes_tab_widget.indexOf(editor)
        self.view.notes_tab_widget.setCurrentIndex(index)

        # Explicitly set the current note title and connect the auto-save timers
        self._current_note_title = title
        if hasattr(self, 'autosave_timer'):
            self._active_note_editor = editor
            # Connect to draft autosave timer (runs every 2 seconds)
            self._active_note_editor.textChanged.connect(self.autosave_timer.start)
            # Connect to full save timer (runs after 10 seconds of inactivity)
            self._active_note_editor.textChanged.connect(self.full_save_timer.start)

    def _remove_note_tab(self, index):
        """Removes a note tab and deletes it from the database."""
        title = self.view.notes_tab_widget.tabText(index)
        reply = QMessageBox.question(
            self.view, "Confirm Delete", f"Are you sure you want to delete the note '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_service.delete_annotation(self.jira_key, title)
            self.view.notes_tab_widget.removeTab(index)
            if self.view.notes_tab_widget.count() == 0:
                self._active_note_editor = None

    def _rename_note_tab(self, index):
        """Renames the currently selected note tab."""
        old_title = self.view.notes_tab_widget.tabText(index)
        new_title, ok = QInputDialog.getText(self.view, "Rename Note", "Enter new title:", text=old_title)
        
        if ok and new_title and new_title.strip() != old_title:
            new_title = new_title.strip()
            self.db_service.rename_annotation(self.jira_key, old_title, new_title)
            self.view.notes_tab_widget.setTabText(index, new_title)

    def _handle_note_tab_change(self, index):
        """Saves the previous tab and sets up the autosave timer for the new one."""
        # Disconnect the textChanged signals from the old editor
        if self._active_note_editor:
            if hasattr(self, 'autosave_timer'):
                try:
                    self._active_note_editor.textChanged.disconnect(self.autosave_timer.start)
                except (TypeError, RuntimeError):
                    pass # Was not connected
                    
            if hasattr(self, 'full_save_timer'):
                try:
                    self._active_note_editor.textChanged.disconnect(self.full_save_timer.start)
                except (TypeError, RuntimeError):
                    pass # Was not connected

        # Save the content of the note that was active before the switch
        self._save_current_note()
        
        if index < 0:
            self._active_note_editor = None
            return

        current_widget = self.view.notes_tab_widget.widget(index)
        # Some tabs may be a plain editor widget (MarkdownEditor or QTextEdit)
        # or may be a container widget (from the view) exposing an `editor` attribute.
        editor_ref = None
        if isinstance(current_widget, (QTextEdit, MarkdownEditor)):
            editor_ref = current_widget
        elif hasattr(current_widget, 'editor'):
            # view-created container with .editor (QTextEdit inside)
            editor_ref = getattr(current_widget, 'editor', None)

        if editor_ref is not None:
            self._active_note_editor = editor_ref
            
            # Update the current note title
            self._current_note_title = self.view.notes_tab_widget.tabText(index)

            # Only load content from DB if the editor is empty (i.e., just created)
            try:
                empty_text = self._active_note_editor.toPlainText().strip()
            except Exception:
                # Fallback for editors exposing toMarkdown()
                try:
                    empty_text = self._active_note_editor.toMarkdown().strip()
                except Exception:
                    empty_text = ""

            if empty_text == "":
                # Check if there's a draft version first
                draft_content = self.db_service.get_draft(self.jira_key, self._current_note_title)
                
                if draft_content:
                    # Load the draft version
                    self._active_note_editor.blockSignals(True)
                    self._active_note_editor.setMarkdown(draft_content)
                    self._active_note_editor.blockSignals(False)
                else:
                    # Load from regular annotations
                    annotations = self.db_service.get_annotations(self.jira_key)
                    for ann_title, ann_content in annotations:
                        if ann_title == self._current_note_title:
                            self._active_note_editor.blockSignals(True)
                            self._active_note_editor.setMarkdown(ann_content)
                            self._active_note_editor.blockSignals(False)
                            break

            # Connect the textChanged signals to the timers
            if hasattr(self, 'autosave_timer'):
                try:
                    # Connect to draft autosave (2 seconds)
                    self._active_note_editor.textChanged.connect(self.autosave_timer.start)
                except Exception:
                    pass
                    
            if hasattr(self, 'full_save_timer'):
                try:
                    # Connect to full save (10 seconds)
                    self._active_note_editor.textChanged.connect(self.full_save_timer.start)
                except Exception:
                    pass

            # Wire the top toolbar buttons to the new active editor
            try:
                self._wire_toolbar_actions_for_editor(self._active_note_editor)
            except Exception:
                pass

    def _wire_toolbar_actions_for_editor(self, editor):
        """Connects the JiraDetailView toolbar buttons to the provided editor.

        This supports both MarkdownEditor (which exposes API methods) and plain
        QTextEdit. Connections are replaced atomically to avoid duplicate handlers.
        """
        view = self.view

        # Helper wrappers that operate on the editor safely. Use the inner QTextEdit
        # when available for direct cursor editing which is robust across both
        # MarkdownEditor instances and view-created container widgets.
        def _get_text_edit_target():
            # Return a QTextEdit instance we can operate on directly, or None
            _logger.debug(f"_get_text_edit_target called for editor type: {type(editor).__name__}")
            try:
                # If editor is a MarkdownEditor instance with an internal `editor` QTextEdit
                if hasattr(editor, 'editor') and editor.editor is not None:
                    _logger.debug("Found MarkdownEditor with internal editor")
                    return editor.editor
                # If editor itself is a QTextEdit
                from PyQt6.QtWidgets import QTextEdit
                if isinstance(editor, QTextEdit):
                    _logger.debug("Editor is directly a QTextEdit")
                    return editor
                # If it's a view container exposing .editor attribute
                if hasattr(editor, 'editor'):
                    _logger.debug("Found editor attribute on container")
                    return getattr(editor, 'editor')
            except Exception as e:
                _logger.debug(f"Exception in _get_text_edit_target: {e}")
                pass
            _logger.debug("No suitable text edit target found")
            return None

        def wrap_selection(prefix, suffix=None):
            te = _get_text_edit_target()
            try:
                # Prefer editor-level API when present (MarkdownEditor)
                if hasattr(editor, 'wrap_selection'):
                    _logger.debug("Using editor.wrap_selection method")
                    if suffix is None:
                        editor.wrap_selection(prefix)
                    else:
                        editor.wrap_selection(prefix, suffix)
                    return

                # Directly operate on QTextEdit as fallback
                if te is not None:
                    _logger.debug("Using direct QTextEdit operation")
                    tc = te.textCursor()
                    if suffix is None:
                        suffix = prefix
                    if tc.hasSelection():
                        sel = tc.selectedText()
                        _logger.debug(f"Selected text: '{sel}'")
                        tc.insertText(f"{prefix}{sel}{suffix}")
                    else:
                        _logger.debug("No selection, inserting prefix+suffix")
                        # Insert prefix+suffix and move cursor between them
                        start_pos = tc.position()
                        tc.insertText(f"{prefix}{suffix}")
                        # Move cursor back to between prefix and suffix
                        for _ in range(len(suffix)):
                            tc.movePosition(tc.MoveOperation.Left)
                        te.setTextCursor(tc)
                    te.setFocus()
                    _logger.debug("Operation completed successfully")
                    return
            except Exception as e:
                _logger.exception(f"Error in wrap_selection wrapper: {e}")

            # Last-resort: call view-level helper
            try:
                if hasattr(self.view, '_wrap_selection'):
                    if suffix is None:
                        self.view._wrap_selection(prefix, prefix)
                    else:
                        self.view._wrap_selection(prefix, suffix)
            except Exception:
                _logger.exception("Error calling view._wrap_selection fallback")

        def insert_bullet():
            te = _get_text_edit_target()
            try:
                if hasattr(editor, 'insert_bullet_list'):
                    editor.insert_bullet_list()
                    return
                if te is not None:
                    tc = te.textCursor()
                    tc.movePosition(tc.MoveOperation.StartOfLine)
                    tc.insertText('- ')
                    te.setTextCursor(tc)
                    te.setFocus()
                    return
            except Exception:
                _logger.exception("Error in insert_bullet wrapper")

            try:
                if hasattr(self.view, '_bullet_list'):
                    self.view._bullet_list()
            except Exception:
                _logger.exception("Error calling view._bullet_list fallback")

        def insert_numbered():
            te = _get_text_edit_target()
            try:
                if hasattr(editor, 'insert_numbered_list'):
                    editor.insert_numbered_list()
                    return
                if te is not None:
                    tc = te.textCursor()
                    tc.movePosition(tc.MoveOperation.StartOfLine)
                    tc.insertText('1. ')
                    te.setTextCursor(tc)
                    te.setFocus()
                    return
            except Exception:
                _logger.exception("Error in insert_numbered wrapper")

            try:
                if hasattr(self.view, '_numbered_list'):
                    self.view._numbered_list()
            except Exception:
                _logger.exception("Error calling view._numbered_list fallback")

        def insert_link():
            te = _get_text_edit_target()
            try:
                if hasattr(editor, 'insert_link'):
                    editor.insert_link()
                    return
                if te is not None:
                    tc = te.textCursor()
                    if tc.hasSelection():
                        text = tc.selectedText()
                    else:
                        text = 'Link Text'
                    tc.insertText(f'[{text}](URL)')
                    te.setTextCursor(tc)
                    te.setFocus()
                    return
            except Exception:
                _logger.exception("Error in insert_link wrapper")

            try:
                if hasattr(self.view, '_insert_link'):
                    self.view._insert_link()
            except Exception:
                _logger.exception("Error calling view._insert_link fallback")

        def toggle_preview():
            try:
                # Prefer editor-level preview toggle if available
                if hasattr(editor, 'toggle_preview'):
                    editor.toggle_preview()
                    return
            except Exception:
                _logger.exception("Error calling editor.toggle_preview")

            try:
                if hasattr(self.view, '_toggle_preview'):
                    self.view._toggle_preview()
            except Exception:
                _logger.exception("Error calling view._toggle_preview fallback")

        def prefix_line(prefix):
            te = _get_text_edit_target()
            try:
                if hasattr(editor, 'insert_header'):
                    # MarkdownEditor has insert_header(level) - map prefix
                    level = prefix.count('#')
                    editor.insert_header(level)
                    return
                if te is not None:
                    tc = te.textCursor()
                    tc.movePosition(tc.MoveOperation.StartOfLine)
                    tc.insertText(prefix)
                    te.setTextCursor(tc)
                    te.setFocus()
                    return
            except Exception:
                _logger.exception("Error in prefix_line wrapper")

            try:
                # Last-resort: call view helper
                if hasattr(self.view, '_prefix_line'):
                    self.view._prefix_line(prefix)
            except Exception:
                pass

        # Disconnect previous connections by reassigning slots (best effort)
        try:
            view.bold_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.italic_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.code_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.bullet_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.h1_btn.clicked.disconnect()
            view.h2_btn.clicked.disconnect()
            view.h3_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.underline_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.number_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.link_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            view.preview_btn.clicked.disconnect()
        except Exception:
            pass

        # Reconnect to the wrappers
        view.bold_btn.clicked.connect(lambda: wrap_selection('**'))
        view.italic_btn.clicked.connect(lambda: wrap_selection('*'))
        view.code_btn.clicked.connect(lambda: wrap_selection('`'))
        view.bullet_btn.clicked.connect(lambda: insert_bullet())
        view.h1_btn.clicked.connect(lambda: prefix_line('# '))
        view.h2_btn.clicked.connect(lambda: prefix_line('## '))
        view.h3_btn.clicked.connect(lambda: prefix_line('### '))
        view.underline_btn.clicked.connect(lambda: wrap_selection('~~'))
        view.number_btn.clicked.connect(lambda: insert_numbered())
        view.link_btn.clicked.connect(lambda: insert_link())
        view.preview_btn.clicked.connect(lambda: toggle_preview())

        # Emoji picker binds to _insert_emoji which already uses notes_tab_widget to find the active editor
        try:
            view.emoji_picker_btn.clicked.disconnect()
        except Exception:
            pass
        view.emoji_picker_btn.clicked.connect(lambda: self.view._open_emoji_picker() if hasattr(self.view, '_open_emoji_picker') else None)

    def _on_close(self, event):
        """Handler to be called when the window is closed."""
        self._save_current_note() # Ensure last active note is saved
        
        # Cancel all ongoing downloads
        _logger.debug("Cancelling download workers...")
        for worker in self._download_workers[:]:  # Copy list to avoid modification during iteration
            try:
                worker.cancel()
            except Exception as e:
                _logger.debug(f"Error cancelling download worker: {e}")
        
        # Cancel all thumbnail downloads
        _logger.debug("Cancelling thumbnail workers...")
        for worker in self._thumbnail_workers[:]:  # Copy list to avoid modification during iteration
            try:
                worker.cancel()
            except Exception as e:
                _logger.debug(f"Error cancelling thumbnail worker: {e}")
        
        # Cancel links loader
        if self._links_loader_worker:
            _logger.debug("Cancelling links loader worker...")
            try:
                self._links_loader_worker.cancel()
            except Exception as e:
                _logger.debug(f"Error cancelling links loader worker: {e}")
        
        # Cancel issue detail loader
        if self._issue_detail_loader_worker:
            _logger.debug("Cancelling issue detail loader worker...")
            try:
                self._issue_detail_loader_worker.cancel()
            except Exception as e:
                _logger.debug(f"Error cancelling issue detail loader worker: {e}")
        
        # Wait for all workers to finish with timeout
        _logger.debug("Waiting for workers to finish...")
        from PyQt6.QtCore import QDeadlineTimer
        timeout = QDeadlineTimer(5000)  # 5 second timeout
        
        # Wait for download workers
        for worker in self._download_workers[:]:
            if worker.isRunning() and not worker.wait(timeout):
                _logger.warning(f"Download worker did not finish within timeout, terminating: {type(worker).__name__}")
                worker.terminate()
                worker.wait(1000)  # Give it 1 more second after terminate
        
        # Wait for thumbnail workers
        for worker in self._thumbnail_workers[:]:
            if worker.isRunning() and not worker.wait(timeout):
                _logger.warning(f"Thumbnail worker did not finish within timeout, terminating: {type(worker).__name__}")
                worker.terminate()
                worker.wait(1000)
        
        # Wait for links loader
        if self._links_loader_worker and self._links_loader_worker.isRunning():
            if not self._links_loader_worker.wait(timeout):
                _logger.warning("Links loader worker did not finish within timeout, terminating")
                self._links_loader_worker.terminate()
                self._links_loader_worker.wait(1000)
        
        # Wait for issue detail loader
        if self._issue_detail_loader_worker and self._issue_detail_loader_worker.isRunning():
            if not self._issue_detail_loader_worker.wait(timeout):
                _logger.warning("Issue detail loader worker did not finish within timeout, terminating")
                self._issue_detail_loader_worker.terminate()
                self._issue_detail_loader_worker.wait(1000)
        
        self.pause_timer()
        
        # Emit the window closed signal
        self.window_closed.emit(self.jira_key)
        
        event.accept()

    def _toggle_timer(self):
        """Starts or pauses the timer."""
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        """Starts the timer."""
        self.is_running = True
        self.view.start_pause_btn.setText("Pause")
        self.timer.start()
        self.timer_started.emit(self.jira_key)

    def pause_timer(self):
        """Pauses the timer."""
        self.timer.stop()
        self.is_running = False
        self.view.start_pause_btn.setText("Start")
        
        # Save final time before stopping
        self.db_service.update_local_time(
            self.jira_key, 
            self.total_seconds_tracked,
            datetime.now()
        )

    def _add_time_manually(self):
        """Opens a dialog to add a worklog manually."""
        from controllers.add_time_controller import AddTimeController
        
        add_time_controller = AddTimeController(self.view)
        data = add_time_controller.run()

        if data:
            start_time = data["start_time"]
            seconds = data["time_spent_seconds"]
            comment = data["comment"]
            task = data["task"]
            
            # Add to local worklog history
            self.db_service.add_local_worklog(
                self.jira_key, 
                start_time, 
                seconds,
                comment,
                task
            )
            
            # Add to sync queue
            payload = {
                "jira_key": self.jira_key,
                "time_spent_seconds": seconds,
                "start_time": start_time.isoformat(),
                "comment": comment,
                "task": task
            }
            
            # Add to sync queue
            self.db_service.add_to_sync_queue("ADD_WORKLOG", json.dumps(payload))
            
            # Check if auto-sync is enabled (use this controller's db_service)
            from services.app_settings import AppSettings
            app_settings = AppSettings(self.db_service)
            auto_sync = app_settings.get_setting("auto_sync", "false").lower() == "true"
            
            # Reload time history to show new entry
            self._load_time_history()
            
            message = "Il worklog è stato aggiunto alla coda di sincronizzazione."
            if auto_sync:
                message += " Sarà sincronizzato automaticamente."
                # TODO: Trigger sync process here
            else:
                message += " Sarà visibile su Jira dopo la prossima sincronizzazione manuale."
                
            QMessageBox.information(self.view, "Worklog Aggiunto", message)


    def _stop_timer(self):
        """Stops the timer, adds worklog to sync queue, and resets."""
        if not self.is_running and self.total_seconds_tracked == 0:
            return # Nothing to do

        self.pause_timer() # Pause first to save the last second

        # Confirm with the user
        reply = QMessageBox.question(
            self.view,
            'Confirm Stop',
            f"Are you sure you want to stop the timer and log the tracked time for {self.jira_key}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Round up to the nearest minute (Req 2.4.2.1)
        if self.total_seconds_tracked > 0:
            minutes_to_log = math.ceil(self.total_seconds_tracked / 60)
            seconds_to_log = minutes_to_log * 60
            
            start_time_obj = self.db_service.get_start_time(self.jira_key)
            start_time = start_time_obj.isoformat() if start_time_obj else datetime.now().isoformat()
            
            # Add to local worklog history
            self.db_service.add_local_worklog(
                self.jira_key, 
                start_time_obj if start_time_obj else datetime.now(), 
                seconds_to_log,
                "Worklog from Jira Time Tracker"
            )
            
            # Add to sync queue
            payload = {
                "jira_key": self.jira_key,
                "time_spent_seconds": seconds_to_log,
                "start_time": start_time,
                "comment": "Worklog from Jira Time Tracker"
            }
            
            # Add to sync queue
            self.db_service.add_to_sync_queue("ADD_WORKLOG", json.dumps(payload))
            
            # Check if auto-sync is enabled
            from services.app_settings import AppSettings
            app_settings = AppSettings(self.db_service)
            auto_sync = app_settings.get_setting("auto_sync", "false").lower() == "true"

        # Reset everything
        self.total_seconds_tracked = 0
        self.db_service.reset_local_time(self.jira_key)
        self._update_display()
        
        # Reload time history to show new entry
        self._load_time_history()
        
        # Emit the timer stopped signal
        self.timer_stopped.emit(self.jira_key)
        
        message = "Il worklog è stato aggiunto alla coda di sincronizzazione."
        if auto_sync:
            message += " Sarà sincronizzato automaticamente."
            # TODO: Trigger sync process here
        else:
            message += " Sarà visibile su Jira dopo la prossima sincronizzazione manuale."
            
        QMessageBox.information(self.view, "Timer Fermato", message)


    def _update_display(self):
        """Updates the timer label and saves time to DB if running."""
        if self.is_running:
            self.total_seconds_tracked += 1
            
            # Save to DB every second while running
            self.db_service.update_local_time(
                self.jira_key, 
                self.total_seconds_tracked,
                datetime.now() # Update start time to now to reflect continuous tracking
            )
            
            # Emit the time updated signal
            self.time_updated.emit(self.jira_key, self.total_seconds_tracked)
        
        self.view.timer_label.setText(self._format_time(self.total_seconds_tracked))
        
    def _load_time_history(self):
        """Loads the local time history for this issue."""
        # Clear the table
        self.view.time_history_table.setRowCount(0)
        
        # Get history from database
        time_logs = self.db_service.get_local_worklogs(self.jira_key)
        
        if not time_logs:
            return
        
        # Add rows to table
        self.view.time_history_table.setRowCount(len(time_logs))
        
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtGui import QColor, QBrush
        
        for row, (log_id, start_time, duration_seconds, comment, sync_status, task) in enumerate(time_logs):
            # Format start time and convert from UTC to local time
            try:
                # Parse the UTC datetime
                dt_object = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                
                # Convert to local time
                local_dt = dt_object.astimezone()  # Senza argomenti, astimezone converte al fuso orario locale
                
                # Format for display with local timezone
                formatted_date = local_dt.strftime('%d %b %Y %H:%M')
            except ValueError:
                formatted_date = "Unknown date"
                
            # Format duration
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            formatted_duration = f"{hours}h {minutes}m"
            
            # Create items
            date_item = QTableWidgetItem(formatted_date)
            duration_item = QTableWidgetItem(formatted_duration)
            comment_item = QTableWidgetItem(comment if comment else "")
            status_item = QTableWidgetItem(sync_status)
            
            # Set color based on sync status
            if sync_status == "Pending":
                status_item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
            elif sync_status == "Failed":
                status_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            elif sync_status == "Synced":
                status_item.setBackground(QBrush(QColor(200, 255, 200)))  # Light green
            
            # Add items to table
            self.view.time_history_table.setItem(row, 0, date_item)
            self.view.time_history_table.setItem(row, 1, duration_item)
            self.view.time_history_table.setItem(row, 2, comment_item)
            self.view.time_history_table.setItem(row, 3, status_item)
            
            # Store log_id in the date_item for later reference
            date_item.setData(Qt.ItemDataRole.UserRole, log_id)

        # Resize columns to content
        self.view.time_history_table.resizeColumnsToContents()
        
    def _handle_tab_change(self, index):
        """Handles tab changes to update data if needed."""
        # If the time history tab is selected, refresh the data
        if index == 4:  # Index of Time History tab
            self._load_time_history()

    def _update_notification_button(self):
        """Updates the notification subscription button state."""
        is_subscribed = self.db_service.get_notification_subscription(self.jira_key) is not None
        self.view.notification_btn.setChecked(is_subscribed)
        self.view.notification_btn.setText("🔔 Non ricevere notifiche" if is_subscribed else "🔕 Ricevi notifiche")

    def _toggle_notification_subscription(self):
        """Toggles the notification subscription status for this issue."""
        is_subscribed = self.db_service.get_notification_subscription(self.jira_key) is not None
        
        if is_subscribed:
            # Unsubscribe
            self.db_service.delete_notification_subscription(self.jira_key)
            self.view.notification_btn.setText("🔕 Ricevi notifiche")
        else:
            # Subscribe
            self.db_service.add_notification_subscription(self.jira_key)
            self.view.notification_btn.setText("🔔 Non ricevere notifiche")

    def _start_attachment_download(self, attachment_widget):
        """Start downloading an attachment."""
        # Create and start download worker
        worker = AttachmentDownloadWorker(
            self.jira_service,
            attachment_widget.attachment_data,
            attachment_widget
        )
        
        # Connect signals
        worker.progress_updated.connect(self._on_download_progress)
        worker.download_finished.connect(self._on_download_finished)
        worker.download_error.connect(self._on_download_error)
        
        # Store worker reference
        self._download_workers.append(worker)
        # Start download
        worker.start()
    
    def _start_thumbnail_download(self, attachment_widget):
        """Start downloading thumbnail for an image attachment."""
        # Create and start thumbnail worker
        worker = ThumbnailDownloadWorker(
            self.jira_service,
            attachment_widget.attachment_data,
            attachment_widget
        )
        
        # Connect signals
        worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        worker.thumbnail_error.connect(self._on_thumbnail_error)
        
        # Store worker reference
        self._thumbnail_workers.append(worker)
        # Start thumbnail download
        worker.start()
    
    @pyqtSlot(object, object)
    def _on_thumbnail_ready(self, attachment_widget, pixmap):
        """Handle successful thumbnail creation."""
        # Set the thumbnail pixmap to the widget
        attachment_widget.thumbnail_label.setPixmap(pixmap)
        
        # Remove worker from active list
        for worker in self._thumbnail_workers:
            if worker.attachment_widget == attachment_widget:
                self._thumbnail_workers.remove(worker)
                break
        
        # Start next pending thumbnail download
        self._start_next_pending_thumbnail()
    
    @pyqtSlot(object, str)
    def _on_thumbnail_error(self, attachment_widget, error_message):
        """Handle thumbnail creation errors."""
        # Keep the default icon, maybe show a different style
        attachment_widget.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #ffe6e6; font-size: 24px;")
        attachment_widget.thumbnail_label.setText("🖼️❌")
        
        print(f"Thumbnail error for {attachment_widget.filename}: {error_message}")
        
        # Remove worker from active list
        for worker in self._thumbnail_workers:
            if worker.attachment_widget == attachment_widget:
                self._thumbnail_workers.remove(worker)
                break
        
        # Start next pending thumbnail download
        self._start_next_pending_thumbnail()
    
    def _download_single_attachment(self, attachment_widget):
        """Download a single attachment."""
        # Cancel any existing download for this widget
        for worker in self._download_workers:
            if worker.attachment_widget == attachment_widget:
                worker.cancel()
                worker.wait()
                self._download_workers.remove(worker)
                break
        
        # Reset widget state
        self._reset_attachment_widget(attachment_widget)
        
        # Start new download
        self._start_attachment_download(attachment_widget)
    
    def _download_selected_attachments(self):
        """Download selected attachments."""
        # For now, download all since we don't have selection mechanism
        self._download_all_attachments()
    
    def _download_all_attachments(self):
        """Download all attachments."""
        for widget in self._attachment_widgets:
            # Only download if not already completed
            if widget.status_label.text() != "✅":
                self._download_single_attachment(widget)
    
    @pyqtSlot(object, int)
    def _on_download_progress(self, attachment_widget, progress):
        """Handle download progress updates."""
        # Don't modify thumbnail_label, use progress bar and button text
        attachment_widget.progress_bar.setVisible(True)
        attachment_widget.progress_bar.setValue(progress)
        attachment_widget.download_btn.setEnabled(False)
        attachment_widget.download_btn.setText("Downloading...")
    
    @pyqtSlot(object, str)
    def _on_download_finished(self, attachment_widget, file_path):
        """Handle successful download completion."""
        attachment_widget.progress_bar.setVisible(False)
        attachment_widget.download_btn.setEnabled(True)
        attachment_widget.download_btn.setText("Apri")
        
        # Store the file path for opening
        attachment_widget.downloaded_file_path = file_path
        
        # Connect button to open file instead of download
        attachment_widget.download_btn.clicked.disconnect()
        attachment_widget.download_btn.clicked.connect(
            lambda: self._open_downloaded_file(file_path)
        )
        
        # Remove worker from active list
        for worker in self._download_workers:
            if worker.attachment_widget == attachment_widget:
                self._download_workers.remove(worker)
                break
        
        # Start next pending download
        self._start_next_pending_download()
    
    @pyqtSlot(object, str)
    def _on_download_error(self, attachment_widget, error_message):
        """Handle download errors."""
        attachment_widget.progress_bar.setVisible(False)
        attachment_widget.download_btn.setEnabled(True)
        attachment_widget.download_btn.setText("Riprova")
        
        # Connect button to retry download
        attachment_widget.download_btn.clicked.disconnect()
        attachment_widget.download_btn.clicked.connect(
            lambda: self._download_single_attachment(attachment_widget)
        )
        
        print(f"Download error for {attachment_widget.filename}: {error_message}")
        
        # Remove worker from active list
        for worker in self._download_workers:
            if worker.attachment_widget == attachment_widget:
                self._download_workers.remove(worker)
                break
        
        # Start next pending download
        self._start_next_pending_download()
    
    def _reset_attachment_widget(self, attachment_widget):
        """Reset an attachment widget to initial state."""
        # Reset status label to appropriate icon based on file type
        filename = attachment_widget.filename
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
        video_extensions = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']
        audio_extensions = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']
        
        # Only reset text/icon if it's not already showing a pixmap
        if not attachment_widget.thumbnail_label.pixmap() or attachment_widget.thumbnail_label.pixmap().isNull():
            if file_extension in video_extensions:
                attachment_widget.thumbnail_label.setText("🎥")
                attachment_widget.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #ffe8e8; font-size: 24px;")
            elif file_extension in audio_extensions:
                attachment_widget.thumbnail_label.setText("🎵")
                attachment_widget.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #e8ffe8; font-size: 24px;")
            else:
                attachment_widget.thumbnail_label.setText("📄")
                attachment_widget.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f8f8f8; font-size: 24px;")
        
        attachment_widget.progress_bar.setVisible(False)
        attachment_widget.progress_bar.setValue(0)
        attachment_widget.download_btn.setEnabled(True)
        attachment_widget.download_btn.setText("Download")
        
        # Reconnect download button
        try:
            attachment_widget.download_btn.clicked.disconnect()
        except TypeError:
            pass  # Not connected
        
        attachment_widget.download_btn.clicked.connect(
            lambda: self._download_single_attachment(attachment_widget)
        )
    
    def _open_downloaded_file(self, file_path):
        """Open a downloaded file."""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.warning(self.view, "Errore", f"Impossibile aprire il file: {e}")
    
    def _start_async_links_loading(self):
        """Start asynchronous loading of issue links with loading indicator."""
        # Show loading indicator
        self.view.issue_links_tree.clear()
        loading_item = self.view.issue_links_tree.addTopLevelItem(
            self.view.create_tree_item("Caricamento collegamenti...", "", "", "loading")
        )
        self.view.issue_links_tree.setEnabled(False)
        
        # Cancel any existing links loader
        if self._links_loader_worker:
            self._links_loader_worker.cancel()
            self._links_loader_worker.wait()
        
        # Start new links loader
        self._links_loader_worker = IssueLinksLoaderWorker(self.jira_service, self.jira_key)
        self._links_loader_worker.links_loaded.connect(self._on_links_loaded)
        self._links_loader_worker.links_error.connect(self._on_links_error)
        self._links_loader_worker.start()

    @pyqtSlot(list)
    def _on_links_loaded(self, links_tree):
        """Handle successful loading of issue links."""
        try:
            # Clear loading indicator
            self.view.issue_links_tree.clear()
            self.view.issue_links_tree.setEnabled(True)
            
            if not links_tree:
                # No links found
                no_links_item = self.view.issue_links_tree.addTopLevelItem(
                    self.view.create_tree_item("Nessun collegamento trovato", "", "", "info")
                )
                return
            
            # Build the tree structure
            self._build_links_tree_widget(links_tree)
            
            # Expand the root item
            if self.view.issue_links_tree.topLevelItemCount() > 0:
                self.view.issue_links_tree.topLevelItem(0).setExpanded(True)
            
            # Update the auto-generated note with links information
            self._update_auto_note_with_links(links_tree)
            
        except Exception as e:
            print(f"Error building links tree: {e}")
            self._on_links_error("Errore nella costruzione dell'albero dei collegamenti")
    
    @pyqtSlot(str)
    def _on_links_error(self, error_message):
        """Handle error loading issue links."""
        self.view.issue_links_tree.clear()
        self.view.issue_links_tree.setEnabled(True)
        
        error_item = self.view.issue_links_tree.addTopLevelItem(
            self.view.create_tree_item(f"Errore: {error_message}", "", "", "error")
        )
    
    def _build_links_tree_widget(self, links_tree):
        """Build the QTreeWidget from the links tree data."""
        for root_data in links_tree:
            root_item = self.view.create_tree_item(
                root_data['key'],
                root_data['summary'],
                root_data['status'],
                root_data['type']
            )
            self.view.issue_links_tree.addTopLevelItem(root_item)
            
            # Add children recursively
            self._add_tree_children(root_item, root_data['children'])
    
    def _add_tree_children(self, parent_item, children_data):
        """Recursively add children to a tree item."""
        for child_data in children_data:
            child_item = self.view.create_tree_item(
                child_data['key'],
                child_data['summary'],
                child_data.get('status', ''),
                child_data.get('direction', 'child'),
                child_data.get('link_type', '')
            )
            parent_item.addChild(child_item)
            
            # Add grandchildren if any
            if child_data.get('children'):
                self._add_tree_children(child_item, child_data['children'])

    def _start_next_pending_thumbnail(self):
        """Start the next pending thumbnail download if available."""
        if self._pending_thumbnail_widgets and len(self._thumbnail_workers) < self._max_concurrent_downloads:
            widget = self._pending_thumbnail_widgets.pop(0)
            self._start_thumbnail_download(widget)
    
    def _start_next_pending_download(self):
        """Start the next pending download if available."""
        if self._pending_download_widgets and len(self._download_workers) < self._max_concurrent_downloads:
            widget = self._pending_download_widgets.pop(0)
            self._start_attachment_download(widget)
    
    def _on_issue_loaded(self, issue_data):
        """Handle successful loading of issue details."""
        try:
            # Store the issue data
            self._issue_data = issue_data
            
            # Save issue details in local cache for offline mode
            try:
                jira_key = issue_data.get('key')
                if jira_key:
                    fields = issue_data.get('fields', {})
                    summary = fields.get('summary', '')
                    status = fields.get('status', {}).get('name', '')
                    priority = fields.get('priority', {}).get('name', '')
                    
                    # Save to cache database
                    self.db_service.save_jira_issue(jira_key, summary, status, priority)
            except Exception as cache_e:
                print(f"Error saving issue to cache: {cache_e}")
                # Continue with display even if caching fails
            
            # Populate the view with the data
            self._populate_details()
            self._populate_comments()
            self._populate_attachments()
            self._start_async_links_loading()  # Start async loading of issue links
            
            # Set the current priority in the combo box
            self._update_priority_combo_from_issue_data()
            
            # Create or update auto-generated note with issue details
            self._create_or_update_auto_note()
            
        except Exception as e:
            print(f"Error populating issue data: {e}")
            self.view.details_browser.setText(f"<b>Error populating issue data:</b><br>{e}")
    
    def _update_priority_combo_from_issue_data(self):
        """Update the priority combo box based on current issue data."""
        if not self._issue_data:
            return
            
        try:
            # Get the current priority from the issue data
            priority_id = self._issue_data.get('fields', {}).get('priority', {}).get('id')
            if not priority_id:
                return
                
            # Find and select the matching priority in the combo box
            for i in range(self.view.priority_combo.count()):
                if self.view.priority_combo.itemData(i) == priority_id:
                    self.view.priority_combo.blockSignals(True)  # Prevent triggering the changed signal
                    self.view.priority_combo.setCurrentIndex(i)
                    self.view.priority_combo.blockSignals(False)
                    break
        except Exception as e:
            print(f"Error updating priority combo: {e}")
    
    @pyqtSlot(str)
    def _on_issue_error(self, error_message):
        """Handle error loading issue details."""
        self.view.details_browser.setText(f"<b>Error loading issue data:</b><br>{error_message}")
        self.view.comments_browser.setText(f"<b>Error loading comments:</b><br>{error_message}")
        
        # Clear loading indicators from attachments
        self._clear_attachment_widgets()
        error_label = QLabel(f"Error loading attachments: {error_message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.attachments_layout.addWidget(error_label)
        
        print(f"Error in IssueDetailLoaderWorker: {error_message}")
        
    def _show_attachments_dialog(self):
        """Show the attachments management dialog."""
        try:
            # Get or create attachment controller
            from controllers.attachment_controller import AttachmentController
            
            # First try to get the main controller's attachment controller (preferred)
            main_controller = None
            from PyQt6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'controller') and hasattr(widget.controller, 'attachment_controller'):
                    main_controller = widget.controller
                    break
            
            if main_controller and hasattr(main_controller, 'attachment_controller'):
                # Use the main controller's attachment controller
                attachment_controller = main_controller.attachment_controller
                _logger.debug("Using main controller's attachment controller")
            else:
                # Create a new attachment controller as fallback
                _logger.debug("Creating new attachment controller")
                attachment_controller = AttachmentController(
                    self.db_service, 
                    self.jira_service, 
                    None  # No app_settings, not critical
                )
                
            # Show the attachments dialog
            attachment_controller.show_attachments_dialog(self.jira_key, parent=self.view)
            
        except Exception as e:
            _logger.error(f"Failed to open attachments dialog: {e}", exc_info=True)
            QMessageBox.warning(self.view, "Error", f"Failed to open attachments dialog: {e}")

    def _on_time_history_cell_changed(self, row, column):
        """Handles inline editing of comment and duration in the time history table."""
        table = self.view.time_history_table
        log_id_item = table.item(row, 0)
        if not log_id_item:
            return
        # Retrieve the log_id from the hidden data (store it in the QTableWidgetItem)
        log_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if log_id is None:
            return
        if column == 2:  # Comment
            new_comment = table.item(row, column).text()
            self.db_service.update_worklog_comment(log_id, new_comment)
        elif column == 1:  # Duration
            new_duration_str = table.item(row, column).text()
            # Parse duration in format "Xh Ym"
            import re
            match = re.match(r"(\d+)h\s*(\d+)m", new_duration_str)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                new_duration = hours * 3600 + minutes * 60
                self.db_service.update_worklog_duration(log_id, new_duration)

    def _format_time(self, total_seconds):
        """Formats the time in HH:MM:SS."""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def _create_or_update_auto_note(self):
        """Create or update the auto-generated note with issue details. Now with version tracking."""
        if not self._issue_data:
            return
            
        import hashlib
        import json
        from datetime import datetime
            
        fields = self._issue_data.get('fields', {})
        
        # Build the note content
        content_lines = []
        content_lines.append(f"# {fields.get('summary', 'No Summary')}")
        content_lines.append("")
        content_lines.append("## Issue Information")
        content_lines.append(f"- **Key**: {self.jira_key}")
        content_lines.append(f"- **Type**: {fields.get('issuetype', {}).get('name', 'N/A')}")
        content_lines.append(f"- **Status**: {fields.get('status', {}).get('name', 'N/A')}")
        content_lines.append(f"- **Priority**: {fields.get('priority', {}).get('name', 'N/A')}")
        content_lines.append(f"- **Assignee**: {fields.get('assignee', {}).get('displayName', 'Unassigned')}")
        
        # Add reporter if available
        reporter = fields.get('reporter', {}).get('displayName')
        if reporter:
            content_lines.append(f"- **Reporter**: {reporter}")
        
        # Add created/updated dates if available (converted to local time)
        created = fields.get('created')
        if created:
            try:
                # Parse the UTC datetime and convert to local time
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                local_dt = dt.astimezone()  # Senza argomenti, astimezone converte al fuso orario locale
                
                # Format for display with local timezone
                content_lines.append(f"- **Created**: {local_dt.strftime('%d %b %Y at %H:%M')}")
            except:
                pass
                
        updated = fields.get('updated')
        if updated:
            try:
                # Parse the UTC datetime and convert to local time
                dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                local_dt = dt.astimezone()  # Senza argomenti, astimezone converte al fuso orario locale
                
                # Format for display with local timezone
                content_lines.append(f"- **Updated**: {local_dt.strftime('%d %b %Y at %H:%M')}")
            except:
                pass
        
        content_lines.append("")
        content_lines.append("## Description")
        description = fields.get('description', 'No description.')
        if description:
            # Convert Jira markup to basic markdown
            description_md = description.replace('{code}', '```').replace('{code}', '```')
            content_lines.append(description_md)
        else:
            content_lines.append("No description available.")
        
        content_lines.append("")
        content_lines.append("## Links")
        content_lines.append("*Loading issue links...*")
        
        # Create the content without hash for comparison
        content = "\n".join(content_lines)
        auto_note_title = "Auto: Issue Details"
        
        # Check if auto note already exists
        existing_notes = self.db_service.get_notes_by_jira_key(self.jira_key)
        
        # Separate the main note and versioned notes
        main_note = None
        versioned_notes = []
        
        for note in existing_notes:
            if note['title'] == auto_note_title:
                main_note = note
            elif note['title'].startswith("Auto: Issue Details v"):
                versioned_notes.append(note)
        
        # Sort versioned notes by version number (highest first)
        def get_version(note):
            try:
                return int(note['title'].split("v")[1])
            except:
                return 0
                
        versioned_notes.sort(key=get_version, reverse=True)
        
        # Function to normalize content for comparison - make it less sensitive to whitespace
        # and other formatting differences
        def normalize_content(content_text):
            if not content_text:
                return ""
                
            # Remove any hidden hash comments
            if "<!-- Issue data hash: " in content_text:
                content_text = content_text.split("<!-- Issue data hash: ")[0]
                
            # Extract only the significant content
            # This focuses on extracting only key information for comparison:
            # - Summary
            # - Issue Key
            # - Type
            # - Status
            # - Priority
            # - Assignee
            # - Description (without caring about whitespace)
            result = {}
            
            # Extract Summary (first heading)
            import re
            summary_match = re.search(r'#\s*(.*?)(?=\n|$)', content_text)
            if summary_match:
                result['summary'] = summary_match.group(1).strip()
            
            # Extract Key, Type, Status, Priority, Assignee
            for field in ['Key', 'Type', 'Status', 'Priority', 'Assignee']:
                pattern = r'\*\*' + field + r'\*\*:\s*(.*?)(?=\n|$)'
                match = re.search(pattern, content_text)
                if match:
                    result[field.lower()] = match.group(1).strip()
            
            # Extract Description (normalize whitespace)
            desc_pattern = r'## Description\s*(.*?)(?=\n##|\Z)'
            desc_match = re.search(desc_pattern, content_text, re.DOTALL)
            if desc_match:
                # Normalize whitespace in description
                desc = desc_match.group(1).strip()
                # Remove all whitespace to make comparison less sensitive
                desc = re.sub(r'\s+', '', desc)
                result['description'] = desc
                
            return result
            
        # First check if the main note exists
        if main_note:
            # Compare content using normalized values
            main_content_norm = normalize_content(main_note['content'])
            new_content_norm = normalize_content(content)
            
            # Check if the significant parts are the same
            significant_changes = False
            
            # Compare all extracted fields
            for key in set(main_content_norm.keys()) | set(new_content_norm.keys()):
                main_value = main_content_norm.get(key, '')
                new_value = new_content_norm.get(key, '')
                
                # If values are different for any key field, consider it a significant change
                if main_value != new_value:
                    significant_changes = True
                    break
            
            if not significant_changes:
                # No significant changes detected, update timestamp but don't create new version
                self.db_service.update_note(main_note['id'], content=content)
                return
            else:
                # Significant changes detected, create a new version
                version = 1
                if versioned_notes:
                    version = get_version(versioned_notes[0]) + 1
                
                # Create a new versioned note
                new_title = f"Auto: Issue Details v{version}"
                self.db_service.create_note(
                    jira_key=self.jira_key,
                    title=new_title,
                    content=content,
                    tags="auto-generated,issue-details,version-history"
                )
                
                # Also update the main note with the latest content
                self.db_service.update_note(main_note['id'], content=content)
                return
        elif versioned_notes:
            # No main note, but we have versioned notes
            # Create a new main note with the current content
            self.db_service.create_note(
                jira_key=self.jira_key,
                title=auto_note_title,
                content=content,
                tags="auto-generated,issue-details"
            )
            return
        else:
            # No notes exist at all, create the first one
            self.db_service.create_note(
                jira_key=self.jira_key,
                title=auto_note_title,
                content=content,
                tags="auto-generated,issue-details"
            )
    
    def populate_priority_combo(self, priorities=None):
        """Populate the priority dropdown with available priorities."""
        # Clear existing items
        self.view.priority_combo.clear()
        
        if not priorities:
            # If no priorities provided, get them from the Jira service
            try:
                if self.jira_service and self.jira_service.is_connected():
                    priorities = self.jira_service.get_priorities()
                else:
                    # Default priorities when offline
                    priorities = [
                        {"id": "1", "name": "Highest"},
                        {"id": "2", "name": "High"},
                        {"id": "3", "name": "Medium"},
                        {"id": "4", "name": "Low"},
                        {"id": "5", "name": "Lowest"}
                    ]
            except Exception as e:
                print(f"Error getting priorities: {e}")
                priorities = []
        
        # Add priorities to combo box
        for priority in priorities:
            self.view.priority_combo.addItem(priority.get("name", ""), priority.get("id", ""))
        
        # Set current priority if issue data is loaded
        if self._issue_data:
            current_priority = self._issue_data.get("fields", {}).get("priority", {})
            current_id = current_priority.get("id", "")
            
            # Find index with this id
            for i in range(self.view.priority_combo.count()):
                if self.view.priority_combo.itemData(i) == current_id:
                    self.view.priority_combo.setCurrentIndex(i)
                    break
    
    def _update_issue_priority(self):
        """Update the priority of the issue."""
        if not self.view.priority_combo.currentData():
            return
            
        new_priority_id = self.view.priority_combo.currentData()
        new_priority_name = self.view.priority_combo.currentText()
        
        # Get priority configuration controller
        from controllers.priority_config_controller import PriorityConfigController
        priority_controller = PriorityConfigController(self.db_service, self.jira_service)
        
        # Update priority
        success = priority_controller.update_priority(self.jira_key, new_priority_id)
        if success:
            # Update local issue data
            if self._issue_data and "fields" in self._issue_data:
                self._issue_data["fields"]["priority"] = {
                    "id": new_priority_id,
                    "name": new_priority_name
                }
    
    def _show_priority_config(self):
        """Show the priority configuration dialog."""
        from controllers.priority_config_controller import PriorityConfigController
        priority_controller = PriorityConfigController(self.db_service, self.jira_service)
        
        # Open priority configuration dialog
        priority_controller.open_priority_config_dialog(parent=self.view)
        
        # After config dialog is closed, refresh priorities
        self.populate_priority_combo()
    
    def populate_priority_combo(self, priorities=None):
        """Populate the priority combo box with available priorities from Jira."""
        if not priorities:
            # If not provided, try to get them from the priority controller
            if hasattr(self, 'priority_controller') and self.priority_controller:
                priorities = self.priority_controller.get_available_priorities()
            else:
                # Default priorities if no controller available
                priorities = [
                    {"id": "1", "name": "Highest"},
                    {"id": "2", "name": "High"},
                    {"id": "3", "name": "Medium"},
                    {"id": "4", "name": "Low"},
                    {"id": "5", "name": "Lowest"}
                ]
        
        # Clear existing items
        self.view.priority_combo.clear()
        
        # Add priorities to the combo box
        for priority in priorities:
            self.view.priority_combo.addItem(priority.get("name", "Unknown"), priority.get("id"))
    
    def _update_issue_priority(self, index):
        """Handle priority selection change."""
        if index < 0:
            return
            
        priority_id = self.view.priority_combo.itemData(index)
        priority_name = self.view.priority_combo.itemText(index)
        
        if not priority_id:
            return
            
        # Get or create priority controller if needed
        if not self.priority_controller:
            from controllers.priority_config_controller import PriorityConfigController
            self.priority_controller = PriorityConfigController(self.db_service, self.jira_service)
        
        # Update priority
        self.priority_controller.update_priority(self.jira_key, priority_id)
    
    def _show_priority_config(self):
        """Show the priority configuration dialog."""
        # Get or create priority controller if needed
        if not self.priority_controller:
            from controllers.priority_config_controller import PriorityConfigController
            self.priority_controller = PriorityConfigController(self.db_service, self.jira_service)
        
        # Open the configuration dialog
        self.priority_controller.open_priority_config_dialog(self.view)
        
        # Refresh the priority combo box after configuration
        priorities = self.priority_controller.get_available_priorities()
        self.populate_priority_combo(priorities)
    
    def _update_auto_note_with_links(self, links_tree):
        """Update the auto-generated note with links information."""
        auto_note_title = "Auto: Issue Details"
        existing_notes = self.db_service.get_notes_by_jira_key(self.jira_key)
        
        # Find the auto note
        auto_note = None
        for note in existing_notes:
            if note['title'] == auto_note_title:
                auto_note = note
                break
        
        if not auto_note:
            return
            
        # Build links section
        links_lines = []
        if links_tree:
            for root_data in links_tree:
                children = root_data.get('children', [])
                if children:
                    links_lines.append("")
                    links_lines.append("### Issue Links")
                    for child in children:
                        link_type = child.get('link_type', 'links to')
                        direction = child.get('direction', 'outward')
                        key = child.get('key', 'Unknown')
                        summary = child.get('summary', 'No summary')
                        status = child.get('status', 'Unknown')
                        
                        # Format based on direction
                        if direction == 'outward':
                            links_lines.append(f"- **{link_type}** [{key}]({summary}) - {status}")
                        elif direction == 'inward':
                            links_lines.append(f"- **{link_type}** [{key}]({summary}) - {status}")
                        else:
                            links_lines.append(f"- [{key}]({summary}) - {status}")
                else:
                    links_lines.append("")
                    links_lines.append("*No linked issues found.*")
        else:
            links_lines.append("")
            links_lines.append("*No linked issues found.*")
        
        links_content = "\n".join(links_lines)
        
        # Update the note content by replacing the links section
        current_content = auto_note['content']
        # Find and replace the "## Links" section
        import re
        links_pattern = r"(## Links\n).*?(\n\n##|\n*$)"
        replacement = r"\1" + links_content + r"\2"
        
        # If no next section, just append
        if "## Links" in current_content:
            new_content = re.sub(links_pattern, replacement, current_content, flags=re.DOTALL)
        else:
            new_content = current_content + links_content
        
        self.db_service.update_note(auto_note['id'], content=new_content)


