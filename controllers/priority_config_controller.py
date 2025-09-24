from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog
import logging

class PriorityConfigController(QObject):
    """Controller for managing Jira priority configurations."""
    
    priority_updated = pyqtSignal(str, str)  # jira_key, new_priority
    
    def __init__(self, db_service, jira_service):
        super().__init__()
        self.db_service = db_service
        self.jira_service = jira_service
        self.logger = logging.getLogger('JiraTimeTracker')
        
    def update_priority(self, jira_key, new_priority):
        """Update the priority of a Jira issue."""
        try:
            # First, try to update the priority in Jira
            if self.jira_service.is_connected():
                success = self.jira_service.update_issue_priority(jira_key, new_priority)
                if success:
                    self.logger.info(f"Priority updated in Jira for {jira_key}: {new_priority}")
                    # Mark as synced and remove from local overrides
                    self.db_service.mark_priority_update_synced(jira_key)
                    self.priority_updated.emit(jira_key, new_priority)
                    return True
                else:
                    self.logger.warning(f"Failed to update priority in Jira for {jira_key}")
            else:
                self.logger.warning("Cannot update priority: Jira is not connected")
                
            # If Jira update failed or we're offline, store locally for sync later
            # Try to get priority ID from name
            priority_id = self._get_priority_id_for_name(new_priority)
            self.db_service.set_local_priority(jira_key, priority_id, new_priority)
            self.logger.info(f"Priority update stored locally for {jira_key}: {new_priority}")
            self.priority_updated.emit(jira_key, new_priority)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating priority: {str(e)}")
            return False
    
    def _get_priority_id_for_name(self, priority_name: str) -> str:
        """Get the priority ID for a given priority name."""
        priority_map = {
            "Highest": "1",
            "High": "2", 
            "Medium": "3",
            "Low": "4",
            "Lowest": "5"
        }
        return priority_map.get(priority_name, priority_name)
    
    def get_available_priorities(self):
        """Get list of available priorities from Jira."""
        try:
            if self.jira_service.is_connected():
                priorities = self.jira_service.get_priorities()
                return priorities
            else:
                # Return basic priorities when offline
                return [
                    {"id": "1", "name": "Highest"},
                    {"id": "2", "name": "High"},
                    {"id": "3", "name": "Medium"},
                    {"id": "4", "name": "Low"},
                    {"id": "5", "name": "Lowest"}
                ]
        except Exception as e:
            self.logger.error(f"Error getting priorities: {str(e)}")
            return []