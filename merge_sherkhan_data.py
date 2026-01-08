#!/usr/bin/env python3
"""Merge Sherkhan's commit analysis with evaluation results."""

import json
import csv
import re
from pathlib import Path

def normalize_url(url: str) -> str:
    """Normalize GitHub URL for matching."""
    if not url:
        return ""
    url = url.lower().strip()
    url = re.sub(r'https?://github\.com/', '', url)
    url = url.rstrip('/')
    url = re.sub(r'\.git$', '', url)
    return url

def load_sherkhan_data(csv_path: str) -> dict:
    """Load Sherkhan's commit analysis into a dict keyed by normalized URL."""
    data = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            repo_url = row.get('repository', '')
            if not repo_url or row.get('error_reason'):
                continue

            normalized = normalize_url(repo_url)
            data[normalized] = {
                'first_commit': row.get('first_commit_date', ''),
                'last_commit': row.get('last_commit_date', ''),
                'active_days': int(row.get('active_days', 0) or 0),
                'duration_days': int(row.get('duration_days', 0) or 0),
                'total_commits': int(row.get('total_commits', 0) or 0),
                'commits_before_hackathon': int(row.get('commits_before_hackathon', 0) or 0),
                'user_age_years': float(row.get('userAgeYears', 0) or 0),
                'networks': row.get('networks', ''),
                'mentions_x402': row.get('mentions_x402', '').upper() == 'TRUE',
            }
    return data

def load_rankings(json_path: str) -> dict:
    """Load rankings JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_and_analyze(sherkhan_data: dict, rankings: dict) -> dict:
    """Merge Sherkhan's data with rankings and flag issues."""

    results = {
        'timeline_violations': [],
        'x402_mismatches': [],
        'network_data': [],
        'matched_projects': 0,
        'unmatched_projects': [],
    }

    # Build lookup from rankings (key is 'rankings' not 'projects')
    for project in rankings.get('rankings', []):
        github_url = project.get('github_url', '')
        normalized = normalize_url(github_url)

        if normalized in sherkhan_data:
            results['matched_projects'] += 1
            sk_data = sherkhan_data[normalized]

            # Check timeline violations
            commits_before = sk_data['commits_before_hackathon']
            if commits_before > 0:
                total = sk_data['total_commits']
                pct = (commits_before / total * 100) if total > 0 else 0
                results['timeline_violations'].append({
                    'project': project.get('project_name', normalized),
                    'github_url': github_url,
                    'commits_before': commits_before,
                    'total_commits': total,
                    'percent_before': round(pct, 1),
                    'current_score': project.get('weighted_total', 0),
                    'current_rank': project.get('rank', 0),
                })

            # Add network data
            if sk_data['networks']:
                results['network_data'].append({
                    'project': project.get('project_name', normalized),
                    'networks': sk_data['networks'],
                })
        else:
            results['unmatched_projects'].append({
                'name': project.get('project_name', ''),
                'github_url': github_url,
            })

    # Sort violations by severity
    results['timeline_violations'].sort(
        key=lambda x: x['commits_before'],
        reverse=True
    )

    return results

def main():
    csv_path = '/mnt/z/ultravioleta/dao/hackathon-judge/commit_analysis.csv'
    json_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/rankings.json'

    print("Loading Sherkhan's commit analysis...")
    sherkhan_data = load_sherkhan_data(csv_path)
    print(f"  Loaded {len(sherkhan_data)} valid entries")

    print("\nLoading rankings...")
    rankings = load_rankings(json_path)
    print(f"  Loaded {len(rankings.get('projects', []))} projects")

    print("\nMerging and analyzing...")
    results = merge_and_analyze(sherkhan_data, rankings)

    print(f"\n{'='*60}")
    print("MERGE RESULTS")
    print('='*60)
    print(f"Matched projects: {results['matched_projects']}")
    print(f"Unmatched in rankings: {len(results['unmatched_projects'])}")

    print(f"\n{'='*60}")
    print("TIMELINE VIOLATIONS (commits before Dec 8, 2025)")
    print('='*60)

    for v in results['timeline_violations']:
        print(f"\n{v['project']}")
        print(f"  URL: {v['github_url']}")
        print(f"  Commits before hackathon: {v['commits_before']}/{v['total_commits']} ({v['percent_before']}%)")
        print(f"  Current score: {v['current_score']:.2f} (rank #{v['current_rank']})")

        # Recommendation
        if v['percent_before'] >= 90:
            print(f"  ⚠️  CRITICAL: Mostly pre-existing code")
        elif v['percent_before'] >= 50:
            print(f"  ⚠️  WARNING: Significant pre-existing code")
        else:
            print(f"  ℹ️  Minor: Some pre-existing foundation")

    # Save results
    output_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/timeline_audit.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to: {output_path}")

    # Create summary for judges
    summary_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/timeline_audit.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# Timeline Audit Report\n\n")
        f.write("## Overview\n\n")
        f.write(f"- **Projects matched with Sherkhan's data**: {results['matched_projects']}\n")
        f.write(f"- **Timeline violations found**: {len(results['timeline_violations'])}\n\n")

        f.write("## Timeline Violations\n\n")
        f.write("Projects with commits before hackathon start (Dec 8, 2024):\n\n")
        f.write("| Project | Pre-Hackathon Commits | Total | % Pre-existing | Current Score | Rank | Severity |\n")
        f.write("|---------|----------------------|-------|----------------|---------------|------|----------|\n")

        for v in results['timeline_violations']:
            if v['percent_before'] >= 90:
                severity = "🔴 CRITICAL"
            elif v['percent_before'] >= 50:
                severity = "🟠 WARNING"
            else:
                severity = "🟡 Minor"

            f.write(f"| {v['project']} | {v['commits_before']} | {v['total_commits']} | {v['percent_before']}% | {v['current_score']:.2f} | #{v['current_rank']} | {severity} |\n")

        f.write("\n## Recommendations\n\n")
        f.write("1. **Critical violations (90%+ pre-existing)**: Consider disqualification\n")
        f.write("2. **Warnings (50-90% pre-existing)**: Review manually, may need score adjustment\n")
        f.write("3. **Minor (under 50%)**: Likely building on starter code, acceptable\n")

    print(f"Summary saved to: {summary_path}")

if __name__ == '__main__':
    main()
