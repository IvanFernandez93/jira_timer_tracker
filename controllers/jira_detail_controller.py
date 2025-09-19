from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QDateTime, QUrl, Qt, QThread, pyqtSlot
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QListWidgetItem, QTextEdit, QInputDialog, QLabel
from PyQt6.QtGui import QDesktopServices, QPixmap
import json
import math
from datetime import datetime
import os
import requests
import markdown

from services.jira_service import JiraService
from views.markdown_editor import MarkdownEditor

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
    
    def cancel(self):
        """Cancel the download."""
        self.is_cancelled = True
    
    def run(self):
        """Download the attachment."""
        try:
            if self.is_cancelled:
                return
                
            filename = self.attachment_data.get('filename')
            file_url = self.attachment_data.get('content')
            
            if not file_url:
                self.download_error.emit(self.attachment_widget, "URL mancante")
                return
            
            # Update status to downloading
            self.progress_updated.emit(self.attachment_widget, 0)
            
            # Get the attachment content with progress tracking
            response = self.jira_service.jira._session.get(file_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            # Determine save path
            from PyQt6.QtCore import QStandardPaths
            download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            save_path = os.path.join(download_dir, filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            downloaded_size = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        f.close()
                        os.remove(save_path)  # Clean up partial download
                        return
                        
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_updated.emit(self.attachment_widget, progress)
            
            self.download_finished.emit(self.attachment_widget, save_path)
            
        except Exception as e:
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
    
    def cancel(self):
        """Cancel the thumbnail download."""
        self.is_cancelled = True
    
    def run(self):
        """Download image and create thumbnail."""
        try:
            if self.is_cancelled:
                return
                
            filename = self.attachment_data.get('filename')
            file_url = self.attachment_data.get('content')
            
            if not file_url:
                self.thumbnail_error.emit(self.attachment_widget, "URL mancante")
                return
            
            # Download the image
            response = self.jira_service.jira._session.get(file_url, stream=True)
            response.raise_for_status()
            
            # Read image data
            image_data = response.content
            
            if self.is_cancelled:
                return
            
            # Create QPixmap from image data
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import QBuffer, QIODevice
            
            pixmap = QPixmap()
            buffer = QBuffer()
            buffer.setData(image_data)
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            
            if pixmap.loadFromData(image_data):
                # Scale to thumbnail size (64x64) maintaining aspect ratio
                thumbnail = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
                self.thumbnail_ready.emit(self.attachment_widget, thumbnail)
            else:
                self.thumbnail_error.emit(self.attachment_widget, "Impossibile caricare l'immagine")
            
        except Exception as e:
            self.thumbnail_error.emit(self.attachment_widget, str(e))


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

        self._issue_data = None
        self._attachments_data = []
        self._attachment_widgets = []
        self._download_workers = []
        self._thumbnail_workers = []
        self._active_note_editor = None
        self._current_note_title = None # Track the title of the active note
        
        self._connect_signals()
        self._setup_autosave_timer() # Setup the timer once
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_display)
        self.timer.setInterval(1000) # 1 second

        self.is_running = False
        self.total_seconds_tracked = self.db_service.get_local_time(self.jira_key)
        self._update_display() # Show initial time

    def _connect_signals(self):
        self.view.start_pause_btn.clicked.connect(self._toggle_timer)
        self.view.stop_btn.clicked.connect(self._stop_timer)
        self.view.add_time_btn.clicked.connect(self._add_time_manually)
        
        # Notification button
        self.view.notification_btn.clicked.connect(self._toggle_notification_subscription)
        
        # Comment signals
        self.view.add_comment_btn.clicked.connect(self._add_comment)

        # Attachment signals
        self.view.upload_attachment_btn.clicked.connect(self._upload_attachment)
        self.view.download_selected_btn.clicked.connect(self._download_selected_attachments)
        self.view.download_all_btn.clicked.connect(self._download_all_attachments)

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
        Loads all necessary data from Jira and the local DB.
        This should be run in a background thread in a real app.
        """
        try:
            # Record this view in history
            self.db_service.add_view_history(self.jira_key)
            
            # 1. Fetch issue data from Jira
            self._issue_data = self.jira_service.get_issue(self.jira_key)
            
            # 2. Populate the view with the data
            self._populate_details()
            self._populate_comments()
            self._populate_attachments()
            self._populate_annotations()
            self._load_time_history()
            
            # 3. Update notification subscription button
            self._update_notification_button()

        except Exception as e:
            self.view.details_browser.setText(f"<b>Error loading issue data:</b><br>{e}")
            print(f"Error in JiraDetailController: {e}")

    def _populate_details(self):
        """Populates the 'Details' tab."""
        if not self._issue_data: return
        
        fields = self._issue_data.get('fields', {})
        
        # Use raw description field for markdown conversion
        description_md = fields.get('description', 'No description.')
        # Convert Jira's markup to HTML
        description_html = markdown.markdown(description_md or "")

        # Build an HTML string for the details view
        html = f"""
            <h2>{fields.get('summary', 'No Summary')}</h2>
            <hr>
            <p><b>Type:</b> {fields.get('issuetype', {}).get('name', 'N/A')}</p>
            <p><b>Status:</b> {fields.get('status', {}).get('name', 'N/A')}</p>
            <p><b>Priority:</b> {fields.get('priority', {}).get('name', 'N/A')}</p>
            <p><b>Assignee:</b> {fields.get('assignee', {}).get('displayName', 'Unassigned')}</p>
            <hr>
            <h3>Description:</h3>
            {description_html}
        """
        self.view.details_browser.setHtml(html)

    def _populate_comments(self):
        """Populates the 'Comments' tab with formatted HTML."""
        if not self._issue_data: return

        comments = self._issue_data.get('renderedFields', {}).get('comment', {}).get('comments', [])
        
        if not comments:
            self.view.comments_browser.setHtml("<p><i>No comments on this issue.</i></p>")
            return
            
        html_parts = []
        for comment in comments:
            author = comment.get('author', {}).get('displayName', 'Unknown Author')
            # Use 'updated' for more accuracy, fallback to 'created'
            timestamp_str = comment.get('updated', comment.get('created', ''))
            
            # Parse the timestamp and format it nicely
            try:
                dt_object = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                formatted_date = dt_object.strftime('%d %b %Y at %H:%M')
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
        app_settings = AppSettings()
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
        
        # Create widgets for each attachment and start downloads/thumbnails
        for attachment in self._attachments_data:
            filename = attachment.get('filename', 'Unknown')
            size_kb = attachment.get('size', 0) / 1024
            
            # Create attachment widget
            attachment_widget = self.view.create_attachment_widget(filename, size_kb, attachment)
            self.view.attachments_layout.addWidget(attachment_widget)
            self._attachment_widgets.append(attachment_widget)
            
            # Connect download button
            attachment_widget.download_btn.clicked.connect(
                lambda checked, widget=attachment_widget: self._download_single_attachment(widget)
            )
            
            # Check if this is an image file for thumbnail generation
            file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
            
            if file_extension in image_extensions:
                # Start thumbnail download for images
                self._start_thumbnail_download(attachment_widget)
            else:
                # Start automatic download for non-image files
                self._start_attachment_download(attachment_widget)

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
        
        if not annotations:
            self._add_new_note_tab(title="Note 1")
        else:
            for title, content in annotations:
                self._create_note_tab(title, content)
        
        # Set up the autosave timer for the first tab
        if self.view.notes_tab_widget.count() > 0:
            self._handle_note_tab_change(0)

    def _create_note_tab(self, title, content):
        """Helper to create a new tab with a markdown editor."""
        editor = MarkdownEditor()
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

        # Create a new empty note in the database first
        self.db_service.save_annotation(self.jira_key, title, "")

        # Create the editor and add the tab
        editor = self._create_note_tab(title, "")
        
        # Switch to the new tab, which will trigger _handle_note_tab_change
        index = self.view.notes_tab_widget.indexOf(editor)
        self.view.notes_tab_widget.setCurrentIndex(index)

        # Explicitly set the current note title and connect the auto-save timer
        self._current_note_title = title
        if hasattr(self, 'autosave_timer'):
            self._active_note_editor = editor
            self._active_note_editor.textChanged.connect(self.autosave_timer.start)
            # Also save immediately on text change to avoid data loss
            self._active_note_editor.textChanged.connect(self._save_current_note)

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
        # Disconnect the textChanged signal from the old editor to prevent auto-saving an empty string
        if self._active_note_editor and hasattr(self, 'autosave_timer'):
            try:
                self._active_note_editor.textChanged.disconnect(self.autosave_timer.start)
            except TypeError:
                pass # Was not connected

        # Save the content of the note that was active before the switch
        self._save_current_note()
        
        if index < 0:
            self._active_note_editor = None
            return

        current_editor = self.view.notes_tab_widget.widget(index)
        if isinstance(current_editor, (QTextEdit, MarkdownEditor)):
            self._active_note_editor = current_editor
            
            # Update the current note title
            self._current_note_title = self.view.notes_tab_widget.tabText(index)

            # Only load content from DB if the editor is empty (i.e., just created)
            if self._active_note_editor.toPlainText().strip() == "":
                annotations = self.db_service.get_annotations(self.jira_key)
                for ann_title, ann_content in annotations:
                    if ann_title == self._current_note_title:
                        self._active_note_editor.blockSignals(True)
                        self._active_note_editor.setMarkdown(ann_content)
                        self._active_note_editor.blockSignals(False)
                        break

            # Connect the textChanged signal to the new editor's timer and immediate save
            if hasattr(self, 'autosave_timer'):
                self._active_note_editor.textChanged.connect(self.autosave_timer.start)
                self._active_note_editor.textChanged.connect(self._save_current_note)

    def _setup_autosave_timer(self):
        """Sets up a single timer for auto-saving the active annotation."""
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(3000) # 3 seconds
        self.autosave_timer.timeout.connect(self._save_current_note)

    def _save_current_note(self):
        """Saves the content of the currently active annotation editor."""
        if not self._active_note_editor or not self._current_note_title:
            return
            
        content = self._active_note_editor.toMarkdown()
        self.db_service.save_annotation(self.jira_key, self._current_note_title, content)

    def _on_close(self, event):
        """Handler to be called when the window is closed."""
        self._save_current_note() # Ensure last active note is saved
        
        # Cancel all ongoing downloads
        for worker in self._download_workers:
            worker.cancel()
        
        # Cancel all thumbnail downloads
        for worker in self._thumbnail_workers:
            worker.cancel()
        
        # Wait for all workers to finish
        for worker in self._download_workers:
            worker.wait()
        
        for worker in self._thumbnail_workers:
            worker.wait()
        
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
            
            # Check if auto-sync is enabled
            from services.app_settings import AppSettings
            app_settings = AppSettings()
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
            app_settings = AppSettings()
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
            # Format start time
            try:
                dt_object = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_date = dt_object.strftime('%d %b %Y %H:%M')
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
    
    def _format_time(self, total_seconds):
        """Formats the time in HH:MM:SS."""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
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


