from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView, QHeaderView, QLabel, QTableWidgetItem, QFrame, QComboBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie
from qfluentwidgets import (
    SearchLineEdit, TableWidget, FluentIcon as FIF, 
    LineEdit, PushButton, TransparentToolButton,
    InfoBar, InfoBarPosition
)

class JiraGridView(QWidget):
    """
    A view widget that displays Jira issues in a searchable and sortable table.
    Fulfills requirements 2.3.1, 2.3.2.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("jiraGridView") # For navigation
        self.app_settings = None

        # Table for Jira Issues (Req 2.3.1)
        # Columns config - list of dicts: {id,label,visible,sortable}
        self.columns_config = [
            {"id": "key", "label": "Key", "visible": True, "sortable": True},
            {"id": "title", "label": "Title", "visible": True, "sortable": True},
            {"id": "status", "label": "Status", "visible": True, "sortable": True},
            {"id": "time_spent", "label": "Time Spent", "visible": True, "sortable": True},
            {"id": "favorite", "label": "Favorite", "visible": True, "sortable": False},
        ]

        self.table = TableWidget() # Using Fluent TableWidget
        # Initialize columns according to config (will be updated when app_settings set)
        # Default: apply current config
        try:
            header = self.table.horizontalHeader()
        except Exception:
            header = None
        # We'll set up headers properly when app_settings is available via _apply_columns()
        
        # Configure column resizing - Key column always visible, Title stretches
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Key column auto-resize
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title column stretches
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Status column auto-resize
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Time column auto-resize
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Favorite column fixed
        self.table.setColumnWidth(4, 60)  # Fixed width for favorite column
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Enable cumulative sorting
        self.table.setSortingEnabled(True)
        self.sort_columns = []  # Track sort order for cumulative sorting
        header.sectionClicked.connect(self._on_header_clicked)

        # Title label
        self.title_label = QLabel("Griglia Jira")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        # JQL filter layout
        jql_layout = QHBoxLayout()
        jql_label = QLabel("JQL:")
        jql_layout.addWidget(jql_label)
        
        self.jql_combo = QComboBox()
        self.jql_combo.setEditable(True)  # Allow manual input
        self.jql_combo.setPlaceholderText("Enter JQL query or select from favorites...")
        self.jql_combo.setToolTip("Inserisci una query JQL o seleziona dai preferiti")
        # Remove minimum width to allow full expansion
        jql_layout.addWidget(self.jql_combo, 1)  # Stretch factor 1 to expand
        
        self.apply_jql_btn = PushButton("Apply")
        self.apply_jql_btn.setIcon(FIF.SEARCH)
        self.apply_jql_btn.setToolTip("Esegui la query JQL")
        jql_layout.addWidget(self.apply_jql_btn)

        # Search and filter layout
        filter_layout = QHBoxLayout()
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Filter by Key or Title...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setToolTip("Filtra i ticket per chiave o titolo")
        filter_layout.addWidget(self.search_box)

        # Favorites toggle button
        self.favorites_btn = TransparentToolButton()
        self.favorites_btn.setCheckable(True)
        self.favorites_btn.setText("☆")
        self.favorites_btn.setToolTip("Mostra solo i ticket preferiti")
        self.favorites_btn.setFixedSize(32, 32)
        filter_layout.addWidget(self.favorites_btn)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addLayout(jql_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        # Notification button
        self.notifications_btn = PushButton(FIF.RINGER, "Notifiche")
        self.notifications_btn.setToolTip("Visualizza le notifiche del programma")
        self.notifications_btn.setFixedHeight(32)
        layout.insertWidget(0, self.notifications_btn)

        # Loading spinner overlay
        self.loading_overlay = QFrame(self)
        self.loading_overlay.setFrameShape(QFrame.Shape.StyledPanel)
        self.loading_overlay.setStyleSheet("background-color: rgba(255, 255, 255, 180);")
        self.loading_overlay.setVisible(False)
        
        loading_layout = QVBoxLayout(self.loading_overlay)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create spinner indicator using a simple animated text label instead of GIF
        self.loading_spinner = QLabel("⬤")
        self.loading_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_spinner.setStyleSheet("""
            font-size: 24px;
            color: #007ACC;
        """)
        loading_layout.addWidget(self.loading_spinner, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Create animation timer for the spinner
        from PyQt6.QtCore import QTimer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_spinner_animation)
        self.animation_counter = 0
        
        self.status_label = QLabel("Caricamento dati in corso...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #007ACC;")
        loading_layout.addWidget(self.status_label)
        
        # Error message label
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #E74C3C; font-weight: bold;")
        self.error_label.setVisible(False)
        loading_layout.addWidget(self.error_label)
        
    def resizeEvent(self, event):
        """Handle resize events to reposition the loading overlay."""
        super().resizeEvent(event)
        if self.loading_overlay.isVisible():
            self.loading_overlay.setGeometry(self.table.geometry())

    def _update_spinner_animation(self):
        """Updates the spinner animation."""
        spinner_frames = ["⬤   ", " ⬤  ", "  ⬤ ", "   ⬤", "  ⬤ ", " ⬤  "]
        self.loading_spinner.setText(spinner_frames[self.animation_counter % len(spinner_frames)])
        self.animation_counter += 1
        
    def show_loading(self, is_loading):
        """Shows or hides the loading indicator."""
        if is_loading:
            # Start the loading animation
            self.animation_timer.start(200)  # Update every 200ms
            self.status_label.setText("Caricamento dati in corso...")
            self.error_label.setVisible(False)
            
            # Position the overlay over the table
            self.loading_overlay.setGeometry(self.table.geometry())
            self.loading_overlay.raise_()  # Bring to front
            self.loading_overlay.setVisible(True)
        else:
            # Stop the loading animation and hide the overlay
            self.animation_timer.stop()
            self.loading_overlay.setVisible(False)

    def show_error(self, message):
        """Displays an error message using Fluent InfoBar and in the loading overlay."""
        # If the loading overlay is visible, show the error there
        if self.loading_overlay.isVisible():
            self.animation_timer.stop()
            self.loading_spinner.setText("❌")  # Show error icon
            self.status_label.setText("Si è verificato un errore:")
            self.error_label.setText(message)
            self.error_label.setVisible(True)
            
            # Hide overlay after a delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.loading_overlay.setVisible(False))
        
        # Always attempt to show the error in the InfoBar; fallback to QMessageBox or overlay
        try:
            InfoBar.error(
                title="Errore",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,  # 3 seconds
                parent=self
            )
        except Exception:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Errore", str(message))
            except Exception:
                # Last fallback: show in the overlay label if available
                try:
                    self.error_label.setText(message)
                    self.error_label.setVisible(True)
                except Exception:
                    pass

    def clear_table(self):
        """Removes all rows from the table."""
        self.table.setRowCount(0)

    def add_issue_row(self, row_data):
        """
        Adds a new row to the table.
        `row_data` should be a dictionary with keys: 'key', 'title', 'status', 'time_spent'.
        """
        # Insert row and populate columns according to visible columns config
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        visible = self.get_visible_columns()
        for col_index, col in enumerate(visible):
            cid = col.get('id')
            if cid == 'favorite':
                fav_button = TransparentToolButton("☆")
                fav_button.setCheckable(True)
                fav_button.setToolTip("Aggiungi/rimuovi dai preferiti")
                # set checked state if provided
                if row_data.get('favorite_checked'):
                    fav_button.setChecked(True)
                    fav_button.setText("★")
                self.table.setCellWidget(row_position, col_index, fav_button)
            else:
                text = str(row_data.get(cid, ''))
                self.table.setItem(row_position, col_index, QTableWidgetItem(text))

    def populate_jql_favorites(self, favorites):
        """Populate the JQL combo box with favorite queries."""
        self.jql_combo.clear()
        
        # Add favorites with their names and query preview
        for fav_id, name, query in favorites:
            # Create display text with truncated query only
            if len(query) <= 60:
                display_text = query
            else:
                truncated_query = query[:60]
                last_space = truncated_query.rfind(' ')
                if last_space > 20:
                    truncated_query = query[:last_space]
                display_text = f"{truncated_query}..."
            
            # Store the query as user data and display the truncated query
            self.jql_combo.addItem(display_text, query)
            # Set tooltip with the full name and query
            self.jql_combo.setItemData(self.jql_combo.count() - 1, f"{name}\n{query}", Qt.ItemDataRole.ToolTipRole)
        
        # Always add option to show history dialog (even if no favorites)
        if favorites:
            self.jql_combo.insertSeparator(self.jql_combo.count())
        
        self.jql_combo.addItem("📚 Gestisci cronologia e preferiti...", None)

    def get_jql_text(self):
        """Get the current JQL text from the combo box."""
        current_index = self.jql_combo.currentIndex()
        if current_index >= 0:
            # Check if this is a favorite item (has associated data)
            item_data = self.jql_combo.itemData(current_index)
            if item_data is not None:
                # This is a favorite, return the actual query
                return item_data
            else:
                # This is either manually typed text or the management option
                current_text = self.jql_combo.currentText()
                if current_text == "📚 Gestisci cronologia e preferiti...":
                    return ""  # Don't return the management option text
                else:
                    return current_text
        return ""
    
    def set_jql_text(self, text):
        """Set the JQL text in the combo box."""
        # First, check if this text matches any favorite query
        for i in range(self.jql_combo.count()):
            item_data = self.jql_combo.itemData(i)
            if item_data == text:
                # Found a matching favorite, select it and show the actual query
                self.jql_combo.setCurrentIndex(i)
                # Override the display text to show the full query instead of truncated version
                self.jql_combo.setCurrentText(text)
                return
        
        # If no favorite matches, set the text manually
        self.jql_combo.setCurrentText(text)

    def _on_header_clicked(self, logical_index):
        """Handle header clicks for cumulative sorting."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        
        # Check if Shift is pressed for cumulative sorting
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Cumulative sorting: add this column to sort order
            existing_sort = next((item for item in self.sort_columns if item['column'] == logical_index), None)
            
            if existing_sort:
                # Toggle sort order for existing column
                existing_sort['order'] = Qt.SortOrder.DescendingOrder if existing_sort['order'] == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            else:
                # Add new column to sort order
                self.sort_columns.append({
                    'column': logical_index,
                    'order': Qt.SortOrder.AscendingOrder
                })
        else:
            # Normal sorting: clear previous sorts and set new primary sort
            current_order = Qt.SortOrder.AscendingOrder
            if self.sort_columns and self.sort_columns[0]['column'] == logical_index:
                current_order = Qt.SortOrder.DescendingOrder if self.sort_columns[0]['order'] == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            
            self.sort_columns = [{
                'column': logical_index,
                'order': current_order
            }]
        
        # Apply the cumulative sort
        self._apply_cumulative_sort()
        
        # Save sort order to settings
        self._save_sort_order()
    
    def _apply_cumulative_sort(self):
        """Apply cumulative sorting to the table."""
        if not self.sort_columns:
            return
            
        # Get all table data
        table_data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount() - 1):  # Exclude favorite column
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            
            # Store widget from favorite column
            favorite_widget = self.table.cellWidget(row, 4)
            row_data.append(favorite_widget)
            table_data.append(row_data)
        
        # Sort data using multiple criteria
        def sort_key(row_data):
            key = []
            for sort_info in reversed(self.sort_columns):  # Process in reverse order for stable sort
                col_index = sort_info['column']
                if col_index < len(row_data) - 1:  # Exclude favorite column from sorting
                    value = row_data[col_index]
                    # Handle numeric sorting for time column
                    if col_index == 3:  # Time Spent column
                        try:
                            # Extract hours and minutes
                            if 'h' in value and 'm' in value:
                                parts = value.replace('h', '').replace('m', '').split()
                                hours = int(parts[0]) if len(parts) > 0 else 0
                                minutes = int(parts[1]) if len(parts) > 1 else 0
                                numeric_value = hours * 60 + minutes
                            else:
                                numeric_value = 0
                            key.append((numeric_value, sort_info['order'] == Qt.SortOrder.DescendingOrder))
                        except:
                            key.append((0, sort_info['order'] == Qt.SortOrder.DescendingOrder))
                    else:
                        # String sorting
                        key.append((value.lower(), sort_info['order'] == Qt.SortOrder.DescendingOrder))
            return key
        
        # Sort the data
        sorted_data = sorted(table_data, key=sort_key, reverse=False)
        
        # Clear table and repopulate with sorted data
        self.table.setRowCount(0)
        for row_data in sorted_data:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Add text items
            for col in range(len(row_data) - 1):
                self.table.setItem(row_position, col, QTableWidgetItem(row_data[col]))
            
            # Add favorite widget
            if row_data[-1]:
                self.table.setCellWidget(row_position, 4, row_data[-1])
    
    def _save_sort_order(self):
        """Save current sort order to settings."""
        if self.app_settings and self.sort_columns:
            try:
                import json
                payload = json.dumps(self.sort_columns)
            except Exception:
                # Fallback to string repr if json fails
                payload = str(self.sort_columns)
            try:
                self.app_settings.set_setting('table_sort_order', payload)
            except Exception:
                pass
    
    def restore_sort_order(self, sort_order_data):
        """Restore sort order from settings."""
        if sort_order_data:
            self.sort_columns = sort_order_data
            self._apply_cumulative_sort()
    
    def get_sort_order(self):
        """Get current sort order for saving to settings."""
        return self.sort_columns
        
    def set_app_settings(self, app_settings):
        """Set the app_settings reference for persistence functionality."""
        self.app_settings = app_settings

        # If no app_settings provided (e.g. tests pass None), just apply default columns
        if not self.app_settings:
            try:
                self._apply_columns()
            except Exception:
                pass
            return

        # Load columns config if present
        try:
            import json
            saved = self.app_settings.get_setting('grid_columns', None)
            if saved:
                self.columns_config = json.loads(saved)
        except Exception:
            pass

        # Restore saved sort order if available
        try:
            saved_sort_order = self.app_settings.get_setting('table_sort_order', None)
            if saved_sort_order:
                # Try JSON decode first, fall back to eval-like parsing
                try:
                    import json
                    parsed = json.loads(saved_sort_order)
                except Exception:
                    try:
                        # Safe-ish eval for list reprs
                        parsed = eval(saved_sort_order)
                    except Exception:
                        parsed = None

                if parsed:
                    self.restore_sort_order(parsed)
        except Exception:
            pass

        # Re-apply columns now that settings loaded
        try:
            self._apply_columns()
        except Exception:
            pass

    def _apply_columns(self):
        """Apply current `self.columns_config` to the table headers and column count."""
        # Build visible columns list
        visible = [c for c in self.columns_config if c.get('visible', True)]
        self.table.setColumnCount(len(visible))
        labels = [c.get('label', c.get('id')) for c in visible]
        try:
            self.table.setHorizontalHeaderLabels(labels)
        except Exception:
            pass
        # Adjust header defaults for some known columns
        try:
            header = self.table.horizontalHeader()
            for i, col in enumerate(visible):
                cid = col.get('id')
                if cid == 'key':
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
                elif cid == 'title':
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
                elif cid == 'favorite':
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    try:
                        self.table.setColumnWidth(i, 60)
                    except Exception:
                        pass
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        except Exception:
            pass

    def get_visible_columns(self):
        return [c for c in self.columns_config if c.get('visible', True)]
