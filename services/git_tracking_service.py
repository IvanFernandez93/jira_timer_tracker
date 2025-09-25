"""
Git-based Issue Tracking Service

This service tracks Jira issue changes using Git version control,
creating a much more robust and queryable history than database logs.
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QStandardPaths

_logger = logging.getLogger('JiraTimeTracker.GitTracking')

class GitTrackingService:
    """Service to track Jira issue changes using Git version control."""
    
    def __init__(self):
        """Initialize Git tracking service."""
        # Use same directory as database (AppDataLocation)
        data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        self.workspace_path = Path(data_dir)
        self.tracking_dir = self.workspace_path / '.jira_tracking'
        self.issues_dir = self.tracking_dir / 'issues'
        
        # Ensure directories exist
        self.tracking_dir.mkdir(exist_ok=True)
        self.issues_dir.mkdir(exist_ok=True)
        
        # Initialize Git repository if needed
        self._ensure_git_repo()
        
    def _ensure_git_repo(self):
        """Ensure the tracking directory is a Git repository."""
        git_dir = self.tracking_dir / '.git'
        
        if not git_dir.exists():
            # Initialize Git repository
            try:
                subprocess.run([
                    'git', 'init'
                ], cwd=self.tracking_dir, check=True, capture_output=True)
                
                # Configure Git for automated commits
                subprocess.run([
                    'git', 'config', 'user.name', 'Jira Tracker Bot'
                ], cwd=self.tracking_dir, check=True, capture_output=True)
                
                subprocess.run([
                    'git', 'config', 'user.email', 'jira-tracker@localhost'
                ], cwd=self.tracking_dir, check=True, capture_output=True)
                
                # Create initial .gitignore
                gitignore_path = self.tracking_dir / '.gitignore'
                gitignore_path.write_text(
                    "# Temporary files\n"
                    "*.tmp\n"
                    "*.log\n\n"
                    "# OS files\n"
                    ".DS_Store\n"
                    "Thumbs.db\n"
                )
                
                # Create initial README
                readme_path = self.tracking_dir / 'README.md'
                readme_path.write_text(
                    "# Jira Issue Tracking History\n\n"
                    "This repository contains the version history of Jira issues tracked by the Jira Timer Tracker application.\n\n"
                    "## Structure\n\n"
                    "- `issues/`: Contains JSON files for each tracked issue\n"
                    "- Each file is named `{ISSUE-KEY}.json`\n"
                    "- Git history shows all changes over time\n\n"
                    "## Usage\n\n"
                    "Use `git log --oneline` to see all changes.\n"
                    "Use `git show {commit}` to see specific changes.\n"
                    "Use `git log -p issues/{ISSUE-KEY}.json` to see history of specific issue.\n"
                )
                
                # Initial commit
                subprocess.run([
                    'git', 'add', '.'
                ], cwd=self.tracking_dir, check=True, capture_output=True)
                
                subprocess.run([
                    'git', 'commit', '-m', 'Initial commit: Jira issue tracking setup'
                ], cwd=self.tracking_dir, check=True, capture_output=True)
                
                _logger.info(f"Initialized Git repository for issue tracking at {self.tracking_dir}")
                
            except subprocess.CalledProcessError as e:
                _logger.error(f"Failed to initialize Git repository: {e}")
                raise
    
    def _run_git_command(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a git command in the tracking directory."""
        try:
            return subprocess.run(
                ['git'] + args,
                cwd=self.tracking_dir,
                check=True,
                capture_output=True,
                text=True,
                **kwargs
            )
        except subprocess.CalledProcessError as e:
            _logger.error(f"Git command failed: git {' '.join(args)}\n{e.stderr}")
            raise
    
    def track_issue_changes(self, jira_key: str, issue_data: Dict[str, Any]) -> bool:
        """
        Track changes to a Jira issue using Git.
        
        Returns True if changes were detected and committed, False otherwise.
        """
        if not issue_data:
            return False
        
        try:
            # Extract trackable data
            fields = issue_data.get('fields', {})
            
            trackable_data = {
                'jira_key': jira_key,
                'summary': fields.get('summary', ''),
                'description': fields.get('description', ''),
                'status': {
                    'name': fields.get('status', {}).get('name', ''),
                    'id': fields.get('status', {}).get('id', '')
                },
                'priority': {
                    'name': fields.get('priority', {}).get('name', ''),
                    'id': fields.get('priority', {}).get('id', '')
                },
                'assignee': {
                    'displayName': fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else '',
                    'emailAddress': fields.get('assignee', {}).get('emailAddress', '') if fields.get('assignee') else ''
                },
                'reporter': {
                    'displayName': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else '',
                    'emailAddress': fields.get('reporter', {}).get('emailAddress', '') if fields.get('reporter') else ''
                },
                'issuetype': {
                    'name': fields.get('issuetype', {}).get('name', ''),
                    'id': fields.get('issuetype', {}).get('id', '')
                },
                'created': fields.get('created', ''),
                'updated': fields.get('updated', ''),
                'resolution': {
                    'name': fields.get('resolution', {}).get('name', '') if fields.get('resolution') else '',
                    'id': fields.get('resolution', {}).get('id', '') if fields.get('resolution') else ''
                },
                'labels': fields.get('labels', []),
                'components': [
                    {'name': comp.get('name', ''), 'id': comp.get('id', '')}
                    for comp in fields.get('components', [])
                ],
                'fixVersions': [
                    {'name': ver.get('name', ''), 'id': ver.get('id', '')}
                    for ver in fields.get('fixVersions', [])
                ],
                'versions': [
                    {'name': ver.get('name', ''), 'id': ver.get('id', '')}
                    for ver in fields.get('versions', [])
                ],
                'last_tracked': datetime.now().isoformat(),
                'tracking_metadata': {
                    'tracked_by': 'jira-timer-tracker',
                    'version': '1.0'
                }
            }
            
            # File path for this issue
            issue_file = self.issues_dir / f"{jira_key}.json"
            
            # Check if file exists and if content has changed
            content_changed = True
            if issue_file.exists():
                try:
                    existing_data = json.loads(issue_file.read_text(encoding='utf-8'))
                    # Remove timestamp for comparison
                    existing_copy = existing_data.copy()
                    current_copy = trackable_data.copy()
                    existing_copy.pop('last_tracked', None)
                    current_copy.pop('last_tracked', None)
                    
                    if existing_copy == current_copy:
                        content_changed = False
                except (json.JSONDecodeError, KeyError):
                    # If we can't read/parse existing file, assume it changed
                    content_changed = True
            
            if not content_changed:
                _logger.debug(f"No changes detected for {jira_key}")
                return False
            
            # Write updated data
            issue_file.write_text(
                json.dumps(trackable_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            # Stage the file
            self._run_git_command(['add', f'issues/{jira_key}.json'])
            
            # Check if there are any changes to commit
            result = self._run_git_command(['status', '--porcelain'])
            if not result.stdout.strip():
                _logger.debug(f"No Git changes to commit for {jira_key}")
                return False
            
            # Create commit message based on changes
            commit_msg = self._generate_commit_message(jira_key, trackable_data, issue_file)
            
            # Commit the changes
            self._run_git_command(['commit', '-m', commit_msg])
            
            _logger.info(f"Tracked changes for {jira_key} in Git")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to track changes for {jira_key}: {e}")
            return False
    
    def _generate_commit_message(self, jira_key: str, current_data: Dict[str, Any], issue_file: Path) -> str:
        """Generate a descriptive commit message based on changes."""
        try:
            # Try to get the previous version to compare
            result = self._run_git_command(['show', 'HEAD:' + str(issue_file.relative_to(self.tracking_dir))])
            previous_data = json.loads(result.stdout)
            
            changes = []
            
            # Compare key fields
            comparisons = [
                ('summary', 'Summary'),
                ('status.name', 'Status'),
                ('priority.name', 'Priority'), 
                ('assignee.displayName', 'Assignee'),
                ('description', 'Description')
            ]
            
            for field_path, display_name in comparisons:
                old_val = self._get_nested_value(previous_data, field_path)
                new_val = self._get_nested_value(current_data, field_path)
                
                if old_val != new_val:
                    if display_name == 'Description':
                        # For description, just note it changed (too long for commit msg)
                        changes.append(f"{display_name} updated")
                    else:
                        changes.append(f"{display_name}: '{old_val}' → '{new_val}'")
            
            if changes:
                return f"Update {jira_key}: {'; '.join(changes[:3])}" + ("..." if len(changes) > 3 else "")
            else:
                return f"Update {jira_key}: Fields updated"
                
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            # Fallback for new issues or errors
            return f"Track {jira_key}: {current_data.get('summary', 'Issue updated')}"
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> str:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return ''
        
        return str(current) if current is not None else ''
    
    def get_issue_history(self, jira_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the Git history for a specific issue."""
        try:
            issue_file = f'issues/{jira_key}.json'
            
            # Get Git log for the specific file
            result = self._run_git_command([
                'log', '--oneline', f'-{limit}', '--', issue_file
            ])
            
            history = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    commit_hash, *message_parts = line.split(' ', 1)
                    message = message_parts[0] if message_parts else ''
                    
                    # Get commit details
                    commit_result = self._run_git_command([
                        'show', '--format=%ai|%an|%ae', '--name-only', commit_hash
                    ])
                    
                    lines = commit_result.stdout.strip().split('\n')
                    if lines:
                        date_author_email = lines[0].split('|')
                        if len(date_author_email) == 3:
                            history.append({
                                'commit': commit_hash,
                                'message': message,
                                'date': date_author_email[0],
                                'author': date_author_email[1],
                                'email': date_author_email[2]
                            })
            
            return history
            
        except subprocess.CalledProcessError as e:
            _logger.error(f"Failed to get history for {jira_key}: {e}")
            return []
    
    def get_issue_changes(self, jira_key: str, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get the specific changes made in a commit for an issue."""
        try:
            issue_file = f'issues/{jira_key}.json'
            
            # Get the diff for this commit
            result = self._run_git_command([
                'show', commit_hash, '--', issue_file
            ])
            
            return {
                'commit': commit_hash,
                'diff': result.stdout,
                'file': issue_file
            }
            
        except subprocess.CalledProcessError as e:
            _logger.error(f"Failed to get changes for {jira_key} at {commit_hash}: {e}")
            return None
    
    def get_current_issue_data(self, jira_key: str) -> Optional[Dict[str, Any]]:
        """Get the current tracked data for an issue."""
        try:
            issue_file = self.issues_dir / f"{jira_key}.json"
            if issue_file.exists():
                return json.loads(issue_file.read_text(encoding='utf-8'))
            return None
        except (json.JSONDecodeError, IOError) as e:
            _logger.error(f"Failed to read current data for {jira_key}: {e}")
            return None
    
    def cleanup_old_tracking(self, days: int = 365) -> int:
        """Clean up tracking data older than specified days (optional maintenance)."""
        # This could be implemented to archive very old commits to keep the repo size manageable
        # For now, we'll keep all history as it's usually not too large
        return 0
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get statistics about the tracking repository."""
        try:
            # Count total commits
            commit_result = self._run_git_command(['rev-list', '--count', 'HEAD'])
            total_commits = int(commit_result.stdout.strip())
            
            # Count tracked issues
            issues_count = len(list(self.issues_dir.glob('*.json')))
            
            # Get repository size
            repo_size = sum(f.stat().st_size for f in self.tracking_dir.rglob('*') if f.is_file())
            
            return {
                'total_commits': total_commits,
                'tracked_issues': issues_count,
                'repository_size_bytes': repo_size,
                'tracking_directory': str(self.tracking_dir)
            }
            
        except (subprocess.CalledProcessError, ValueError) as e:
            _logger.error(f"Failed to get repository stats: {e}")
            return {
                'total_commits': 0,
                'tracked_issues': 0,
                'repository_size_bytes': 0,
                'tracking_directory': str(self.tracking_dir)
            }
    
    def get_tracking_directory(self) -> str:
        """Get the path to the Git tracking directory."""
        return str(self.tracking_dir)