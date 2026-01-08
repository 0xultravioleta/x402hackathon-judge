"""Data models for hackathon judge system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """A hackathon project submission."""
    id: str
    name: str
    github_url: str
    description: str = ""
    demo_url: Optional[str] = None
    other_links: Optional[str] = None
    technologies: Optional[str] = None
    submission_date: Optional[str] = None

    def __post_init__(self):
        # Clean up github URL
        if self.github_url:
            self.github_url = self.github_url.strip()
            # Handle URLs that have extra content after the repo
            if '\n' in self.github_url:
                self.github_url = self.github_url.split('\n')[0].strip()


@dataclass
class RepoMetadata:
    """Metadata fetched from GitHub API."""
    owner: str
    repo_name: str
    default_branch: str = "main"
    stars: int = 0
    forks: int = 0
    created_at: Optional[str] = None
    pushed_at: Optional[str] = None
    language: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    has_readme: bool = False
    has_license: bool = False
    is_accessible: bool = True
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result from repo analysis."""
    project_id: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    architecture: str = "unknown"
    has_readme: bool = False
    readme_quality: int = 0  # 1-10
    has_tests: bool = False
    test_coverage_estimate: str = "none"  # none|low|medium|high
    has_demo: bool = False
    demo_url: Optional[str] = None
    has_deployment_config: bool = False
    deployment_target: Optional[str] = None
    code_quality_signals: dict = field(default_factory=dict)
    notable_findings: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ForensicsResult:
    """Result from git forensics analysis."""
    project_id: str
    total_commits: int = 0
    commits_in_window: int = 0
    commits_before_window: int = 0
    pre_window_commits: list[dict] = field(default_factory=list)
    timeline_flags: dict = field(default_factory=dict)
    development_pattern: str = "unknown"  # organic|suspicious|likely_pre-existing
    lines_added_in_window: int = 0
    lines_before_window: int = 0
    verdict: str = "UNKNOWN"  # VALID|QUESTIONABLE|INVALID|UNKNOWN
    confidence: float = 0.5
    notes: str = ""
    error: Optional[str] = None


@dataclass
class X402Result:
    """Result from X402 protocol analysis."""
    project_id: str
    uses_x402: bool = False
    integration_score: int = 0  # 0-10
    has_402_handling: bool = False
    has_wallet_integration: bool = False
    payment_verification: str = "missing"  # onchain|offchain|hybrid|missing
    use_case: str = ""
    payment_necessity: str = "unknown"  # essential|useful|forced|unknown
    economic_viability: str = "unknown"  # viable|questionable|not_viable|unknown
    novelty_score: int = 0  # 1-10
    creative_elements: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ProjectScores:
    """Scores for a project."""
    demo_functionality: float = 0.0
    x402_integration: float = 0.0
    code_quality: float = 0.0
    completeness: float = 0.0
    innovation: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "demo_functionality": self.demo_functionality,
            "x402_integration": self.x402_integration,
            "code_quality": self.code_quality,
            "completeness": self.completeness,
            "innovation": self.innovation,
        }


@dataclass
class ScoredProject:
    """A fully scored project."""
    project: Project
    scores: ProjectScores
    weighted_total: float = 0.0
    normalized_score: float = 0.0
    rank: int = 0
    tied_with: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    analysis: Optional[AnalysisResult] = None
    forensics: Optional[ForensicsResult] = None
    x402: Optional[X402Result] = None
    metadata: Optional[RepoMetadata] = None


@dataclass
class EvaluationRun:
    """A complete evaluation run."""
    run_id: str
    timestamp: str
    total_projects: int = 0
    evaluated: int = 0
    skipped: int = 0
    average_score: float = 0.0
    rankings: list[ScoredProject] = field(default_factory=list)
    skipped_projects: list[dict] = field(default_factory=list)
