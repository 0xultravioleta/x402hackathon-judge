"""JSON export for evaluation results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from hackathon_judge.config import WEIGHTS, TIME_WINDOW
from hackathon_judge.models import ScoredProject, EvaluationRun


class JSONExporter:
    """Export evaluation results to JSON."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, run: EvaluationRun) -> Path:
        """Export full evaluation results to JSON."""
        data = {
            "hackathon": {
                "name": "X402 Hackathon",
                "evaluation_date": run.timestamp,
                "judge": "automated",
                "criteria_version": "1.0"
            },
            "summary": {
                "total_projects": run.total_projects,
                "evaluated": run.evaluated,
                "skipped": run.skipped,
                "average_score": round(run.average_score, 2)
            },
            "rankings": [self._serialize_scored_project(p) for p in run.rankings],
            "skipped_projects": run.skipped_projects,
            "metadata": {
                "weights_used": WEIGHTS.as_dict(),
                "valid_window": TIME_WINDOW.as_dict()
            }
        }

        path = self.output_dir / 'rankings.json'
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return path

    def _serialize_scored_project(self, scored: ScoredProject) -> dict[str, Any]:
        """Serialize a scored project to dictionary."""
        project = scored.project

        data = {
            "rank": scored.rank,
            "project_id": project.id,
            "project_name": project.name,
            "github_url": project.github_url,
            "demo_url": project.demo_url,
            "description": project.description[:500] if project.description else "",
            "scores": {
                "demo_functionality": round(scored.scores.demo_functionality, 2),
                "x402_integration": round(scored.scores.x402_integration, 2),
                "code_quality": round(scored.scores.code_quality, 2),
                "completeness": round(scored.scores.completeness, 2),
                "innovation": round(scored.scores.innovation, 2)
            },
            "weighted_total": round(scored.weighted_total, 2),
            "normalized_score": round(scored.normalized_score, 1),
            "tied_with": scored.tied_with,
            "strengths": scored.strengths,
            "weaknesses": scored.weaknesses,
            "feedback": scored.feedback,
            "flags": scored.flags,
        }

        # Add analysis details if available
        if scored.analysis:
            data["analysis"] = {
                "languages": scored.analysis.languages,
                "frameworks": scored.analysis.frameworks,
                "architecture": scored.analysis.architecture,
                "has_readme": scored.analysis.has_readme,
                "readme_quality": scored.analysis.readme_quality,
                "has_tests": scored.analysis.has_tests,
                "test_coverage": scored.analysis.test_coverage_estimate,
                "has_demo": scored.analysis.has_demo,
                "has_deployment": scored.analysis.has_deployment_config,
                "deployment_target": scored.analysis.deployment_target,
            }

        # Add forensics details if available
        if scored.forensics:
            data["forensics"] = {
                "verdict": scored.forensics.verdict,
                "confidence": scored.forensics.confidence,
                "total_commits": scored.forensics.total_commits,
                "commits_in_window": scored.forensics.commits_in_window,
                "commits_before_window": scored.forensics.commits_before_window,
                "development_pattern": scored.forensics.development_pattern,
                "notes": scored.forensics.notes,
            }

        # Add X402 details if available
        if scored.x402:
            data["x402"] = {
                "uses_x402": scored.x402.uses_x402,
                "integration_score": scored.x402.integration_score,
                "has_wallet_integration": scored.x402.has_wallet_integration,
                "payment_verification": scored.x402.payment_verification,
                "use_case": scored.x402.use_case,
                "novelty_score": scored.x402.novelty_score,
                "creative_elements": scored.x402.creative_elements,
            }

        return data
