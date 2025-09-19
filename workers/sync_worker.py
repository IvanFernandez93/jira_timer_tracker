from PyQt6.QtCore import QObject, pyqtSignal
import json
import time

class SyncWorker(QObject):
    """
    A worker that runs in a separate thread to process the sync queue.
    """
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, jira_service, db_service):
        super().__init__()
        self.jira_service = jira_service
        self.db_service = db_service
        self.is_running = True

    def run(self):
        """The main work of the thread."""
        self.progress.emit("Sync worker started...")
        
        pending_items = self.db_service.get_pending_sync_items()
        if not pending_items:
            self.progress.emit("No items to sync.")
            self.finished.emit()
            return

        for item in pending_items:
            if not self.is_running:
                break

            item_id = item[0]
            op_type = item[1]
            payload_str = item[2]
            
            self.db_service.update_sync_item_status(item_id, "Processing")
            self.progress.emit(f"Processing item {item_id}: {op_type}")

            try:
                payload = json.loads(payload_str)
                
                if op_type == "ADD_WORKLOG":
                    self._handle_add_worklog(payload)
                elif op_type == "ADD_COMMENT":
                    self._handle_add_comment(payload)
                elif op_type == "ADD_ATTACHMENT":
                    self._handle_add_attachment(payload)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")

                self.db_service.update_sync_item_status(item_id, "Success")
                self.progress.emit(f"Item {item_id} synced successfully.")

            except Exception as e:
                error_message = str(e)
                self.error.emit(f"Failed to sync item {item_id}: {error_message}")
                self.db_service.mark_sync_item_as_error(item_id, error_message)
            
            time.sleep(1) # Small delay between operations

        self.progress.emit("Sync run finished.")
        self.finished.emit()

    def _handle_add_worklog(self, payload):
        """Processes the ADD_WORKLOG operation."""
        self.jira_service.add_worklog(
            issue=payload["jira_key"],
            timeSpentSeconds=payload["time_spent_seconds"],
            comment=payload.get("comment", ""),
            started=payload["start_time"]
        )

    def _handle_add_comment(self, payload):
        """Processes the ADD_COMMENT operation."""
        self.jira_service.add_comment(
            issue_key=payload["jira_key"],
            body=payload["body"]
        )

    def _handle_add_attachment(self, payload):
        """Processes the ADD_ATTACHMENT operation."""
        self.jira_service.add_attachment(
            issue_key=payload["jira_key"],
            file_path=payload["file_path"]
        )

    def stop(self):
        self.is_running = False
