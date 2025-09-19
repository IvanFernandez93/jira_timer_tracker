from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QToolBar, 
    QApplication, QTextBrowser, QStackedWidget
)
from PyQt6.QtGui import QTextCursor, QFont, QAction, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import ToolButton, FluentIcon as FIF
import markdown

class MarkdownEditor(QWidget):
    """
    A custom widget that provides a QTextEdit with Markdown formatting toolbar.
    Supports bold, italic, underline, and other basic formatting options.
    """
    
    textChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_mode = 0  # 0: edit only, 1: edit + preview side by side
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create toolbar
        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)
        
        # Create main container
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create stacked widget for different modes
        self.stacked_widget = QStackedWidget()
        
        # Create combined view (editor + preview side by side)
        self.combined_widget = QWidget()
        combined_layout = QHBoxLayout(self.combined_widget)
        combined_layout.setContentsMargins(0, 0, 0, 0)
        combined_layout.setSpacing(5)
        
        # Editor on the left
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)  # We want plain text with Markdown
        combined_layout.addWidget(self.editor)
        
        # Preview on the right
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setReadOnly(True)  # Preview is read-only
        combined_layout.addWidget(self.preview)
        
        # Add widgets to stacked widget
        self.stacked_widget.addWidget(self.editor)  # Index 0: Edit only
        self.stacked_widget.addWidget(self.combined_widget)  # Index 1: Edit + Preview side by side
        
        main_layout.addWidget(self.stacked_widget)
        
        layout.addWidget(self.main_container)
        
    def create_toolbar(self):
        """Create the formatting toolbar."""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(5, 2, 5, 2)
        toolbar_layout.setSpacing(2)
        
        # Bold button
        self.bold_btn = ToolButton(FIF.FONT)
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.setShortcut(QKeySequence("Ctrl+B"))
        toolbar_layout.addWidget(self.bold_btn)
        
        # Italic button  
        self.italic_btn = ToolButton(FIF.EDIT)
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.setShortcut(QKeySequence("Ctrl+I"))
        toolbar_layout.addWidget(self.italic_btn)
        
        # Underline button (using strikethrough in Markdown)
        self.underline_btn = ToolButton(FIF.EDIT)
        self.underline_btn.setToolTip("Strikethrough (Ctrl+U)")
        self.underline_btn.setShortcut(QKeySequence("Ctrl+U"))
        toolbar_layout.addWidget(self.underline_btn)
        
        # Add separator
        toolbar_layout.addSpacing(10)
        
        # Header buttons
        self.h1_btn = QPushButton("H1")
        self.h1_btn.setToolTip("Header 1")
        self.h1_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.h1_btn)
        
        self.h2_btn = QPushButton("H2")
        self.h2_btn.setToolTip("Header 2")
        self.h2_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.h2_btn)
        
        self.h3_btn = QPushButton("H3")
        self.h3_btn.setToolTip("Header 3")
        self.h3_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.h3_btn)
        
        # Add separator
        toolbar_layout.addSpacing(10)
        
        # List buttons
        self.bullet_btn = ToolButton(FIF.CHECKBOX)
        self.bullet_btn.setToolTip("Bullet List")
        toolbar_layout.addWidget(self.bullet_btn)
        
        self.number_btn = ToolButton(FIF.VIEW)
        self.number_btn.setToolTip("Numbered List")
        toolbar_layout.addWidget(self.number_btn)
        
        # Add separator
        toolbar_layout.addSpacing(10)
        
        # Code button
        self.code_btn = ToolButton(FIF.SETTING)
        self.code_btn.setToolTip("Inline Code")
        toolbar_layout.addWidget(self.code_btn)
        
        # Link button
        self.link_btn = ToolButton(FIF.SHARE)
        self.link_btn.setToolTip("Insert Link")
        toolbar_layout.addWidget(self.link_btn)
        
        # Add separator
        toolbar_layout.addSpacing(10)
        
        # Preview/Edit toggle button
        self.preview_btn = ToolButton(FIF.VIEW)
        self.preview_btn.setToolTip("Toggle Preview (Ctrl+P)")
        self.preview_btn.setShortcut(QKeySequence("Ctrl+P"))
        self.preview_btn.setCheckable(True)
        # Remove text to avoid overlap with icon
        self.preview_btn.setText("")
        toolbar_layout.addWidget(self.preview_btn)
        
        # Add stretch to push buttons to the left
        toolbar_layout.addStretch()
        
        return toolbar_widget
    
    def setup_connections(self):
        """Set up signal connections."""
        self.bold_btn.clicked.connect(self.toggle_bold)
        self.italic_btn.clicked.connect(self.toggle_italic)
        self.underline_btn.clicked.connect(self.toggle_strikethrough)
        
        self.h1_btn.clicked.connect(lambda: self.insert_header(1))
        self.h2_btn.clicked.connect(lambda: self.insert_header(2))
        self.h3_btn.clicked.connect(lambda: self.insert_header(3))
        
        self.bullet_btn.clicked.connect(self.insert_bullet_list)
        self.number_btn.clicked.connect(self.insert_numbered_list)
        
        self.code_btn.clicked.connect(self.toggle_inline_code)
        self.link_btn.clicked.connect(self.insert_link)
        self.preview_btn.clicked.connect(self.toggle_preview)
        
        # Forward text changed signal
        self.editor.textChanged.connect(self.textChanged.emit)
        self.editor.textChanged.connect(self._update_preview)
    
    def get_selected_text_or_word(self):
        """Get selected text or word at cursor position."""
        cursor = self.editor.textCursor()
        
        if cursor.hasSelection():
            return cursor.selectedText(), cursor
        
        # If no selection, select the word at cursor
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText(), cursor
    
    def wrap_selection(self, prefix, suffix=""):
        """Wrap selected text or word with prefix and suffix."""
        if suffix == "":
            suffix = prefix
            
        text, cursor = self.get_selected_text_or_word()
        
        # If text is already wrapped, unwrap it
        if text.startswith(prefix) and text.endswith(suffix):
            new_text = text[len(prefix):-len(suffix)] if suffix else text[len(prefix):]
        else:
            new_text = f"{prefix}{text}{suffix}"
        
        cursor.insertText(new_text)
        self.editor.setTextCursor(cursor)
    
    def toggle_bold(self):
        """Toggle bold formatting (**text**)."""
        self.wrap_selection("**")
    
    def toggle_italic(self):
        """Toggle italic formatting (*text*)."""
        self.wrap_selection("*")
    
    def toggle_strikethrough(self):
        """Toggle strikethrough formatting (~~text~~)."""
        self.wrap_selection("~~")
    
    def toggle_inline_code(self):
        """Toggle inline code formatting (`text`)."""
        self.wrap_selection("`")
    
    def insert_header(self, level):
        """Insert header at the current line."""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        
        line_text = cursor.selectedText()
        
        # Remove existing header markers
        while line_text.startswith('#'):
            line_text = line_text[1:].lstrip()
        
        # Add new header markers
        header_prefix = "#" * level + " "
        new_text = header_prefix + line_text
        
        cursor.insertText(new_text)
        self.editor.setTextCursor(cursor)
    
    def insert_bullet_list(self):
        """Insert bullet list item."""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        
        if cursor.atEnd():
            cursor.insertText("- ")
        else:
            cursor.insertText("- ")
            
        self.editor.setTextCursor(cursor)
    
    def insert_numbered_list(self):
        """Insert numbered list item."""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        
        if cursor.atEnd():
            cursor.insertText("1. ")
        else:
            cursor.insertText("1. ")
            
        self.editor.setTextCursor(cursor)
    
    def insert_link(self):
        """Insert link template."""
        text, cursor = self.get_selected_text_or_word()
        
        if text:
            link_text = f"[{text}](URL)"
        else:
            link_text = "[Link Text](URL)"
        
        cursor.insertText(link_text)
        self.editor.setTextCursor(cursor)
    
    def toggle_preview(self):
        """Toggle between edit only and edit + preview side by side modes."""
        self.preview_mode = (self.preview_mode + 1) % 2
        
        if self.preview_mode == 0:  # Edit only
            self.stacked_widget.setCurrentIndex(0)
            self.preview_btn.setToolTip("Switch to Edit+Preview Mode (Ctrl+P)")
        else:  # Edit + Preview side by side
            self.stacked_widget.setCurrentIndex(1)
            self._update_preview()
            self.preview_btn.setToolTip("Switch to Edit Only Mode (Ctrl+P)")
        
        self.preview_btn.setChecked(self.preview_mode > 0)
    
    def _update_preview(self):
        """Update the preview with rendered markdown."""
        if self.preview_mode == 0:  # Edit only mode
            return
            
        markdown_text = self.editor.toPlainText()
        html = self._markdown_to_html(markdown_text)
        self.preview.setHtml(html)
    
    def _markdown_to_html(self, markdown_text):
        """Convert markdown to HTML."""
        # Configure markdown with extensions
        md = markdown.Markdown(extensions=[
            'extra',  # Extra features like tables, footnotes
            'codehilite',  # Code highlighting
            'toc',  # Table of contents
            'meta',  # Metadata
            'nl2br',  # Newlines to <br>
        ])
        
        # Convert to HTML
        html = md.convert(markdown_text)
        
        # Add some basic CSS styling
        css = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: none;
                margin: 0;
                padding: 10px;
            }
            h1 { font-size: 2em; margin-top: 0.5em; margin-bottom: 0.5em; border-bottom: 2px solid #eee; }
            h2 { font-size: 1.5em; margin-top: 0.5em; margin-bottom: 0.5em; border-bottom: 1px solid #eee; }
            h3 { font-size: 1.25em; margin-top: 0.5em; margin-bottom: 0.5em; }
            h4 { font-size: 1.1em; margin-top: 0.5em; margin-bottom: 0.5em; }
            h5 { font-size: 1em; margin-top: 0.5em; margin-bottom: 0.5em; }
            h6 { font-size: 0.9em; margin-top: 0.5em; margin-bottom: 0.5em; }
            p { margin: 0.5em 0; }
            code {
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 0.9em;
            }
            pre {
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 0.9em;
                margin: 0.5em 0;
            }
            blockquote {
                border-left: 4px solid #ddd;
                margin: 0;
                padding-left: 10px;
                color: #666;
            }
            ul, ol { margin: 0.5em 0; padding-left: 2em; }
            li { margin: 0.25em 0; }
            table {
                border-collapse: collapse;
                margin: 0.5em 0;
                width: 100%;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th { background-color: #f2f2f2; }
            a { color: #0366d6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
        """
        
        return css + html
    
    # Public methods to maintain compatibility with QTextEdit
    def setMarkdown(self, markdown):
        """Set the content as Markdown."""
        self.editor.setPlainText(markdown)
        if self.preview_mode > 0:  # Preview mode
            self._update_preview()
    
    def toMarkdown(self):
        """Get the content as Markdown."""
        return self.editor.toPlainText()
    
    def setPlaceholderText(self, text):
        """Set placeholder text."""
        self.editor.setPlaceholderText(text)
    
    def toPlainText(self):
        """Get plain text content."""
        return self.editor.toPlainText()
    
    def setPlainText(self, text):
        """Set plain text content."""
        self.editor.setPlainText(text)
        if self.preview_mode > 0:  # Preview mode
            self._update_preview()
    
    def clear(self):
        """Clear the editor."""
        self.editor.clear()
        if self.preview_mode > 0:  # Preview mode
            self.preview.clear()
    
    def setFocus(self):
        """Set focus to the current active widget."""
        if self.preview_mode == 0:  # Edit only
            self.editor.setFocus()
        else:  # Edit + Preview side by side
            self.editor.setFocus()  # Focus on editor