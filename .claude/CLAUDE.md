# Hackathon Judge System

## Project Overview

Automated hackathon evaluation system that analyzes GitHub repositories, scores them against configurable criteria, and generates comprehensive reports.

## Expert Agents

This project uses specialized agents located in `.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `repo-analyzer` | Analyze repo structure, tech stack, quality signals | First pass on any repo |
| `git-forensics` | Validate timeline, detect history manipulation | Verify hackathon compliance |
| `x402-expert` | Evaluate X402 protocol integration | Domain-specific scoring |
| `scoring-engine` | Calculate scores, apply weights, generate rankings | After all analysis complete |
| `report-writer` | Format reports in MD/JSON, write feedback | Final output generation |

## Evaluation Pipeline

```
1. INGESTION
   └── Parse submissions.csv
   └── Extract GitHub URLs + metadata

2. PER-PROJECT ANALYSIS (parallel)
   ├── repo-analyzer → structure, tech, quality
   ├── git-forensics → timeline validation
   └── x402-expert → protocol evaluation

3. SCORING
   └── scoring-engine → weighted scores, ranking

4. REPORTING
   └── report-writer → MD + JSON outputs
```

## Configuration

### Scoring Weights (from interview)
```json
{
  "demo_functionality": 0.35,
  "x402_integration": 0.25,
  "code_quality": 0.15,
  "completeness": 0.15,
  "innovation": 0.10
}
```

### Valid Time Window
- Start: December 8, 2025
- End: January 5, 2026

### Decisions Made
- Conflicts of interest: Ignore (evaluate all equally)
- Git history verification: Trust (assume good faith)
- AI code detection: Not evaluated (AI usage acceptable)
- Demo vs Code weight: 70/30 (demo matters more)
- Tiebreaker: Don't force (human decides ties)
- Error handling: Skip + log problematic repos
- Repo access: Hybrid (API overview, clone if promising)
- Analysis depth: ~50k tokens per repo

## Commands

### Evaluate All Projects
```bash
python -m hackathon_judge evaluate --input submissions.csv --output results/
```

### Evaluate Single Project
```bash
python -m hackathon_judge evaluate-single --url https://github.com/user/repo
```

### Generate Report Only
```bash
python -m hackathon_judge report --input results/scores.json --format md
```

## Output Files

```
results/
├── rankings.md           # Human-readable ranking matrix
├── rankings.json         # Machine-readable full data
├── projects/
│   ├── project-1.md      # Individual project reports
│   ├── project-2.md
│   └── ...
├── executive-summary.md  # High-level summary
└── logs/
    ├── skipped.json      # Projects that couldn't be evaluated
    └── evaluation.log    # Full execution log
```

## Development Notes

### Stack
- Python 3.11+
- GitPython (repo cloning)
- requests (GitHub API)
- pandas (data processing)
- rich (CLI progress display)

### Future Improvements (TODO after X402 hackathon)
- Make scoring criteria fully configurable via YAML
- Add plugin system for different hackathon types
- Web UI for monitoring evaluations
- Support for GitLab, Bitbucket
- Parallel evaluation with Celery

## Quick Reference

### Run Evaluation
```bash
# Full run
python -m hackathon_judge evaluate -i submissions.csv -o results/

# Dry run (no cloning, API only)
python -m hackathon_judge evaluate -i submissions.csv --dry-run

# Resume interrupted run
python -m hackathon_judge evaluate -i submissions.csv --resume
```

### Check Single Repo
```bash
# Quick analysis
python -m hackathon_judge analyze https://github.com/user/repo

# With git forensics
python -m hackathon_judge analyze https://github.com/user/repo --forensics
```
