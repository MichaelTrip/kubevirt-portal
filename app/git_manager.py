"""Thread-safe Git operations manager with transaction support."""

import os
import git
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Custom exception for Git operation failures."""
    pass


class GitOperationManager:
    """
    Thread-safe Git operations manager with transaction support.
    
    Provides atomic git operations with automatic rollback on failure.
    """

    def __init__(self, config: Config):
        """
        Initialize Git operation manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.lock = threading.RLock()  # Reentrant lock for nested calls
        self._repo = None
        self._repo_path = None
        
        logger.info("GitOperationManager initialized")

    def _get_auth_url(self) -> str:
        """
        Construct authenticated Git URL.
        
        Returns:
            Git URL with authentication credentials
        """
        repo_url = self.config.GIT_REPO_URL.rstrip('/')
        
        # Remove existing protocol
        if repo_url.startswith('https://'):
            repo_url = repo_url[8:]
        elif repo_url.startswith('http://'):
            repo_url = repo_url[7:]
        
        # Add authentication
        auth_url = f"https://{self.config.GIT_USERNAME}:{self.config.GIT_TOKEN}@{repo_url}"
        return auth_url

    def ensure_repository(self) -> Path:
        """
        Ensure repository is cloned and up to date.
        
        Returns:
            Path to repository directory
            
        Raises:
            GitOperationError: If repository operations fail
        """
        with self.lock:
            try:
                # Create storage directory
                os.makedirs(self.config.GIT_CLONE_DIR, exist_ok=True)
                repo_path = Path(self.config.GIT_CLONE_DIR) / 'repo'
                
                if (repo_path / '.git').exists():
                    logger.debug("Repository exists, pulling latest changes")
                    repo = git.Repo(repo_path)
                    
                    # Verify remote URL matches configuration
                    remote = repo.remotes.origin
                    if remote.url != self._get_auth_url():
                        logger.info("Remote URL changed, updating...")
                        remote.set_url(self._get_auth_url())
                    
                    # Pull latest changes
                    try:
                        repo.remotes.origin.pull()
                    except git.GitCommandError as e:
                        logger.warning(f"Pull failed, attempting reset: {e}")
                        # If pull fails, try to reset to origin
                        repo.git.reset('--hard', 'origin/main')
                else:
                    logger.info("Cloning repository")
                    try:
                        # Try to clone with main branch first
                        repo = git.Repo.clone_from(
                            self._get_auth_url(),
                            repo_path,
                            branch='main'
                        )
                    except git.GitCommandError as e:
                        # If main doesn't exist, try master or default branch
                        logger.warning(f"Failed to clone 'main' branch: {e}")
                        logger.info("Trying to clone default branch")
                        repo = git.Repo.clone_from(
                            self._get_auth_url(),
                            repo_path
                        )
                
                self._repo = repo
                self._repo_path = repo_path
                
                # Verify repository was cloned successfully
                if not repo.heads:
                    raise GitOperationError("Repository cloned but has no branches")
                
                logger.info(f"Repository ready at {repo_path}, active branch: {repo.active_branch.name if repo.heads else 'none'}")
                return repo_path
                
            except git.GitCommandError as e:
                logger.error(f"Git command error: {e}")
                raise GitOperationError(f"Git operation failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error ensuring repository: {e}")
                raise GitOperationError(f"Failed to ensure repository: {e}")

    @contextmanager
    def transaction(self, operation_name: str = "operation"):
        """
        Context manager for atomic Git operations with automatic rollback.
        
        Usage:
            with git_manager.transaction("create VM") as repo:
                # Make changes
                repo.index.add([file_path])
                
        Args:
            operation_name: Description of the operation for logging
            
        Yields:
            git.Repo: Repository instance
            
        Raises:
            GitOperationError: If operation fails
        """
        with self.lock:
            repo_path = self.ensure_repository()
            repo = git.Repo(repo_path)
            
            # Store original state
            original_head = None
            if repo.heads:
                original_head = repo.head.commit.hexsha
            
            logger.info(f"Starting transaction: {operation_name}")
            logger.debug(f"Repository dirty: {repo.is_dirty()}, Untracked files: {repo.untracked_files}")
            
            try:
                yield repo
                
                # Transaction successful, check if we need to push
                logger.debug(f"Transaction completed, checking for changes")
                
                # Check if HEAD moved (new commit was made)
                current_head = repo.head.commit.hexsha if repo.heads else None
                has_new_commits = original_head != current_head
                
                logger.debug(f"Original HEAD: {original_head}, Current HEAD: {current_head}")
                logger.debug(f"Has new commits: {has_new_commits}")
                logger.debug(f"Repository dirty: {repo.is_dirty()}, Untracked: {repo.untracked_files}")
                
                # Push if we have new commits OR uncommitted changes
                if has_new_commits or repo.is_dirty() or repo.untracked_files:
                    logger.info(f"Pushing changes for: {operation_name}")
                    push_info = repo.remote().push()
                    
                    # Check push result
                    for info in push_info:
                        if info.flags & info.ERROR:
                            raise GitOperationError(
                                f"Push failed: {info.summary}"
                            )
                        logger.info(f"Push successful: {info.summary}")
                else:
                    logger.info("No changes to push (repository clean and no new commits)")
                    
            except Exception as e:
                logger.error(f"Transaction failed for {operation_name}: {e}")
                
                # Rollback on error
                if original_head:
                    try:
                        logger.warning("Rolling back changes")
                        repo.git.reset('--hard', original_head)
                        repo.git.clean('-fd')
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}")
                
                # Re-raise the original exception
                if isinstance(e, GitOperationError):
                    raise
                else:
                    raise GitOperationError(f"Transaction failed: {e}")

    def commit_file(
        self, 
        file_path: str, 
        content: str, 
        commit_message: str,
        subdirectory: Optional[str] = None
    ) -> str:
        """
        Commit a file to the repository.
        
        Args:
            file_path: Name of the file
            content: File content
            commit_message: Commit message
            subdirectory: Optional subdirectory within repo
            
        Returns:
            Commit SHA
            
        Raises:
            GitOperationError: If commit fails
        """
        logger.info(f"Starting commit_file for: {file_path} in subdirectory: {subdirectory}")
        
        with self.transaction(f"commit {file_path}") as repo:
            repo_path = Path(repo.working_dir)
            logger.debug(f"Repository path: {repo_path}")
            logger.debug(f"Repository is valid: {repo.git_dir}")
            
            # Determine full file path
            if subdirectory:
                target_dir = repo_path / subdirectory
                target_dir.mkdir(parents=True, exist_ok=True)
                full_path = target_dir / file_path
                relative_path = str(Path(subdirectory) / file_path)
            else:
                full_path = repo_path / file_path
                relative_path = file_path
            
            # Write file
            logger.info(f"Writing file to: {full_path}")
            full_path.write_text(content)
            logger.info(f"File written successfully, size: {len(content)} bytes")
            
            # Stage and commit
            logger.info(f"Staging file: {relative_path}")
            repo.index.add([relative_path])
            
            # Check if there are changes to commit
            logger.debug("Checking for changes to commit")
            if repo.index.diff('HEAD'):
                logger.info("Changes detected, creating commit")
                commit = repo.index.commit(commit_message)
                logger.info(f"Created commit: {commit.hexsha}")
                return commit.hexsha
            else:
                logger.warning("No changes to commit (file might already exist with same content)")
                if repo.head.is_valid():
                    return repo.head.commit.hexsha
                else:
                    raise GitOperationError("No changes to commit and no HEAD commit exists")

    def delete_file(
        self, 
        file_path: str, 
        commit_message: str,
        subdirectory: Optional[str] = None
    ) -> str:
        """
        Delete a file from the repository.
        
        Args:
            file_path: Name of the file
            commit_message: Commit message
            subdirectory: Optional subdirectory within repo
            
        Returns:
            Commit SHA
            
        Raises:
            GitOperationError: If deletion fails
        """
        with self.transaction(f"delete {file_path}") as repo:
            repo_path = Path(repo.working_dir)
            
            # Determine full file path
            if subdirectory:
                full_path = repo_path / subdirectory / file_path
                relative_path = str(Path(subdirectory) / file_path)
            else:
                full_path = repo_path / file_path
                relative_path = file_path
            
            # Check if file exists
            if not full_path.exists():
                logger.warning(f"File does not exist: {full_path}")
                raise GitOperationError(f"File not found: {file_path}")
            
            # Remove file
            logger.debug(f"Removing file: {full_path}")
            full_path.unlink()
            repo.index.remove([relative_path])
            
            # Commit
            commit = repo.index.commit(commit_message)
            logger.info(f"Deleted file, commit: {commit.hexsha}")
            return commit.hexsha

    def read_file(
        self, 
        file_path: str, 
        subdirectory: Optional[str] = None
    ) -> str:
        """
        Read a file from the repository.
        
        Args:
            file_path: Name of the file
            subdirectory: Optional subdirectory within repo
            
        Returns:
            File content
            
        Raises:
            GitOperationError: If file doesn't exist
        """
        with self.lock:
            repo_path = self.ensure_repository()
            
            # Determine full file path
            if subdirectory:
                full_path = repo_path / subdirectory / file_path
            else:
                full_path = repo_path / file_path
            
            if not full_path.exists():
                raise GitOperationError(f"File not found: {file_path}")
            
            return full_path.read_text()

    def list_files(
        self, 
        subdirectory: Optional[str] = None, 
        extension: Optional[str] = None
    ) -> list:
        """
        List files in the repository.
        
        Args:
            subdirectory: Optional subdirectory to list
            extension: Optional file extension filter
            
        Returns:
            List of file paths
        """
        with self.lock:
            repo_path = self.ensure_repository()
            
            # Determine directory to list
            if subdirectory:
                target_dir = repo_path / subdirectory
            else:
                target_dir = repo_path
            
            if not target_dir.exists():
                logger.warning(f"Directory does not exist: {target_dir}")
                return []
            
            # List files
            files = []
            for file_path in target_dir.iterdir():
                if file_path.is_file():
                    if extension is None or file_path.suffix == extension:
                        files.append(file_path.name)
            
            return sorted(files)

    def get_repository_status(self) -> Dict[str, Any]:
        """
        Get current repository status.
        
        Returns:
            Dictionary with repository status information
        """
        with self.lock:
            try:
                repo_path = self.ensure_repository()
                repo = git.Repo(repo_path)
                
                return {
                    'is_dirty': repo.is_dirty(),
                    'untracked_files': repo.untracked_files,
                    'active_branch': repo.active_branch.name if repo.heads else None,
                    'latest_commit': repo.head.commit.hexsha if repo.heads else None,
                    'remote_url': repo.remotes.origin.url if repo.remotes else None
                }
            except Exception as e:
                logger.error(f"Error getting repository status: {e}")
                return {'error': str(e)}
