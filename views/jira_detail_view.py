from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QTextEdit, QListWidget, QTextBrowser, QSplitter,
                             QTabBar, QScrollArea, QProgressBar, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class JiraDetailView(QWidget):
    """
    A window to display the full details of a single Jira issue.
    Fulfills requirement 2.4.
    """
    def __init__(self, jira_key, parent=None):
        super().__init__(parent)
        self.jira_key = jira_key
        self.setWindowTitle(f"Detail - {jira_key}")
        self.setGeometry(150, 150, 900, 700)

        main_layout = QVBoxLayout(self)

        # 1. Header (Req 2.4.1)
        header_layout = QHBoxLayout()
        self.jira_key_label = QLabel(jira_key)
        self.jira_key_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        
        # Add notification subscription toggle button
        self.notification_btn = QPushButton()
        self.notification_btn.setCheckable(True)
        self.notification_btn.setText("🔔 Notifiche")
        self.notification_btn.setToolTip("Attiva/disattiva le notifiche per questo ticket")
        
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        header_layout.addWidget(self.jira_key_label)
        header_layout.addWidget(self.notification_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.timer_label)
        main_layout.addLayout(header_layout)

        # 2. Timer Controls (Req 2.4.2)
        controls_layout = QHBoxLayout()
        self.start_pause_btn = QPushButton("Start")
        self.start_pause_btn.setToolTip("Avvia o metti in pausa il timer")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setToolTip("Ferma il timer e registra il tempo trascorso")
        self.add_time_btn = QPushButton("Add Time Manually")
        self.add_time_btn.setToolTip("Aggiungi manualmente un tempo di lavoro")
        controls_layout.addStretch()
        controls_layout.addWidget(self.start_pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.add_time_btn)
        main_layout.addLayout(controls_layout)

        # 3. Tabbed Section (Req 2.4.3)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Tab 1: Details (Default)
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        self.details_browser = QTextBrowser() # Renders rich text/HTML
        details_layout.addWidget(self.details_browser)
        self.tab_widget.addTab(self.details_tab, "Details")

        # Tab 2: Comments
        self.comments_tab = QWidget()
        comments_layout = QVBoxLayout(self.comments_tab)
        
        # Use a browser to display formatted comments
        self.comments_browser = QTextBrowser()
        self.comments_browser.setOpenExternalLinks(True)

        # Input area for new comments
        self.new_comment_input = QTextEdit()
        self.new_comment_input.setPlaceholderText("Add a new comment...")
        self.new_comment_input.setFixedHeight(80) # Set a fixed initial height
        self.new_comment_input.setToolTip("Scrivi un nuovo commento")
        self.add_comment_btn = QPushButton("Add Comment")
        self.add_comment_btn.setToolTip("Aggiungi il commento al ticket")

        # Layout for the input area
        new_comment_layout = QHBoxLayout()
        new_comment_layout.addWidget(self.new_comment_input)
        new_comment_layout.addWidget(self.add_comment_btn)

        comments_layout.addWidget(self.comments_browser)
        comments_layout.addLayout(new_comment_layout)

        self.tab_widget.addTab(self.comments_tab, "Comments")

        # Tab 3: Attachments
        self.attachments_tab = QWidget()
        attachments_layout = QVBoxLayout(self.attachments_tab)
        
        # Create a custom widget for each attachment with loading indicator
        self.attachments_scroll_area = QScrollArea()
        self.attachments_scroll_area.setWidgetResizable(True)
        self.attachments_container = QWidget()
        self.attachments_layout = QVBoxLayout(self.attachments_container)
        
        # Add the container to the scroll area
        self.attachments_scroll_area.setWidget(self.attachments_container)
        attachments_layout.addWidget(self.attachments_scroll_area)
        
        # Layout for buttons
        attachment_buttons_layout = QHBoxLayout()
        self.upload_attachment_btn = QPushButton("Upload Attachment")
        self.upload_attachment_btn.setToolTip("Carica un nuovo allegato al ticket")
        self.download_selected_btn = QPushButton("Download Selected")
        self.download_selected_btn.setToolTip("Scarica gli allegati selezionati")
        self.download_all_btn = QPushButton("Download All")
        self.download_all_btn.setToolTip("Scarica tutti gli allegati")
        attachment_buttons_layout.addStretch()
        attachment_buttons_layout.addWidget(self.upload_attachment_btn)
        attachment_buttons_layout.addWidget(self.download_selected_btn)
        attachment_buttons_layout.addWidget(self.download_all_btn)
        
        attachments_layout.addLayout(attachment_buttons_layout)
        self.tab_widget.addTab(self.attachments_tab, "Attachments")

        # Tab 4: Personal Annotations (Req 2.4.3)
        self.annotations_tab = QWidget()
        annotations_layout = QVBoxLayout(self.annotations_tab)
        
        self.notes_tab_widget = QTabWidget()
        self.notes_tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        self.notes_tab_widget.setMovable(True)
        self.notes_tab_widget.setTabsClosable(True)

        # Add button for new notes
        self.add_note_btn = QPushButton("+ New Note")
        self.add_note_btn.setToolTip("Crea una nuova nota personale")
        
        # Allow renaming tabs on double-click
        self.notes_tab_widget.tabBar().setExpanding(False)
        self.notes_tab_widget.tabBar().setUsesScrollButtons(True)

        annotations_layout.addWidget(self.notes_tab_widget)
        annotations_layout.addWidget(self.add_note_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.tab_widget.addTab(self.annotations_tab, "Personal Notes")
        
        # Tab 5: Local Time History
        self.time_history_tab = QWidget()
        time_history_layout = QVBoxLayout(self.time_history_tab)
        
        # Table for displaying time history
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.time_history_table = QTableWidget(0, 4)  # Start with 0 rows and 4 columns
        self.time_history_table.setHorizontalHeaderLabels(["Data", "Durata", "Commento", "Stato Sync"])
        self.time_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.time_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.time_history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.time_history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.time_history_table.setAlternatingRowColors(True)
        self.time_history_table.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        for i in range(4):
            self.time_history_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        self.time_history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Refresh button
        self.refresh_history_btn = QPushButton("Aggiorna")
        self.refresh_history_btn.setToolTip("Aggiorna la cronologia dei tempi registrati")
        
        time_history_layout.addWidget(self.time_history_table)
        time_history_layout.addWidget(self.refresh_history_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.tab_widget.addTab(self.time_history_tab, "Time History")

        self.tab_widget.setCurrentIndex(0) # Default to Details tab

    def create_attachment_widget(self, filename, size_kb, attachment_data):
        """Creates a widget for an attachment with loading indicator and thumbnail preview."""
        # Main container for this attachment
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setLineWidth(1)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Thumbnail/Icon area
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(64, 64)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        
        # Determine file type and set appropriate icon/thumbnail
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
        video_extensions = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']
        audio_extensions = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']
        
        if file_extension in image_extensions:
            # For images, we'll load thumbnail later
            thumbnail_label.setText("🖼️")
            thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #e8f4fd; font-size: 24px;")
        elif file_extension in video_extensions:
            thumbnail_label.setText("🎥")
            thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #ffe8e8; font-size: 24px;")
        elif file_extension in audio_extensions:
            thumbnail_label.setText("🎵")
            thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #e8ffe8; font-size: 24px;")
        else:
            # Default document icon
            thumbnail_label.setText("📄")
            thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9; font-size: 24px;")
        
        layout.addWidget(thumbnail_label)
        
        # File info
        info_layout = QVBoxLayout()
        
        # Filename and size
        filename_label = QLabel(f"<b>{filename}</b> ({size_kb:.1f} KB)")
        info_layout.addWidget(filename_label)
        
        # Progress bar (initially hidden)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setVisible(False)
        progress_bar.setFixedHeight(15)
        info_layout.addWidget(progress_bar)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Download button
        download_btn = QPushButton("Download")
        download_btn.setFixedWidth(80)
        layout.addWidget(download_btn)
        
        # Store references for later use
        container.attachment_data = attachment_data
        container.filename = filename
        container.thumbnail_label = thumbnail_label
        container.status_label = thumbnail_label  # Reuse for status (will be updated)
        container.progress_bar = progress_bar
        container.download_btn = download_btn
        
        return container
