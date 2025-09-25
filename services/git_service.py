#!/usr/bin/env python3

"""
Git service for managing note history and versioning.
This service handles git operations for note content versioning.
"""

import os
import subprocess
import tempfile
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import hashlib


class GitService:
    """Service to manage git operations for note versioning."""
    
    def __init__(self, repo_path: str = None):
        """Initialize GitService with optional repository path."""
        self.repo_path = repo_path or os.path.join(os.path.expanduser("~"), ".jira_notes_git")
        self.ensure_git_repo()
    
    def ensure_git_repo(self):
        """Ensure git repository exists and is initialized."""
        try:
            if not os.path.exists(self.repo_path):
                os.makedirs(self.repo_path, exist_ok=True)
            
            # Check if it's already a git repo
            if not os.path.exists(os.path.join(self.repo_path, '.git')):
                subprocess.run(['git', 'init'], cwd=self.repo_path, check=True, capture_output=True)
                
                # Set up initial commit
                subprocess.run(['git', 'config', 'user.name', 'Jira Notes'], cwd=self.repo_path, check=True)
                subprocess.run(['git', 'config', 'user.email', 'notes@jira-tracker.local'], cwd=self.repo_path, check=True)
                
                # Create initial commit
                readme_path = os.path.join(self.repo_path, 'README.md')
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write('# Jira Notes Repository\\n\\nThis repository stores versioned notes for Jira tickets.')
                
                subprocess.run(['git', 'add', 'README.md'], cwd=self.repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.repo_path, check=True)
                
        except subprocess.CalledProcessError as e:
            print(f"Error initializing git repository: {e}")
        except Exception as e:
            print(f"Unexpected error initializing git repository: {e}")
    
    def _get_note_filename(self, jira_key: str, note_title: str) -> str:
        """Generate a safe filename for the note."""
        # Create a safe filename by removing/replacing invalid characters
        safe_key = "".join(c for c in jira_key if c.isalnum() or c in ".-_").strip()
        safe_title = "".join(c for c in note_title if c.isalnum() or c in " .-_").strip()
        safe_title = safe_title.replace(' ', '_')
        
        # Limit length and add hash if too long
        filename = f"{safe_key}_{safe_title}.md"
        if len(filename) > 100:
            # Use hash for very long titles
            title_hash = hashlib.md5(note_title.encode('utf-8')).hexdigest()[:8]
            filename = f"{safe_key}_{title_hash}.md"
        
        return filename
    
    def save_note_content(self, jira_key: str, note_title: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Save note content to git repository and return the file path."""
        try:
            filename = self._get_note_filename(jira_key, note_title)
            file_path = os.path.join(self.repo_path, filename)
            
            # Create note content with metadata
            note_content = self._format_note_content(content, metadata or {})
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(note_content)
            
            return file_path
        except Exception as e:
            print(f"Error saving note content: {e}")
            return None
    
    def _format_note_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Format note content with metadata header."""
        header = "---\\n"
        header += f"jira_key: {metadata.get('jira_key', '')}\\n"
        header += f"title: {metadata.get('title', '')}\\n"
        header += f"tags: {metadata.get('tags', '')}\\n"
        header += f"created_at: {metadata.get('created_at', '')}\\n"
        header += f"updated_at: {datetime.now(timezone.utc).isoformat()}\\n"
        header += f"is_fictitious: {metadata.get('is_fictitious', False)}\\n"
        header += "---\\n\\n"
        
        return header + content
    
    def commit_note(self, jira_key: str, note_title: str, content: str, metadata: Dict[str, Any] = None, custom_message: str = None) -> Optional[str]:
        """Commit note changes and return commit hash."""
        try:
            file_path = self.save_note_content(jira_key, note_title, content, metadata)
            if not file_path:
                return None
            
            filename = os.path.basename(file_path)
            
            # Stage the file
            subprocess.run(['git', 'add', filename], cwd=self.repo_path, check=True)
            
            # Check if there are changes to commit
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], 
                                  cwd=self.repo_path, capture_output=True)
            if result.returncode == 0:  # No changes
                return self.get_latest_commit_hash()
            
            # Commit the changes with custom or default message
            if custom_message:
                commit_message = f"{custom_message} ({jira_key} - {note_title})"
            else:
                commit_message = f"Update note: {jira_key} - {note_title}"
            subprocess.run(['git', 'commit', '-m', commit_message], 
                          cwd=self.repo_path, check=True)
            
            return self.get_latest_commit_hash()
            
        except subprocess.CalledProcessError as e:
            print(f"Error committing note: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error committing note: {e}")
            return None
    
    def get_latest_commit_hash(self) -> Optional[str]:
        """Get the hash of the latest commit."""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  cwd=self.repo_path, 
                                  check=True, 
                                  capture_output=True, 
                                  text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def get_note_history(self, jira_key: str, note_title: str) -> list:
        """Get commit history for a specific note."""
        try:
            filename = self._get_note_filename(jira_key, note_title)
            file_path = os.path.join(self.repo_path, filename)
            
            if not os.path.exists(file_path):
                return []
            
            # Get git log for the file
            result = subprocess.run(['git', 'log', '--oneline', filename], 
                                  cwd=self.repo_path, 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            history = []
            for line in result.stdout.strip().split('\\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        commit_hash = parts[0]
                        message = parts[1]
                        history.append({
                            'commit_hash': commit_hash,
                            'message': message
                        })
            
            return history
        except subprocess.CalledProcessError:
            return []
    
    def get_note_at_commit(self, jira_key: str, note_title: str, commit_hash: str) -> Optional[str]:
        """Get note content at a specific commit."""
        try:
            filename = self._get_note_filename(jira_key, note_title)
            
            result = subprocess.run(['git', 'show', f'{commit_hash}:{filename}'], 
                                  cwd=self.repo_path, 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            content = result.stdout
            
            # Extract content without metadata header
            if content.startswith('---\\n'):
                parts = content.split('---\\n', 2)
                if len(parts) >= 3:
                    return parts[2]  # Content after second ---
            
            return content
        except subprocess.CalledProcessError:
            return None
    
    def is_git_available(self) -> bool:
        """Check if git is available on the system."""
        try:
            subprocess.run(['git', '--version'], 
                          capture_output=True, 
                          check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_repo_status(self) -> Dict[str, Any]:
        """Get repository status information."""
        try:
            if not os.path.exists(self.repo_path):
                return {'status': 'not_initialized', 'git_available': self.is_git_available()}
            
            # Check if git repo exists
            if not os.path.exists(os.path.join(self.repo_path, '.git')):
                return {'status': 'not_git_repo', 'git_available': self.is_git_available()}
            
            # Get number of commits
            result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                                  cwd=self.repo_path, 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            commit_count = int(result.stdout.strip())
            
            # Get latest commit info
            latest_hash = self.get_latest_commit_hash()
            
            return {
                'status': 'ready',
                'git_available': True,
                'repo_path': self.repo_path,
                'commit_count': commit_count,
                'latest_commit': latest_hash
            }
            
        except subprocess.CalledProcessError:
            return {'status': 'error', 'git_available': self.is_git_available()}
        except Exception:
            return {'status': 'error', 'git_available': self.is_git_available()}
    
    def get_commit_date(self, commit_hash: str) -> Optional[str]:
        """Get the commit date for a specific commit hash."""
        try:
            result = subprocess.run(['git', 'show', '-s', '--format=%ci', commit_hash], 
                                  cwd=self.repo_path, 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            # Format: 2024-01-15 10:30:45 +0100
            # Convert to ISO format
            date_str = result.stdout.strip()
            if date_str:
                # Parse and convert to ISO format
                from datetime import datetime
                dt = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
                return dt.isoformat()
            return None
        except subprocess.CalledProcessError:
            return None