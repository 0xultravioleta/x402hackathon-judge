"""Main CLI for hackathon judge system."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from hackathon_judge.config import WEIGHTS, TIME_WINDOW
from hackathon_judge.models import Project, EvaluationRun, ScoredProject
from hackathon_judge.ingestion import parse_submissions
from hackathon_judge.fetcher import GitHubAPI, RepoCloner
from hackathon_judge.analyzer import RepoAnalyzer, GitForensics, X402Detector
from hackathon_judge.scoring import ScoringEngine
from hackathon_judge.reporter import MarkdownReporter, JSONExporter


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Hackathon Judge - Automated evaluation system for hackathon submissions."""
    pass


@cli.command()
@click.option('-i', '--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Path to submissions CSV file')
@click.option('-o', '--output', 'output_dir', required=True, type=click.Path(),
              help='Output directory for results')
@click.option('--dry-run', is_flag=True, help='API-only analysis without cloning')
@click.option('--resume', is_flag=True, help='Resume from previous run')
@click.option('--limit', type=int, default=0, help='Limit number of projects to evaluate')
def evaluate(input_file: str, output_dir: str, dry_run: bool, resume: bool, limit: int):
    """Evaluate all projects from submissions file."""
    console.print("[bold blue]Hackathon Judge System[/bold blue]")
    console.print(f"Input: {input_file}")
    console.print(f"Output: {output_dir}")
    console.print()

    # Parse submissions
    console.print("[yellow]Parsing submissions...[/yellow]")
    try:
        projects = parse_submissions(input_file)
        console.print(f"[green]Found {len(projects)} valid projects[/green]")
    except Exception as e:
        console.print(f"[red]Error parsing submissions: {e}[/red]")
        sys.exit(1)

    if limit > 0:
        projects = projects[:limit]
        console.print(f"[yellow]Limited to {limit} projects[/yellow]")

    # Initialize components
    github_api = GitHubAPI()
    cloner = RepoCloner() if not dry_run else None
    repo_analyzer = RepoAnalyzer(github_api)
    git_forensics = GitForensics(github_api)
    x402_detector = X402Detector(github_api)
    scoring_engine = ScoringEngine()

    # Prepare output
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logs_path = output_path / 'logs'
    logs_path.mkdir(exist_ok=True)

    # Initialize run
    run = EvaluationRun(
        run_id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().isoformat(),
        total_projects=len(projects),
    )

    scored_projects: list[ScoredProject] = []
    skipped: list[dict] = []

    # Evaluate each project
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Evaluating projects...", total=len(projects))

        for project in projects:
            progress.update(task, description=f"[cyan]{project.name[:30]}...[/cyan]")

            try:
                scored = evaluate_single_project(
                    project, github_api, cloner, repo_analyzer,
                    git_forensics, x402_detector, scoring_engine, dry_run
                )
                scored_projects.append(scored)
            except Exception as e:
                console.print(f"[red]Error evaluating {project.name}: {e}[/red]")
                skipped.append({
                    "name": project.name,
                    "url": project.github_url,
                    "reason": str(e)
                })

            progress.advance(task)

    # Rank projects
    console.print()
    console.print("[yellow]Ranking projects...[/yellow]")
    ranked_projects = scoring_engine.rank_projects(scored_projects)

    # Update run stats
    run.rankings = ranked_projects
    run.evaluated = len(ranked_projects)
    run.skipped = len(skipped)
    run.skipped_projects = skipped
    if ranked_projects:
        run.average_score = sum(p.weighted_total for p in ranked_projects) / len(ranked_projects)

    # Generate reports
    console.print("[yellow]Generating reports...[/yellow]")
    md_reporter = MarkdownReporter(output_path)
    json_exporter = JSONExporter(output_path)

    md_reporter.generate_all(run)
    json_exporter.export(run)

    # Write skipped log
    if skipped:
        import json
        with open(logs_path / 'skipped.json', 'w') as f:
            json.dump(skipped, f, indent=2)

    # Display results
    console.print()
    console.print("[bold green]Evaluation Complete![/bold green]")
    console.print()

    # Show top 5
    table = Table(title="Top 5 Projects")
    table.add_column("Rank", style="cyan")
    table.add_column("Project", style="white")
    table.add_column("Demo", style="green")
    table.add_column("X402", style="yellow")
    table.add_column("Total", style="bold")

    for scored in ranked_projects[:5]:
        table.add_row(
            str(scored.rank),
            scored.project.name[:30],
            f"{scored.scores.demo_functionality:.1f}",
            f"{scored.scores.x402_integration:.1f}",
            f"{scored.weighted_total:.2f}"
        )

    console.print(table)
    console.print()
    console.print(f"[green]Evaluated: {run.evaluated}[/green]")
    console.print(f"[yellow]Skipped: {run.skipped}[/yellow]")
    console.print(f"[blue]Average Score: {run.average_score:.2f}[/blue]")
    console.print()
    console.print(f"[bold]Results saved to: {output_path}[/bold]")


