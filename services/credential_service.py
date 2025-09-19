import keyring
import sys

class CredentialService:
    """
    Manages secure storage and retrieval of credentials using the OS keyring.
    Fulfills requirement 4.3.
    """
    SERVICE_NAME = "JiraTimeTracker"

    def set_pat(self, jira_url: str, pat: str):
        """Saves the Personal Access Token for a given Jira URL."""
        try:
            keyring.set_password(self.SERVICE_NAME, jira_url, pat)
        except Exception as e:
            # Handle potential keyring errors (e.g., on headless systems)
            print(f"Error saving to keyring: {e}", file=sys.stderr)

    def get_pat(self, jira_url: str) -> str | None:
        """Retrieves the Personal Access Token for a given Jira URL."""
        if not jira_url:
            return None
        try:
            return keyring.get_password(self.SERVICE_NAME, jira_url)
        except Exception as e:
            print(f"Error retrieving from keyring: {e}", file=sys.stderr)
            return None

    def delete_pat(self, jira_url: str):
        """Deletes the Personal Access Token for a given Jira URL."""
        try:
            keyring.delete_password(self.SERVICE_NAME, jira_url)
        except keyring.errors.PasswordDeleteError:
            # This can happen if the password doesn't exist, which is fine.
            pass
        except Exception as e:
            print(f"Error deleting from keyring: {e}", file=sys.stderr)
