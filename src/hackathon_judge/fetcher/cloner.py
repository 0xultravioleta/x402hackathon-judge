"""Repository cloner using GitPython."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError

from hackathon_judge.config import CLONE_TIMEOUT


class RepoCloner:
    """Clone and manage temporary repository copies."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "hackathon_judge_repos"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, owner: str, repo: str) -> Path:
        """Get cache path for a repository."""
        return self.cache_dir / f"{owner}_{repo}"

    def clone(self, github_url: str, force_fresh: bool = False) -> tuple[Optional[Path], Optional[str]]:
        """Clone a repository. Returns (path, error)."""
        # Parse owner/repo from URL
        import re
        match = re.search(r'github\.com/([^/]+)/([^/\s]+)', github_url)
        if not match:
            return None, f"Could not parse URL: {github_url}"

        owner = match.group(1)
        repo = match.group(2).rstrip('/').replace('.git', '')

        cache_path = self._get_cache_path(owner, repo)

        # Check if already cloned
        if cache_path.exists() and not force_fresh:
            try:
                Repo(cache_path)
                return cache_path, None
            except:
                # Invalid repo, remove and reclone
                shutil.rmtree(cache_path, ignore_errors=True)

        # Remove existing if forcing fresh
        if cache_path.exists() and force_fresh:
            shutil.rmtree(cache_path, ignore_errors=True)

        # Clone
        try:
            clone_url = f"https://github.com/{owner}/{repo}.git"
            Repo.clone_from(
                clone_url,
                cache_path,
                depth=100,  # Shallow clone with some history
                single_branch=True,
            )
            return cache_path, None

        except GitCommandError as e:
            shutil.rmtree(cache_path, ignore_errors=True)
            return None, f"Clone failed: {str(e)}"
        except Exception as e:
            shutil.rmtree(cache_path, ignore_errors=True)
            return None, f"Clone error: {str(e)}"

    def get_repo(self, path: Path) -> Optional[Repo]:
        """Get a Repo object for a cloned repository."""
        try:
            return Repo(path)
        except:
            return None

    def cleanup(self, owner: str, repo: str):
        """Remove a cached repository."""
        cache_path = self._get_cache_path(owner, repo)
        if cache_path.exists():
            shutil.rmtree(cache_path, ignore_errors=True)

    def cleanup_all(self):
        """Remove all cached repositories."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
