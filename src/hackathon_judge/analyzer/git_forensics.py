"""Git forensics analyzer for timeline validation."""

from datetime import datetime, date
from pathlib import Path
from typing import Optional

from git import Repo

from hackathon_judge.config import TIME_WINDOW
from hackathon_judge.models import ForensicsResult
from hackathon_judge.fetcher import GitHubAPI


class GitForensics:
    """Validate hackathon timeline and detect history manipulation."""

    def __init__(self, github_api: GitHubAPI, time_window=None):
        self.api = github_api
        self.window = time_window or TIME_WINDOW

    def analyze(self, project_id: str, github_url: str,
                local_path: Optional[Path] = None) -> ForensicsResult:
        """Analyze git history for timeline compliance."""
        result = ForensicsResult(project_id=project_id)

        try:
            if local_path and local_path.exists():
                return self._analyze_local(result, local_path)
            else:
                return self._analyze_remote(result, github_url)
        except Exception as e:
            result.error = str(e)
            result.verdict = "UNKNOWN"
            return result

    def _analyze_local(self, result: ForensicsResult, path: Path) -> ForensicsResult:
        """Analyze local git repository."""
        try:
            repo = Repo(path)
        except Exception as e:
            result.error = f"Could not open repo: {e}"
            result.verdict = "UNKNOWN"
            return result

        # Get all commits
        try:
            commits = list(repo.iter_commits('HEAD', max_count=500))
        except Exception as e:
            result.error = f"Could not read commits: {e}"
            result.verdict = "UNKNOWN"
            return result

        result.total_commits = len(commits)

        # Parse window dates
        window_start = datetime.combine(self.window.start, datetime.min.time())
        window_end = datetime.combine(self.window.end, datetime.max.time())

        in_window = []
        before_window = []

        for commit in commits:
            commit_date = datetime.fromtimestamp(commit.committed_date)

            if commit_date < window_start:
                before_window.append({
                    'sha': commit.hexsha[:7],
                    'date': commit_date.isoformat(),
                    'message': commit.message.split('\n')[0][:50],
                })
            elif commit_date <= window_end:
                in_window.append(commit)

        result.commits_in_window = len(in_window)
        result.commits_before_window = len(before_window)
        result.pre_window_commits = before_window[:10]  # Keep first 10

        # Analyze patterns
        result.timeline_flags = self._analyze_patterns(commits, in_window, before_window)

        # Calculate lines added
        result.lines_added_in_window = self._estimate_lines_added(in_window)
        result.lines_before_window = self._estimate_lines_added_commits(before_window, repo)

        # Determine development pattern
        result.development_pattern = self._classify_pattern(result)

        # Make verdict
        result.verdict, result.confidence = self._make_verdict(result)

        # Add notes
        result.notes = self._generate_notes(result)

        return result

    def _analyze_remote(self, result: ForensicsResult, github_url: str) -> ForensicsResult:
        """Analyze via GitHub API."""
        import re
        match = re.search(r'github\.com/([^/]+)/([^/\s]+)', github_url)
        if not match:
            result.error = f"Could not parse URL: {github_url}"
            result.verdict = "UNKNOWN"
            return result

        owner = match.group(1)
        repo = match.group(2).rstrip('/').replace('.git', '')

        # Get all commits
        commits = self.api.get_commits(owner, repo, per_page=100)
        if not commits:
            result.notes = "Could not fetch commits from API"
            result.verdict = "UNKNOWN"
            return result

        result.total_commits = len(commits)

        # Parse window dates
        window_start = self.window.start.isoformat() + "T00:00:00Z"
        window_end = self.window.end.isoformat() + "T23:59:59Z"

        in_window = []
        before_window = []

        for commit in commits:
            commit_info = commit.get('commit', {})
            date_str = commit_info.get('committer', {}).get('date', '')

            if date_str:
                if date_str < window_start:
                    before_window.append({
                        'sha': commit.get('sha', '')[:7],
                        'date': date_str,
                        'message': commit_info.get('message', '')[:50],
                    })
                elif date_str <= window_end:
                    in_window.append(commit)

        result.commits_in_window = len(in_window)
        result.commits_before_window = len(before_window)
        result.pre_window_commits = before_window[:10]

        # Simplified pattern analysis
        result.timeline_flags = {
            'history_manipulation_suspected': False,
            'bulk_initial_commit': result.commits_in_window == 1 and result.total_commits <= 3,
            'author_committer_mismatch': False,
            'suspicious_patterns': [],
        }

        # Determine pattern
        if result.commits_before_window > result.commits_in_window:
            result.development_pattern = "likely_pre-existing"
        elif result.commits_in_window >= 5:
            result.development_pattern = "organic"
        else:
            result.development_pattern = "suspicious"

        # Verdict
        result.verdict, result.confidence = self._make_verdict(result)
        result.notes = self._generate_notes(result)

        return result

    def _analyze_patterns(self, all_commits, in_window, before_window) -> dict:
        """Analyze commit patterns for manipulation signs."""
        flags = {
            'history_manipulation_suspected': False,
            'bulk_initial_commit': False,
            'author_committer_mismatch': False,
            'suspicious_patterns': [],
        }

        if not in_window:
            return flags

        # Check for bulk initial commit
        first_commit = in_window[-1] if in_window else None
        if first_commit:
            try:
                stats = first_commit.stats.total
                if stats.get('insertions', 0) > 5000:
                    flags['bulk_initial_commit'] = True
                    flags['suspicious_patterns'].append("Large initial commit (>5000 lines)")
            except:
                pass

        # Check for author/committer date mismatch
        mismatches = 0
        for commit in in_window[:20]:
            try:
                author_date = datetime.fromtimestamp(commit.authored_date)
                committer_date = datetime.fromtimestamp(commit.committed_date)
                diff = abs((author_date - committer_date).total_seconds())
                if diff > 86400:  # More than 1 day difference
                    mismatches += 1
            except:
                pass

        if mismatches > 3:
            flags['author_committer_mismatch'] = True
            flags['suspicious_patterns'].append("Author/committer date mismatches detected")

        # Check for identical committer dates (batch rebase)
        committer_dates = []
        for commit in in_window[:20]:
            try:
                committer_dates.append(commit.committed_date)
            except:
                pass

        if len(set(committer_dates)) < len(committer_dates) / 2 and len(committer_dates) > 5:
            flags['history_manipulation_suspected'] = True
            flags['suspicious_patterns'].append("Many commits with identical timestamps")

        return flags

    def _estimate_lines_added(self, commits) -> int:
        """Estimate total lines added from commits."""
        total = 0
        for commit in commits[:50]:
            try:
                stats = commit.stats.total
                total += stats.get('insertions', 0)
            except:
                pass
        return total

    def _estimate_lines_added_commits(self, commit_list, repo) -> int:
        """Estimate lines from commit list (with SHA)."""
        total = 0
        for item in commit_list[:10]:
            try:
                sha = item.get('sha', '')
                if sha:
                    commit = repo.commit(sha)
                    stats = commit.stats.total
                    total += stats.get('insertions', 0)
            except:
                pass
        return total

    def _classify_pattern(self, result: ForensicsResult) -> str:
        """Classify the development pattern."""
        if result.commits_before_window > result.commits_in_window * 2:
            return "likely_pre-existing"

        if result.timeline_flags.get('history_manipulation_suspected'):
            return "suspicious"

        if result.timeline_flags.get('bulk_initial_commit') and result.commits_in_window < 5:
            return "suspicious"

        if result.commits_in_window >= 10:
            return "organic"

        if result.commits_in_window >= 3:
            return "organic"

        return "suspicious"

    def _make_verdict(self, result: ForensicsResult) -> tuple[str, float]:
        """Make final verdict."""
        if result.commits_before_window == 0:
            if result.development_pattern == "organic":
                return "VALID", 0.9
            elif result.development_pattern == "suspicious":
                return "QUESTIONABLE", 0.6
            else:
                return "VALID", 0.8

        if result.development_pattern == "likely_pre-existing":
            return "QUESTIONABLE", 0.7

        # Some pre-window commits but mostly during window
        ratio = result.commits_in_window / max(result.total_commits, 1)
        if ratio >= 0.8:
            return "VALID", 0.8
        elif ratio >= 0.5:
            return "QUESTIONABLE", 0.6
        else:
            return "QUESTIONABLE", 0.5

    def _generate_notes(self, result: ForensicsResult) -> str:
        """Generate human-readable notes."""
        notes = []

        if result.verdict == "VALID":
            notes.append("Development appears to have occurred during hackathon window.")

        if result.commits_before_window > 0:
            notes.append(f"{result.commits_before_window} commits before hackathon start.")

        if result.timeline_flags.get('bulk_initial_commit'):
            notes.append("Large initial commit detected - could be legitimate code dump.")

        if result.development_pattern == "organic":
            notes.append("Commit pattern appears organic with incremental development.")

        if result.timeline_flags.get('suspicious_patterns'):
            notes.extend(result.timeline_flags['suspicious_patterns'])

        return " ".join(notes) if notes else "No significant timeline issues detected."