def evaluate_single_project(
    project: Project,
    github_api: GitHubAPI,
    cloner: Optional[RepoCloner],
    repo_analyzer: RepoAnalyzer,
    git_forensics: GitForensics,
    x402_detector: X402Detector,
    scoring_engine: ScoringEngine,
    api_only: bool = False,
) -> ScoredProject:
    """Evaluate a single project."""
    local_path = None

    # Get metadata
    metadata = github_api.get_repo_metadata(project.github_url)

    if not metadata.is_accessible:
        raise ValueError(f"Repository not accessible: {metadata.error}")

    # Clone if needed
    if cloner and not api_only:
        local_path, error = cloner.clone(project.github_url)
        if error:
            # Continue with API-only analysis
            local_path = None

    # Run analyzers
    analysis = repo_analyzer.analyze(project.id, project.github_url, metadata, local_path)
    forensics = git_forensics.analyze(project.id, project.github_url, local_path)
    x402 = x402_detector.analyze(project.id, project, local_path)

    # Score project
    scored = scoring_engine.score_project(project, analysis, forensics, x402)
    scored.metadata = metadata

    return scored


@cli.command()
@click.argument('url')
@click.option('--forensics/--no-forensics', default=False, help='Run git forensics analysis')
def analyze(url: str, forensics: bool):
    """Analyze a single GitHub repository."""
    console.print(f"[bold blue]Analyzing: {url}[/bold blue]")

    # Initialize components
    github_api = GitHubAPI()
    cloner = RepoCloner()
    repo_analyzer = RepoAnalyzer(github_api)
    git_forensics_analyzer = GitForensics(github_api)
    x402_detector = X402Detector(github_api)

    # Get metadata
    console.print("[yellow]Fetching metadata...[/yellow]")
    metadata = github_api.get_repo_metadata(url)

    if not metadata.is_accessible:
        console.print(f"[red]Error: {metadata.error}[/red]")
        return

    console.print(f"[green]Repository: {metadata.owner}/{metadata.repo_name}[/green]")
    console.print(f"Stars: {metadata.stars}, Forks: {metadata.forks}")
    console.print(f"Language: {metadata.language}")
    console.print()

    # Clone
    console.print("[yellow]Cloning repository...[/yellow]")
    local_path, error = cloner.clone(url)
    if error:
        console.print(f"[yellow]Clone failed, using API-only: {error}[/yellow]")
        local_path = None
    else:
        console.print(f"[green]Cloned to: {local_path}[/green]")

    # Create temporary project
    project = Project(
        id="temp",
        name=metadata.repo_name,
        github_url=url,
        description=""
    )

    # Analyze
    console.print()
    console.print("[yellow]Running analysis...[/yellow]")

    analysis = repo_analyzer.analyze(project.id, url, metadata, local_path)
    console.print(f"Languages: {', '.join(analysis.languages)}")
    console.print(f"Frameworks: {', '.join(analysis.frameworks)}")
    console.print(f"Architecture: {analysis.architecture}")
    console.print(f"README Quality: {analysis.readme_quality}/10")
    console.print(f"Has Tests: {analysis.has_tests}")
    console.print(f"Has Demo: {analysis.has_demo}")

    if forensics:
        console.print()
        console.print("[yellow]Running git forensics...[/yellow]")
        forensics_result = git_forensics_analyzer.analyze(project.id, url, local_path)
        console.print(f"Total Commits: {forensics_result.total_commits}")
        console.print(f"In Window: {forensics_result.commits_in_window}")
        console.print(f"Before Window: {forensics_result.commits_before_window}")
        console.print(f"Verdict: {forensics_result.verdict}")
        console.print(f"Pattern: {forensics_result.development_pattern}")

    console.print()
    console.print("[yellow]Checking X402 integration...[/yellow]")
    x402 = x402_detector.analyze(project.id, project, local_path)
    console.print(f"Uses X402: {x402.uses_x402}")
    console.print(f"Integration Score: {x402.integration_score}/10")
    console.print(f"Use Case: {x402.use_case}")
    if x402.creative_elements:
        console.print(f"Creative Elements: {', '.join(x402.creative_elements)}")

    console.print()
    console.print("[green]Analysis complete![/green]")


@cli.command()
@click.option('-i', '--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Path to scores JSON file')
@click.option('-f', '--format', 'output_format', type=click.Choice(['md', 'json', 'both']),
              default='both', help='Output format')
@click.option('-o', '--output', 'output_dir', type=click.Path(), help='Output directory')
def report(input_file: str, output_format: str, output_dir: Optional[str]):
    """Generate reports from existing scores."""
    import json

    console.print(f"[bold blue]Generating reports from: {input_file}[/bold blue]")

    with open(input_file) as f:
        data = json.load(f)

    # Reconstruct run from JSON
    # This is a simplified version - full implementation would deserialize properly
    console.print("[yellow]Report generation from JSON not fully implemented yet[/yellow]")
    console.print("[yellow]Use the evaluate command to generate full reports[/yellow]")


@cli.command()
def info():
    """Show current configuration."""
    console.print("[bold blue]Hackathon Judge Configuration[/bold blue]")
    console.print()

    table = Table(title="Scoring Weights")
    table.add_column("Category", style="cyan")
    table.add_column("Weight", style="green")

    weights = WEIGHTS.as_dict()
    for cat, weight in weights.items():
        table.add_row(cat.replace('_', ' ').title(), f"{weight*100:.0f}%")

    console.print(table)
    console.print()

    console.print(f"[bold]Valid Time Window:[/bold]")
    console.print(f"  Start: {TIME_WINDOW.start}")
    console.print(f"  End: {TIME_WINDOW.end}")


if __name__ == "__main__":
    cli()
