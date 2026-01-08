"""Scoring engine for hackathon evaluation."""

from typing import Optional
from hackathon_judge.config import WEIGHTS, ScoringWeights
from hackathon_judge.models import (
    Project, AnalysisResult, ForensicsResult, X402Result,
    ProjectScores, ScoredProject
)


class ScoringEngine:
    """Calculate scores and generate rankings."""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or WEIGHTS

    def score_project(self, project: Project,
                      analysis: Optional[AnalysisResult] = None,
                      forensics: Optional[ForensicsResult] = None,
                      x402: Optional[X402Result] = None) -> ScoredProject:
        """Score a single project based on all analysis results."""
        scores = ProjectScores()

        # Calculate individual scores
        scores.demo_functionality = self._score_demo(project, analysis)
        scores.x402_integration = self._score_x402(x402)
        scores.code_quality = self._score_code_quality(analysis)
        scores.completeness = self._score_completeness(project, analysis)
        scores.innovation = self._score_innovation(analysis, x402)

        # Calculate weighted total
        weighted_total = (
            scores.demo_functionality * self.weights.demo_functionality +
            scores.x402_integration * self.weights.x402_integration +
            scores.code_quality * self.weights.code_quality +
            scores.completeness * self.weights.completeness +
            scores.innovation * self.weights.innovation
        )

        # Create scored project
        scored = ScoredProject(
            project=project,
            scores=scores,
            weighted_total=round(weighted_total, 2),
            analysis=analysis,
            forensics=forensics,
            x402=x402,
        )

        # Add strengths and weaknesses
        scored.strengths = self._identify_strengths(scored)
        scored.weaknesses = self._identify_weaknesses(scored)
        scored.feedback = self._generate_feedback(scored)
        scored.flags = self._generate_flags(scored)

        return scored

    def _score_demo(self, project: Project, analysis: Optional[AnalysisResult]) -> float:
        """Score demo functionality (0-10)."""
        score = 0.0

        # Has demo URL
        if project.demo_url:
            score += 4.0  # Major boost for having demo

        if analysis:
            # Has deployment config
            if analysis.has_deployment_config:
                score += 2.0

            # README quality indicates documentation
            score += min(analysis.readme_quality / 5, 2.0)

            # Has demo detected in repo
            if analysis.has_demo:
                score += 2.0

        # Ensure score is within bounds
        return min(max(score, 0.0), 10.0)

    def _score_x402(self, x402: Optional[X402Result]) -> float:
        """Score X402 integration (0-10)."""
        if not x402:
            return 0.0

        if not x402.uses_x402:
            return 0.0

        score = float(x402.integration_score)

        # Bonus for proper implementation
        if x402.has_wallet_integration:
            score += 1.0

        if x402.payment_verification in ["onchain", "hybrid"]:
            score += 1.0

        if x402.payment_necessity == "essential":
            score += 1.0

        return min(max(score, 0.0), 10.0)

    def _score_code_quality(self, analysis: Optional[AnalysisResult]) -> float:
        """Score code quality (0-10)."""
        if not analysis:
            return 3.0  # Default middle score

        score = 3.0  # Base score

        # Linting and formatting
        if analysis.code_quality_signals.get('linting'):
            score += 1.5

        if analysis.code_quality_signals.get('formatting'):
            score += 1.0

        # Error handling
        error_handling = analysis.code_quality_signals.get('error_handling', 'poor')
        if error_handling == 'good':
            score += 2.0
        elif error_handling == 'adequate':
            score += 1.0

        # Documentation
        docs = analysis.code_quality_signals.get('documentation', 'poor')
        if docs == 'good':
            score += 1.5
        elif docs == 'adequate':
            score += 0.5

        # Test coverage
        if analysis.has_tests:
            if analysis.test_coverage_estimate == 'high':
                score += 2.0
            elif analysis.test_coverage_estimate == 'medium':
                score += 1.5
            elif analysis.test_coverage_estimate == 'low':
                score += 0.5

        return min(max(score, 0.0), 10.0)

    def _score_completeness(self, project: Project, analysis: Optional[AnalysisResult]) -> float:
        """Score project completeness (0-10)."""
        score = 3.0  # Base score

        # Has README
        if analysis and analysis.has_readme:
            score += 1.5
            if analysis.readme_quality >= 7:
                score += 1.0

        # Has demo
        if project.demo_url or (analysis and analysis.has_demo):
            score += 2.0

        # Has deployment config
        if analysis and analysis.has_deployment_config:
            score += 1.5

        # Multiple languages/frameworks (indicates full-stack)
        if analysis:
            if len(analysis.languages) >= 2:
                score += 1.0
            if len(analysis.frameworks) >= 2:
                score += 1.0

        return min(max(score, 0.0), 10.0)

    def _score_innovation(self, analysis: Optional[AnalysisResult],
                          x402: Optional[X402Result]) -> float:
        """Score innovation (0-10)."""
        score = 4.0  # Base score (solid execution of known concept)

        if x402:
            # Novelty from X402 analysis
            score = max(score, float(x402.novelty_score))

            # Bonus for creative elements
            if x402.creative_elements:
                score += min(len(x402.creative_elements), 3)

            # Special use cases
            if x402.use_case in ['streaming', 'm2m payments', 'cross-chain']:
                score += 1.5

        if analysis:
            # Notable findings can indicate innovation
            innovative_keywords = ['novel', 'unique', 'first', 'innovative', 'creative']
            for finding in analysis.notable_findings:
                if any(kw in finding.lower() for kw in innovative_keywords):
                    score += 0.5

        return min(max(score, 0.0), 10.0)

    def _identify_strengths(self, scored: ScoredProject) -> list[str]:
        """Identify project strengths."""
        strengths = []
        scores = scored.scores

        if scores.demo_functionality >= 7:
            strengths.append("Working demo with good functionality")

        if scores.x402_integration >= 7:
            strengths.append("Strong X402 protocol integration")

        if scores.code_quality >= 7:
            strengths.append("High code quality with good practices")

        if scores.completeness >= 7:
            strengths.append("Feature-complete implementation")

        if scores.innovation >= 7:
            strengths.append("Innovative approach or use case")

        # Analysis-based strengths
        if scored.analysis:
            if scored.analysis.has_tests and scored.analysis.test_coverage_estimate in ['medium', 'high']:
                strengths.append("Good test coverage")

            if scored.analysis.has_deployment_config:
                strengths.append(f"Ready for deployment ({scored.analysis.deployment_target})")

        # X402-based strengths
        if scored.x402 and scored.x402.creative_elements:
            for elem in scored.x402.creative_elements[:2]:
                strengths.append(elem)

        return strengths[:5]  # Limit to top 5

    def _identify_weaknesses(self, scored: ScoredProject) -> list[str]:
        """Identify project weaknesses."""
        weaknesses = []
        scores = scored.scores

        if scores.demo_functionality < 5:
            weaknesses.append("Demo functionality needs improvement")

        if scores.x402_integration < 5:
            weaknesses.append("X402 integration is incomplete or missing")

        if scores.code_quality < 5:
            weaknesses.append("Code quality could be improved")

        if scores.completeness < 5:
            weaknesses.append("Implementation appears incomplete")

        if scores.innovation < 5:
            weaknesses.append("Limited innovation beyond basic implementation")

        # Analysis-based weaknesses
        if scored.analysis:
            if not scored.analysis.has_readme:
                weaknesses.append("Missing README documentation")
            elif scored.analysis.readme_quality < 4:
                weaknesses.append("README needs more detail")

            if not scored.analysis.has_tests:
                weaknesses.append("No tests found")

        # X402-based weaknesses
        if scored.x402 and scored.x402.concerns:
            weaknesses.extend(scored.x402.concerns[:2])

        return weaknesses[:5]  # Limit to top 5

    def _generate_feedback(self, scored: ScoredProject) -> list[str]:
        """Generate actionable feedback."""
        feedback = []

        # Demo feedback
        if not scored.project.demo_url:
            feedback.append("Consider adding a live demo URL for judges to test")

        # Code quality feedback
        if scored.analysis:
            if not scored.analysis.code_quality_signals.get('linting'):
                feedback.append("Add linting configuration for consistent code style")

            if not scored.analysis.has_tests:
                feedback.append("Add tests to improve reliability and maintainability")

            if scored.analysis.readme_quality < 6:
                feedback.append("Expand README with setup instructions and screenshots")

        # X402 feedback
        if scored.x402:
            if not scored.x402.uses_x402:
                feedback.append("Implement X402 protocol for payment functionality")
            elif scored.x402.payment_verification == "missing":
                feedback.append("Add payment verification to ensure transactions are valid")

        return feedback[:4]  # Limit to top 4

    def _generate_flags(self, scored: ScoredProject) -> dict:
        """Generate flags for special conditions."""
        flags = {
            'timeline_issues': False,
            'potential_plagiarism': False,
            'exceptional_quality': False,
            'missing_x402': False,
        }

        # Check forensics
        if scored.forensics:
            if scored.forensics.verdict in ['QUESTIONABLE', 'INVALID']:
                flags['timeline_issues'] = True

        # Check X402
        if scored.x402 and not scored.x402.uses_x402:
            flags['missing_x402'] = True

        # Check for exceptional quality
        if scored.weighted_total >= 8.5:
            flags['exceptional_quality'] = True

        return flags

    def rank_projects(self, scored_projects: list[ScoredProject]) -> list[ScoredProject]:
        """Rank all projects and identify ties."""
        # Sort by weighted total descending
        sorted_projects = sorted(
            scored_projects,
            key=lambda p: p.weighted_total,
            reverse=True
        )

        # Assign ranks and detect ties
        current_rank = 1
        for i, project in enumerate(sorted_projects):
            project.rank = current_rank

            # Check for ties (within 0.5 points)
            project.tied_with = []
            for other in sorted_projects:
                if other.project.id != project.project.id:
                    if abs(other.weighted_total - project.weighted_total) <= 0.5:
                        project.tied_with.append(other.project.name)

            # Calculate normalized score (0-100)
            if sorted_projects:
                max_score = sorted_projects[0].weighted_total
                min_score = sorted_projects[-1].weighted_total
                if max_score > min_score:
                    project.normalized_score = round(
                        ((project.weighted_total - min_score) / (max_score - min_score)) * 100,
                        1
                    )
                else:
                    project.normalized_score = 100.0

            # Increment rank only if next project has different score
            if i + 1 < len(sorted_projects):
                if abs(sorted_projects[i + 1].weighted_total - project.weighted_total) > 0.05:
                    current_rank = i + 2

        return sorted_projects
