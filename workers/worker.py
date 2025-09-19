from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import logging
import traceback


class JiraWorker(QObject):
    """
    A worker object that performs tasks in a separate thread.
    Designed to handle long-running operations like network requests without
    freezing the main UI.
    """
    finished = pyqtSignal(list)  # Signal to emit when the task is done, carrying the result
    error = pyqtSignal(str)        # Signal to emit when an error occurs

    def __init__(self, jira_service, jql, start_at=0, max_results=100, favorite_keys=None):
        super().__init__()
        self.jira_service = jira_service
        self.jql = jql
        self.start_at = start_at
        self.max_results = max_results
        self.favorite_keys = favorite_keys
        self._logger = logging.getLogger('JiraTimeTracker')

    @pyqtSlot()
    def run(self):
        """
        The main task to be executed by the worker.
        Fetches Jira issues and emits the result or an error.
        """
        try:
            # Instrumentation: log entry and parameters so we can trace worker activity
            self._logger.debug(
                "JiraWorker starting: jql=%s start_at=%s max_results=%s favorite_keys=%s",
                self.jql,
                self.start_at,
                self.max_results,
                self.favorite_keys,
            )

            if not self.jira_service.is_connected():
                raise ConnectionError("Not connected to Jira.")

            issues = self.jira_service.search_issues(
                self.jql,
                start_at=self.start_at,
                max_results=self.max_results,
                issue_keys=self.favorite_keys,
            )

            # Log result size for quick diagnostics
            try:
                count = len(issues) if issues is not None else 0
            except Exception:
                count = 0
            self._logger.debug("JiraWorker finished: loaded %s issues", count)

            self.finished.emit(issues)
        except Exception as e:
            tb = traceback.format_exc()
            # Log full traceback to the configured logger so it's visible in file/console
            self._logger.error("JiraWorker error: %s\n%s", e, tb)
            # Emit a descriptive error message including the traceback to aid debugging
            self.error.emit(f"Failed to load data: {e}\n{tb}")
