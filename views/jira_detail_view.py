from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QTextEdit, QListWidget, QTextBrowser, QSplitter,
                             QTabBar, QScrollArea, QProgressBar, QFrame, QDialog, QGridLayout,
                             QSizePolicy, QToolButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence
# QShortcut may be provided under QtWidgets or QtGui depending on PyQt6 build
try:
    from PyQt6.QtWidgets import QShortcut
except Exception:
    from PyQt6.QtGui import QShortcut


class EmojiPickerDialog(QDialog):
    """Simple emoji picker dialog that returns the selected emoji on accept."""
    def __init__(self, parent=None, emojis=None):
        super().__init__(parent)
        self.setWindowTitle('Scegli emoticon')
        self.setModal(True)
        self.selected = None
        emojis = emojis or ['🙂','😀','😂','🥳','👍','👎','🎯','🚀','🔥','😅','😢','😡','❤️','💡','📌']
        layout = QGridLayout(self)
        cols = 8
        for i, e in enumerate(emojis):
            btn = QPushButton(e)
            btn.setFixedSize(36, 36)
            btn.clicked.connect(lambda _checked, ch=e: self._choose(ch))
            r = i // cols
            c = i % cols
            layout.addWidget(btn, r, c)

    def _choose(self, ch):
        self.selected = ch
        self.accept()


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

        # If parent has 'always on top', inherit that flag so this window also stays on top
        try:
            if parent is not None and parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
                self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        except Exception:
            pass

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
        self.notification_btn.setFixedHeight(28)
        # simple visual for checked state
        self.notification_btn.setStyleSheet(
            'padding:4px; border-radius:4px; background:#fff; border:1px solid #ddd;'
            'QPushButton:checked { background-color: #dff0d8; border-color:#b2d8a7 }'
        )
        
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

        # Small toolbar: use QToolButton for better toolbar appearance
        toolbar_layout = QHBoxLayout()

        # Emoji picker button (single control)
        self.emoji_picker_btn = QToolButton()
        self.emoji_picker_btn.setText('😀')
        self.emoji_picker_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.emoji_picker_btn.setFixedSize(36, 36)
        self.emoji_picker_btn.setToolTip('Apri selettore emoticon')
        self.emoji_picker_btn.clicked.connect(self._open_emoji_picker)
        toolbar_layout.addWidget(self.emoji_picker_btn)

        # Formatting tool button factory
        def make_toolbutton(text, tooltip, callback, width=36):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tooltip)
            b.setFixedSize(width, 28)
            b.setAutoRaise(True)
            b.setStyleSheet('font-weight:600; border:1px solid #e6e6e6; background:#fafafa;')
            try:
                b.clicked.connect(callback)
            except Exception:
                pass
            return b
        # Expose toolbar buttons on self so controllers can bind actions
        self.bold_btn = make_toolbutton('B', 'Grassetto (Ctrl+B)', lambda: self._wrap_selection('**','**'))
        self.italic_btn = make_toolbutton('I', 'Corsivo (Ctrl+I)', lambda: self._wrap_selection('*','*'))
        # Strikethrough / underline equivalent
        self.underline_btn = make_toolbutton('S', 'Barrato (Ctrl+U)', lambda: self._wrap_selection('~~','~~'))
        self.code_btn = make_toolbutton('</>', 'Codice', lambda: self._wrap_selection('`','`'), width=48)
        self.bullet_btn = make_toolbutton('•', 'Elenco puntato', lambda: self._bullet_list())
        # Numbered list (connect after helper defined)
        self.number_btn = make_toolbutton('1.', 'Elenco numerato', lambda: None)
        self.h1_btn = make_toolbutton('H1', 'Titolo H1', lambda: self._prefix_line('# '))
        self.h2_btn = make_toolbutton('H2', 'Titolo H2', lambda: self._prefix_line('## '))
        self.h3_btn = make_toolbutton('H3', 'Titolo H3', lambda: self._prefix_line('### '))
        # Link insertion (connect after helper defined)
        self.link_btn = make_toolbutton('🔗', 'Inserisci Link', lambda: None, width=36)
        # Preview toggle (connect after helper defined)
        self.preview_btn = make_toolbutton('👁️', 'Toggle Preview', lambda: None, width=36)

        for b in (self.bold_btn, self.italic_btn, self.underline_btn, self.code_btn,
                  self.bullet_btn, self.number_btn, self.link_btn, self.preview_btn,
                  self.h1_btn, self.h2_btn, self.h3_btn):
            toolbar_layout.addWidget(b)

        toolbar_layout.addStretch()
        annotations_layout.addLayout(toolbar_layout)

        # Notes tab widget (left-side tabs)
        self.notes_tab_widget = QTabWidget()
        self.notes_tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        self.notes_tab_widget.setMovable(True)
        self.notes_tab_widget.setTabsClosable(True)
        self.notes_tab_widget.tabCloseRequested.connect(lambda idx: self._close_note(idx))

        # Configure tabbar behaviour for readability
        try:
            self.notes_tab_widget.tabBar().setExpanding(False)
            self.notes_tab_widget.tabBar().setUsesScrollButtons(True)
        except Exception:
            pass

        annotations_layout.addWidget(self.notes_tab_widget)

        # Add button for new notes
        self.add_note_btn = QPushButton("+ New Note")
        self.add_note_btn.setToolTip("Crea una nuova nota personale")
        self.add_note_btn.setStyleSheet("font-size: 14px; padding: 6px 10px;")
        self.add_note_btn.clicked.connect(lambda: self._add_note())

        annotations_layout.addWidget(self.add_note_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Install the annotations tab
        self.tab_widget.addTab(self.annotations_tab, "Personal Notes")

        # --- Helper functions attached to the instance so they are available in other scopes ---
        def _make_note_widget(title: str = None):
            w = QWidget()
            l = QVBoxLayout(w)
            editor = QTextEdit()
            editor.setPlaceholderText("Your private notes (Markdown supported)...")
            editor.setStyleSheet("font-size: 14px;")
            editor.setAcceptRichText(False)
            # expose editor for external access
            w.editor = editor
            l.addWidget(editor)
            return w

        def _add_note():
            count = self.notes_tab_widget.count() + 1
            title = f"Note {count}"
            w = _make_note_widget(title)
            idx = self.notes_tab_widget.addTab(w, title)
            self.notes_tab_widget.setCurrentIndex(idx)
            # focus editor
            try:
                w.editor.setFocus()
            except Exception:
                pass

        def _close_note(idx: int):
            try:
                self.notes_tab_widget.removeTab(idx)
            except Exception:
                pass

        def _insert_emoji(ch: str):
            cur = self.notes_tab_widget.currentWidget()
            if cur and hasattr(cur, 'editor'):
                try:
                    ed = cur.editor
                    tc = ed.textCursor()
                    tc.insertText(ch)
                    ed.setTextCursor(tc)
                    ed.setFocus()
                except Exception:
                    pass

        def _wrap_selection(prefix: str, suffix: str):
            cur = self.notes_tab_widget.currentWidget()
            if cur and hasattr(cur, 'editor'):
                try:
                    ed = cur.editor
                    tc = ed.textCursor()
                    if tc.hasSelection():
                        sel = tc.selectedText()
                        tc.insertText(f"{prefix}{sel}{suffix}")
                    else:
                        # insert both and place cursor between
                        tc.insertText(f"{prefix}{suffix}")
                        # move cursor back len(suffix) positions
                        for _ in range(len(suffix)):
                            tc.movePosition(tc.MoveOperation.Left)
                        ed.setTextCursor(tc)
                    ed.setFocus()
                except Exception:
                    pass

        # bind helpers to self so they can be called from other methods or callbacks
        self._make_note_widget = _make_note_widget
        self._add_note = _add_note
        self._close_note = _close_note
        self._insert_emoji = _insert_emoji
        self._wrap_selection = _wrap_selection

        def _numbered_list():
            cur = self.notes_tab_widget.currentWidget()
            if cur and hasattr(cur, 'editor'):
                ed = cur.editor
                tc = ed.textCursor()
                if tc.hasSelection():
                    sel = tc.selection().toPlainText() if hasattr(tc, 'selection') else tc.selectedText()
                    lines = sel.split('\n')
                    new = '\n'.join([(f"1. {ln}" if not ln.strip().startswith('1.') else ln) for ln in lines])
                    tc.insertText(new)
                else:
                    tc.insertText('1. ')
                    ed.setTextCursor(tc)
                ed.setFocus()

        def _insert_link():
            cur = self.notes_tab_widget.currentWidget()
            if cur and hasattr(cur, 'editor'):
                ed = cur.editor
                tc = ed.textCursor()
                if tc.hasSelection():
                    text = tc.selectedText()
                else:
                    text = 'Link Text'
                tc.insertText(f'[{text}](URL)')
                ed.setTextCursor(tc)
                ed.setFocus()

        def _toggle_preview():
            # If the active editor is a MarkdownEditor instance, call its toggle_preview
            cur = self.notes_tab_widget.currentWidget()
            if cur and hasattr(cur, 'editor'):
                ed = cur.editor
                # Some editors may implement toggle_preview() or toggle_preview-like behavior
                if hasattr(ed, 'toggle_preview'):
                    try:
                        ed.toggle_preview()
                    except Exception:
                        pass
        # Connect buttons that were placeholder-connected earlier
        try:
            self.number_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            self.link_btn.clicked.disconnect()
        except Exception:
            pass
        try:
            self.preview_btn.clicked.disconnect()
        except Exception:
            pass

        try:
            self.number_btn.clicked.connect(_numbered_list)
            self.link_btn.clicked.connect(_insert_link)
            self.preview_btn.clicked.connect(_toggle_preview)
        except Exception:
            pass
        # create an initial empty note
        try:
            self._add_note()
        except Exception:
            pass

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

    def mousePressEvent(self, event):
        # ensure window is raised and activated when clicked anywhere inside
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        return super().mousePressEvent(event)

    def focusInEvent(self, event):
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        return super().focusInEvent(event)

    def _open_emoji_picker(self):
        dlg = EmojiPickerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and getattr(dlg, 'selected', None):
            ch = dlg.selected
            try:
                self._insert_emoji(ch)
            except Exception:
                pass

    def _bullet_list(self):
        cur = self.notes_tab_widget.currentWidget()
        if cur and hasattr(cur, 'editor'):
            ed = cur.editor
            tc = ed.textCursor()
            if tc.hasSelection():
                sel = tc.selection().toPlainText() if hasattr(tc, 'selection') else tc.selectedText()
                lines = sel.split('\n')
                new = '\n'.join([('- ' + ln if not ln.strip().startswith('-') else ln) for ln in lines])
                tc.insertText(new)
            else:
                tc.insertText('- ')
                ed.setTextCursor(tc)
            ed.setFocus()

    def _prefix_line(self, prefix: str):
        cur = self.notes_tab_widget.currentWidget()
        if cur and hasattr(cur, 'editor'):
            ed = cur.editor
            tc = ed.textCursor()
            if tc.hasSelection():
                sel = tc.selection().toPlainText() if hasattr(tc, 'selection') else tc.selectedText()
                lines = sel.split('\n')
                new = '\n'.join([prefix + ln for ln in lines])
                tc.insertText(new)
            else:
                tc.insertText(prefix)
                ed.setTextCursor(tc)
            ed.setFocus()
