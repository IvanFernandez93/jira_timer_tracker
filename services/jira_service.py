from jira import JIRA, JIRAError
import time
import random
import logging
import tempfile
import os
from typing import Callable, Any
import json

class JiraService:
    """
    A wrapper around the jira-python library to handle all interactions
    with the Jira API.
    """
    def __init__(
        self,
        max_retries: int = 3,
        base_retry_delay: float = 0.5,
        max_delay: float = 30.0,
        sleep_func: Callable[[float], None] | None = None,
        non_retryable_statuses: list[int] | None = None,
        non_retryable_exceptions: list[type] | None = None,
    ):
        self.jira = None
        # Configurable retry policy
        self._max_retries = max_retries
        self._base_retry_delay = base_retry_delay
        self._max_delay = max_delay
        # Injectable sleep for easier unit testing (defaults to time.sleep)
        self._sleep = sleep_func or time.sleep
        # use the application logger name so logs respect global app configuration
        self._logger = logging.getLogger('JiraTimeTracker')
        # non-retryable status codes and exceptions
        self._non_retryable_statuses = set(non_retryable_statuses or [400, 401, 403, 404])
        default_excs = [json.JSONDecodeError, ValueError]
        if non_retryable_exceptions:
            default_excs.extend(non_retryable_exceptions)
        self._non_retryable_exceptions = tuple(default_excs)

    def connect(self, server_url: str, pat: str):
        """
        Connects to the Jira instance using a Personal Access Token.
        Raises JIRAError on failure.
        """
        if not server_url.startswith("http"):
            raise ValueError("Server URL must start with http or https")

        def _do_connect():
            self._logger.debug("[JiraService.connect] Attempting to connect to Jira at %s...", server_url)
            self._logger.debug("[JiraService.connect] Using PAT: %s", pat[:6] + '...' if pat else None)
            self.jira = JIRA(
                server=server_url,
                token_auth=pat,
                timeout=20, # 20-second timeout for requests
                max_retries=0 # We'll manage retries here
            )
            # The client is lazy, so we need to make a call to verify the connection
            self.jira.myself()
            self._logger.info("Jira connection verified successfully.")

        try:
            self._with_retries(_do_connect)
        except JIRAError as e:
            self._logger.error(
                "Jira connection failed. Status: %s, Text: %s",
                getattr(e, 'status_code', None),
                getattr(e, 'text', None),
            )
            raise e
        except Exception as e:
            self._logger.exception("An unexpected error occurred during Jira connection: %s", e)
            raise ConnectionError(f"Failed to connect to Jira: {e}")

    def is_connected(self) -> bool:
        """Checks if the service is connected to Jira."""
        return self.jira is not None

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 100, issue_keys: list[str] | None = None) -> list:
        """
        Searches for issues using a JQL query.
        Optionally filters by a list of issue keys.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")

        final_jql = jql
        if issue_keys is not None:
            if not issue_keys:
                return []  # If favorite list is empty, return no results
            keys_str = ", ".join(f'"{key}"' for key in issue_keys)
            # Combine with existing JQL if present
            if final_jql:
                final_jql = f"key in ({keys_str}) AND ({final_jql})"
            else:
                final_jql = f"key in ({keys_str})"
        
        def _do_search():
            # We only need a few fields for the grid view
            fields = "summary,status,timespent"
            self._logger.debug("[JiraService.search_issues] Eseguo search_issues con JQL: %s, startAt: %s, maxResults: %s", final_jql, start_at, max_results)
            issues = self.jira.search_issues(
                final_jql,
                startAt=start_at,
                maxResults=max_results,
                fields=fields,
                json_result=True # Easier to parse than objects
            )
            self._logger.debug("[JiraService.search_issues] Risposta search_issues: %s", issues)
            return issues.get('issues', [])

        try:
            return self._with_retries(_do_search)
        except JIRAError as e:
            self._logger.error("Error searching Jira issues: %s", getattr(e, 'text', None))
            raise e

    def get_issue(self, issue_key: str) -> dict:
        """
        Retrieves full details for a single issue, including comments and attachments.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        def _do_get():
            # Fetch all available fields, plus comments and attachments
            issue = self.jira.issue(issue_key, expand="renderedFields")
            issue_data = issue.raw
            # Also fetch comments separately
            issue_data['comments'] = self.jira.comments(issue_key)
            return issue_data

        try:
            return self._with_retries(_do_get)
        except JIRAError as e:
            self._logger.error("Error fetching issue '%s': %s", issue_key, getattr(e, 'text', None))
            raise e

    def add_comment(self, issue_key: str, body: str):
        """
        Adds a comment to a Jira issue.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        def _do_add():
            self.jira.add_comment(issue_key, body)
            return True

        try:
            self._with_retries(_do_add)
            self._logger.info("Successfully added comment to %s", issue_key)
        except JIRAError as e:
            self._logger.error("Error adding comment to '%s': %s", issue_key, getattr(e, 'text', None))
            raise e

    def add_attachment(self, issue_key: str, file_path: str):
        """
        Attaches a file to a Jira issue.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        def _do_attach():
            with open(file_path, 'rb') as f:
                self.jira.add_attachment(issue=issue_key, attachment=f)
            return True

        try:
            return self._with_retries(_do_attach)
        except JIRAError as e:
            self._logger.error("Error attaching file to '%s': %s", issue_key, getattr(e, 'text', None))
            raise e
        except FileNotFoundError:
            self._logger.error("Attachment file not found: %s", file_path)
            raise
            
    def get_issue_comments(self, issue_key: str) -> list:
        """
        Retrieves comments for an issue.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        def _do_get_comments():
            comments = self.jira.comments(issue_key)
            comments_list = []
            for comment in comments:
                comment_dict = {
                    'id': comment.id,
                    'body': comment.body,
                    'author': comment.author.displayName,
                    'created': comment.created,
                    'updated': comment.updated
                }
                comments_list.append(comment_dict)
            return comments_list

        try:
            return self._with_retries(_do_get_comments)
        except JIRAError as e:
            self._logger.error("Error getting comments for '%s': %s", issue_key, getattr(e, 'text', None))
            raise e
            
    def download_attachment(self, attachment_url: str, filename: str, save_path: str = None) -> str:
        """
        Downloads an attachment from Jira and saves it to the specified path.
        Returns the full path of the saved file.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        def _do_download():
            import requests

            # Use streaming request with a timeout
            sess = getattr(self.jira, '_session', None)
            if sess is None:
                # fallback to requests
                sess = requests.Session()

            resp = sess.get(attachment_url, stream=True, timeout=30)
            try:
                resp.raise_for_status()
            except Exception:
                # If 429 with Retry-After, raise JIRAError-like with status_code attribute
                status = getattr(resp, 'status_code', None)
                self._logger.error("Failed to download attachment, status: %s", status)
                resp.raise_for_status()

            # Determine save path
            if save_path is None:
                # Use default download directory
                from PyQt6.QtCore import QStandardPaths
                download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
                target_path = os.path.join(download_dir, filename)
            else:
                target_path = save_path

            # Ensure the directory exists - handle when dirname is empty
            dir_name = os.path.dirname(target_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # Stream to a temporary file then move atomically
            fd, tmp_path = tempfile.mkstemp(prefix=filename + '.', dir=dir_name or None)
            os.close(fd)
            try:
                with open(tmp_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                # Atomic replace
                os.replace(tmp_path, target_path)
            except Exception:
                # cleanup temp file on failure
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                raise

            self._logger.info("Successfully downloaded attachment: %s", target_path)
            return target_path

        try:
            return self._with_retries(_do_download)
        except Exception as e:
            print(f"Error downloading attachment '{filename}': {e}")
            raise e

    def _with_retries(
        self,
        func: Callable[[], Any],
        max_attempts: int | None = None,
        base_delay: float | None = None,
    ) -> Any:
        """Helper to execute func with retries and exponential backoff + jitter.
        - func: callable that performs network action and may raise exceptions
        - max_attempts: number of attempts including the first
        - base_delay: initial delay in seconds for backoff
        Behavior:
          * Uses for-loop for attempts (1..max_attempts)
          * Honors Retry-After header for 429 responses when available
          * Respects _max_delay
          * Uses injectable sleep function for testability
        """
        if max_attempts is None:
            max_attempts = self._max_retries
        if base_delay is None:
            base_delay = self._base_retry_delay

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except JIRAError as e:
                status_code = getattr(e, 'status_code', None)
                # Non-retryable client errors
                if status_code is not None and 400 <= int(status_code) < 500:
                    self._logger.error("Non-retryable JIRA error (status %s): %s", status_code, getattr(e, 'text', None))
                    raise

                last_exc = e
                # If this was the last attempt, re-raise
                if attempt >= max_attempts:
                    self._logger.error("JIRA error after %d attempts: %s", attempt, e)
                    raise

                # If the exception carries a Retry-After info, respect it
                retry_after = getattr(e, 'response', None)
                delay = None
                try:
                    # If the jira error wraps a requests.Response, attempt to read headers
                    resp = getattr(e, 'response', None)
                    if resp is not None:
                        ra = resp.headers.get('Retry-After') if hasattr(resp, 'headers') else None
                        if ra:
                            try:
                                delay = float(ra)
                            except Exception:
                                # could be a HTTP-date; fall back to backoff
                                delay = None
                except Exception:
                    delay = None

                if delay is None:
                    delay = min(self._max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, base_delay)

                self._logger.warning("Jira call failed (attempt %d/%d), retrying in %.2fs: %s", attempt, max_attempts, delay, e)
                self._sleep(delay)
            except Exception as e:
                # Generic exceptions (requests, timeouts)
                last_exc = e
                if attempt >= max_attempts:
                    self._logger.error("Network error after %d attempts: %s", attempt, e)
                    raise

                delay = min(self._max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, base_delay)
                self._logger.warning("Network call failed (attempt %d/%d): %s, retrying in %.2fs...", attempt, max_attempts, e, delay)
                self._sleep(delay)

        # If we exit loop, raise the last exception
        if last_exc:
            raise last_exc

    def open_issue_in_browser(self, issue_key: str):
        """
        Opens a Jira issue in the default web browser.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Jira.")
        
        try:
            import webbrowser
            # Construct the URL for the issue
            issue_url = f"{self.jira.server_url}/browse/{issue_key}"
            webbrowser.open(issue_url)
            print(f"Opened issue {issue_key} in browser: {issue_url}")
        except Exception as e:
            print(f"Error opening issue '{issue_key}' in browser: {e}")
            raise e
