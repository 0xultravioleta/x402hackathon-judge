# X402 Hackathon Judge

Automated evaluation system for the X402 hackathon submissions.

## What it does

- Analyzes GitHub repositories for code quality, structure, and X402 integration
- Validates timeline compliance (commits within hackathon window)
- Generates weighted scores and rankings
- Produces detailed reports for human judges

## Scoring Weights

| Category | Weight |
|----------|--------|
| Demo & Functionality | 35% |
| X402 Integration | 25% |
| Code Quality | 15% |
| Completeness | 15% |
| Innovation | 10% |

## Usage

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Run full evaluation
python -m hackathon_judge evaluate -i submissions.csv -o results/

# Analyze single repo
python -m hackathon_judge analyze https://github.com/user/repo
```

## Output

Results are generated in `results/`:
- `rankings.md` - Full ranking table
- `rankings.json` - Machine-readable data
- `executive-summary.md` - Overview for judges
- `timeline_audit.md` - Timeline violation report
- `projects/*.md` - Individual project evaluations

## Hackathon Window

December 8, 2025 - January 5, 2026
