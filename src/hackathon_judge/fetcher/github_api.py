"""GitHub API client for fetching repository metadata."""

import os
import re
import time
from typing import Optional

import requests

from hackathon_judge.config import GITHUB_API_BASE, GITHUB_RATE_LIMIT_PAUSE
from hackathon_judge.models import RepoMetadata


class GitHubAPI:
    """Client for GitHub REST API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.session = requests.Session()
        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
        self.session.headers['Accept'] = 'application/vnd.github.v3+json'
        self.session.headers['User-Agent'] = 'HackathonJudge/1.0'

    def _parse_repo_url(self, url: str) -> tuple[str, str] | None:
        """Extract owner and repo name from GitHub URL."""
        patterns = [
            r'github\.com/([^/]+)/([^/\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Clean repo name
                repo = repo.rstrip('/')
                repo = re.sub(r'\.git$', '', repo)
                return owner, repo

        return None

    def _handle_rate_limit(self, response: requests.Response) -> bool:
        """Handle rate limiting. Returns True if we should retry."""
        if response.status_code == 403:
            remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if remaining == '0':
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(reset_time - time.time(), GITHUB_RATE_LIMIT_PAUSE)
                time.sleep(min(wait_time, GITHUB_RATE_LIMIT_PAUSE))
                return True
        return False

    def get_repo_metadata(self, github_url: str) -> RepoMetadata:
        """Fetch repository metadata from GitHub API."""
        parsed = self._parse_repo_url(github_url)

        if not parsed:
            return RepoMetadata(
                owner="",
                repo_name="",
                is_accessible=False,
                error=f"Could not parse GitHub URL: {github_url}"
            )

        owner, repo = parsed

        try:
            # Get repository info
            response = self.session.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")

            if self._handle_rate_limit(response):
                response = self.session.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")

            if response.status_code == 404:
                return RepoMetadata(
                    owner=owner,
                    repo_name=repo,
                    is_accessible=False,
                    error="Repository not found or is private"
                )

            if response.status_code != 200:
                return RepoMetadata(
                    owner=owner,
                    repo_name=repo,
                    is_accessible=False,
                    error=f"API error: {response.status_code}"
                )

            data = response.json()

            return RepoMetadata(
                owner=owner,
                repo_name=repo,
                default_branch=data.get('default_branch', 'main'),
                stars=data.get('stargazers_count', 0),
                forks=data.get('forks_count', 0),
                created_at=data.get('created_at'),
                pushed_at=data.get('pushed_at'),
                language=data.get('language'),
                topics=data.get('topics', []),
                has_readme=True,  # Will be checked later
                has_license=data.get('license') is not None,
                is_accessible=True,
            )

        except requests.RequestException as e:
            return RepoMetadata(
                owner=owner,
                repo_name=repo,
                is_accessible=False,
                error=f"Request error: {str(e)}"
            )

    def get_repo_contents(self, owner: str, repo: str, path: str = "") -> list[dict]:
        """Get repository contents at a given path."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
            response = self.session.get(url)

            if self._handle_rate_limit(response):
                response = self.session.get(url)

            if response.status_code != 200:
                return []

            return response.json()

        except requests.RequestException:
            return []

    def get_file_content(self, owner: str, repo: str, path: str) -> str | None:
        """Get content of a specific file."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
            response = self.session.get(url)

            if self._handle_rate_limit(response):
                response = self.session.get(url)

            if response.status_code != 200:
                return None

            data = response.json()
            if data.get('encoding') == 'base64':
                import base64
                return base64.b64decode(data['content']).decode('utf-8', errors='replace')

            return data.get('content')

        except (requests.RequestException, Exception):
            return None

    def get_commits(self, owner: str, repo: str, since: str | None = None,
                    until: str | None = None, per_page: int = 100) -> list[dict]:
        """Get repository commits."""
        try:
            params = {'per_page': per_page}
            if since:
                params['since'] = since
            if until:
                params['until'] = until

            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
            response = self.session.get(url, params=params)

            if self._handle_rate_limit(response):
                response = self.session.get(url, params=params)

            if response.status_code != 200:
                return []

            return response.json()

        except requests.RequestException:
            return []

    def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Get repository languages."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
            response = self.session.get(url)

            if self._handle_rate_limit(response):
                response = self.session.get(url)

            if response.status_code != 200:
                return {}

            return response.json()

        except requests.RequestException:
            return {}
