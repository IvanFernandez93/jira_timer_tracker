from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QTableWidgetItem, QWidget, QHBoxLayout, QPushButton,
    QMessageBox, QHeaderView
)
from PyQt6.QtGui import QColor, QBrush, QIcon
import json
from views.sync_queue_dialog import SyncQueueDialog
from qfluentwidgets import FluentIcon as FIF, getIconColor
from qfluentwidgets.common.icon import FluentIconBase, Icon

class SyncQueueController(QObject):
    """Controller for the Sync Queue Dialog."""
    
    sync_operation_changed = pyqtSignal()  # Signal emitted when sync operation status changes
    
    def __init__(self, db_service, jira_service, parent=None):
        super().__init__()
        self.db_service = db_service
        self.jira_service = jira_service
        # Parent the dialog to the provided parent (usually the main window)
        self.view = SyncQueueDialog(parent)
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals from the view to controller methods."""
        self.view.retry_all_btn.clicked.connect(self._retry_all_failed)
        self.view.delete_selected_btn.clicked.connect(self._delete_selected)
        self.view.table.itemClicked.connect(self._on_item_clicked)
        
    def run(self):
        """Loads data and shows the dialog."""
        self._load_data()
        return self.view.exec()
        
    def _load_data(self):
        """Loads the sync queue data from the database."""
        self.view.clear_table()
        self.view.hide_error_details()
        
        # Get pending and failed operations
        pending_ops = self.db_service.get_pending_sync_operations()
        failed_ops = self.db_service.get_failed_sync_operations()
        
        # Update status counters
        self.view.pending_label.setText(f"In attesa: {len(pending_ops)}")
        self.view.failed_label.setText(f"Falliti: {len(failed_ops)}")
        
        # Combine operations for display
        all_ops = []
        for op in pending_ops:
            all_ops.append((op[0], op[1], op[2], "Pending", op[3], None))
            
        for op in failed_ops:
            all_ops.append((op[0], op[1], op[2], "Failed", op[3], op[4]))
            
        # Add rows to table
        self.view.table.setRowCount(len(all_ops))
        
        for row, (op_id, op_type, payload, status, attempts, error) in enumerate(all_ops):
            # Create items for the table
            id_item = QTableWidgetItem(str(op_id))
            type_item = QTableWidgetItem(op_type)
            
            # Format payload for display
            try:
                payload_data = json.loads(payload)
                if op_type == "ADD_WORKLOG":
                    display_text = f"Jira: {payload_data.get('jira_key')}, Tempo: {payload_data.get('time_spent_seconds') // 60} min"
                elif op_type == "ADD_COMMENT":
                    display_text = f"Jira: {payload_data.get('jira_key')}, Commento: {payload_data.get('body')[:30]}..."
                elif op_type == "ADD_ATTACHMENT":
                    display_text = f"Jira: {payload_data.get('jira_key')}, File: {payload_data.get('file_path')}"
                else:
                    display_text = payload[:50] + "..." if len(payload) > 50 else payload
            except json.JSONDecodeError:
                display_text = payload[:50] + "..." if len(payload) > 50 else payload
                
            payload_item = QTableWidgetItem(display_text)
            status_item = QTableWidgetItem(status)
            attempts_item = QTableWidgetItem(str(attempts))
            
            # Set colors based on status
            if status == "Pending":
                status_item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
            elif status == "Failed":
                status_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
                
            # Store original data for reference
            id_item.setData(Qt.ItemDataRole.UserRole, op_id)
            type_item.setData(Qt.ItemDataRole.UserRole, op_type)
            payload_item.setData(Qt.ItemDataRole.UserRole, payload)
            status_item.setData(Qt.ItemDataRole.UserRole, status)
            
            # Add items to table
            self.view.table.setItem(row, 0, id_item)
            self.view.table.setItem(row, 1, type_item)
            self.view.table.setItem(row, 2, payload_item)
            self.view.table.setItem(row, 3, status_item)
            self.view.table.setItem(row, 4, attempts_item)
            
            # Add action buttons
            self._add_action_buttons(row, op_id, status, error)
            
        # Resize columns
        self.view.table.resizeColumnsToContents()
        
    def _add_action_buttons(self, row, op_id, status, error):
        """Adds action buttons to the row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Poiché non possiamo usare direttamente FluentIcon con QPushButton,
        # useremo le icone di sistema per i pulsanti
        from PyQt6.QtWidgets import QStyle
        
        # Retry button (only for failed operations)
        retry_btn = QPushButton()
        retry_btn.setIcon(retry_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        retry_btn.setFixedSize(28, 28)
        retry_btn.setToolTip("Riprova")
        retry_btn.clicked.connect(lambda _, id=op_id: self._retry_operation(id))
        retry_btn.setEnabled(status == "Failed")
        
        # Delete button
        delete_btn = QPushButton()
        delete_btn.setIcon(delete_btn.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.setFixedSize(28, 28)
        delete_btn.setToolTip("Elimina")
        delete_btn.clicked.connect(lambda _, id=op_id: self._delete_operation(id))
        
        # Info button (only for failed operations)
        info_btn = QPushButton()
        info_btn.setIcon(info_btn.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        info_btn.setFixedSize(28, 28)
        info_btn.setToolTip("Dettagli errore")
        info_btn.clicked.connect(lambda _, err=error: self._show_error_info(err))
        info_btn.setEnabled(status == "Failed" and error is not None)
        
        layout.addWidget(retry_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(info_btn)
        layout.addStretch()
        
        self.view.table.setCellWidget(row, 5, widget)
        
    def _on_item_clicked(self, item):
        """Handles click on table item to show error details."""
        row = item.row()
        status_item = self.view.table.item(row, 3)
        
        if status_item and status_item.data(Qt.ItemDataRole.UserRole) == "Failed":
            # Get error message from the database
            op_id = int(self.view.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
            
            # Find the error message from the failed operations
            failed_ops = self.db_service.get_failed_sync_operations()
            error = None
            for fop in failed_ops:
                if fop[0] == op_id:
                    error = fop[4]
                    break
                    
            if error:
                self.view.show_error_details(error)
            else:
                self.view.hide_error_details()
        else:
            self.view.hide_error_details()
            
    def _show_error_info(self, error):
        """Shows error details."""
        if error:
            self.view.show_error_details(error)
        else:
            self.view.hide_error_details()
            
    def _retry_operation(self, op_id):
        """Retries a single failed operation."""
        # In a real implementation, this would attempt to execute the operation
        # For now, we'll just mark it as pending again
        try:
            self.db_service.update_sync_operation_status(op_id, "Pending")
            self.view.show_info(f"Operazione {op_id} rimessa in coda.")
            self._load_data()  # Reload the data
            self.sync_operation_changed.emit()
        except Exception as e:
            self.view.show_error(f"Errore durante la ripresa: {str(e)}")
            
    def _delete_operation(self, op_id):
        """Deletes a sync operation."""
        reply = QMessageBox.question(
            self.view,
            "Conferma eliminazione",
            f"Sei sicuro di voler eliminare l'operazione {op_id} dalla coda?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # For now, we'll just update the status to "Deleted"
                # In a full implementation, you might want to actually delete it or archive it
                self.db_service.update_sync_operation_status(op_id, "Deleted")
                self.view.show_info(f"Operazione {op_id} eliminata.")
                self._load_data()  # Reload the data
                self.sync_operation_changed.emit()
            except Exception as e:
                self.view.show_error(f"Errore durante l'eliminazione: {str(e)}")
                
    def _retry_all_failed(self):
        """Retries all failed operations."""
        # Get failed operations
        failed_ops = self.db_service.get_failed_sync_operations()
        
        if not failed_ops:
            self.view.show_info("Nessuna operazione fallita da riprovare.")
            return
            
        try:
            count = 0
            for op in failed_ops:
                op_id = op[0]
                self.db_service.update_sync_operation_status(op_id, "Pending")
                count += 1
                
            self.view.show_info(f"{count} operazioni rimesse in coda.")
            self._load_data()  # Reload the data
            self.sync_operation_changed.emit()
        except Exception as e:
            self.view.show_error(f"Errore durante la ripresa: {str(e)}")
            
    def _delete_selected(self):
        """Deletes all selected operations."""
        selected_rows = set(item.row() for item in self.view.table.selectedItems())
        
        if not selected_rows:
            self.view.show_info("Nessuna operazione selezionata.")
            return
            
        op_ids = [int(self.view.table.item(row, 0).data(Qt.ItemDataRole.UserRole)) for row in selected_rows]
        
        reply = QMessageBox.question(
            self.view,
            "Conferma eliminazione",
            f"Sei sicuro di voler eliminare {len(op_ids)} operazioni dalla coda?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for op_id in op_ids:
                    self.db_service.update_sync_operation_status(op_id, "Deleted")
                    
                self.view.show_info(f"{len(op_ids)} operazioni eliminate.")
                self._load_data()  # Reload the data
                self.sync_operation_changed.emit()
            except Exception as e:
                self.view.show_error(f"Errore durante l'eliminazione: {str(e)}")