"""Configuration for the hackathon judge system."""

from dataclasses import dataclass
from datetime import date


@dataclass
class ScoringWeights:
    """Scoring weights for evaluation criteria."""
    demo_functionality: float = 0.35
    x402_integration: float = 0.25
    code_quality: float = 0.15
    completeness: float = 0.15
    innovation: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "demo_functionality": self.demo_functionality,
            "x402_integration": self.x402_integration,
            "code_quality": self.code_quality,
            "completeness": self.completeness,
            "innovation": self.innovation,
        }


@dataclass
class TimeWindow:
    """Valid time window for hackathon submissions."""
    start: date = date(2025, 12, 8)
    end: date = date(2026, 1, 5)

    def as_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


# Default configuration
WEIGHTS = ScoringWeights()
TIME_WINDOW = TimeWindow()

# GitHub API settings
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RATE_LIMIT_PAUSE = 60  # seconds

# Analysis settings
MAX_TOKENS_PER_REPO = 50000
CLONE_TIMEOUT = 120  # seconds
