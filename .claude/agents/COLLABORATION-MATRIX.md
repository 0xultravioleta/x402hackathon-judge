# Agent Collaboration Matrix

## Team Overview

This document defines all agents in the Hackathon Judge system, their responsibilities, and how they collaborate.

---

## Agent Registry

| ID | Agent Name | Role | Upstream (receives from) | Downstream (sends to) |
|----|------------|------|--------------------------|------------------------|
| A1 | **repo-analyzer** | Code Structure Analyst | Ingestion (raw repo) | scoring-engine |
| A2 | **git-forensics** | Timeline Validator | Ingestion (raw repo) | scoring-engine |
| A3 | **x402-expert** | Protocol Specialist | Ingestion (raw repo) | scoring-engine |
| A4 | **scoring-engine** | Evaluation Aggregator | A1, A2, A3 | report-writer |
| A5 | **report-writer** | Output Formatter | A4 (scores + findings) | Final output |

---

## Data Flow Diagram

```
                    ┌─────────────────┐
                    │   submissions   │
                    │     .csv        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    INGESTION    │
                    │  (orchestrator) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ repo-analyzer │   │ git-forensics │   │  x402-expert  │
│     (A1)      │   │     (A2)      │   │     (A3)      │
│               │   │               │   │               │
│ - Structure   │   │ - Commits     │   │ - Protocol    │
│ - Tech stack  │   │ - Timeline    │   │ - Integration │
│ - Quality     │   │ - Validation  │   │ - Use case    │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        │    AnalysisResult │    ForensicsResult│    X402Result
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                   ┌────────▼────────┐
                   │ scoring-engine  │
                   │      (A4)       │
                   │                 │
                   │ - Aggregation   │
                   │ - Weighting     │
                   │ - Ranking       │
                   └────────┬────────┘
                            │
                     ScoredProjects
                            │
                   ┌────────▼────────┐
                   │  report-writer  │
                   │      (A5)       │
                   │                 │
                   │ - MD reports    │
                   │ - JSON export   │
                   │ - Feedback      │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        rankings.md   rankings.json   project/*.md
```

---

## Inter-Agent Communication Protocol

### Message Format
```json
{
  "from_agent": "repo-analyzer",
  "to_agent": "scoring-engine",
  "project_id": "abc123",
  "timestamp": "2025-01-07T12:00:00Z",
  "payload_type": "AnalysisResult",
  "payload": { ... }
}
```

### Payload Types

| Type | Producer | Consumer | Contents |
|------|----------|----------|----------|
| `RawProject` | Ingestion | A1, A2, A3 | URL, metadata from CSV |
| `AnalysisResult` | A1 | A4 | Structure, quality signals |
| `ForensicsResult` | A2 | A4 | Timeline verdict, flags |
| `X402Result` | A3 | A4 | Integration score, use case eval |
| `ScoredProject` | A4 | A5 | All scores, ranking position |
| `Report` | A5 | Output | Formatted MD/JSON |

---

## Collaboration Rules

### 1. Independence
- A1, A2, A3 work **in parallel** - no dependencies between them
- Each receives the same `RawProject` input
- Each produces independent analysis

### 2. Aggregation
- A4 (scoring-engine) **waits for all three** before scoring
- If any upstream agent fails, A4 scores with partial data and flags it

### 3. Sequential Final Step
- A5 (report-writer) runs **after** A4 completes
- Receives complete scored data for all projects

### 4. Error Handling
| Situation | Handler | Action |
|-----------|---------|--------|
| Repo inaccessible | A1 | Return `status: "error"`, skip |
| No git history | A2 | Return `verdict: "UNKNOWN"` |
| No X402 code found | A3 | Return `integration_score: 0` |
| Missing upstream data | A4 | Score available data, flag gaps |
| Malformed scores | A5 | Log error, exclude from report |

---

## Agent Capabilities Summary

### repo-analyzer (A1)
- **Reads**: Source code, README, package files, configs
- **Detects**: Languages, frameworks, tests, demos, deployment
- **Outputs**: Quality signals, technology inventory
- **Collaborates with**: scoring-engine (provides structure data)

### git-forensics (A2)
- **Reads**: Git history, commits, branches, reflog
- **Detects**: Timeline manipulation, pre-hackathon code
- **Outputs**: Validity verdict (VALID/QUESTIONABLE/INVALID)
- **Collaborates with**: scoring-engine (provides compliance data)

### x402-expert (A3)
- **Reads**: Source code for X402 patterns, payment flows
- **Detects**: Protocol usage, integration correctness, innovation
- **Outputs**: X402 score, use case evaluation
- **Collaborates with**: scoring-engine (provides domain-specific score)

### scoring-engine (A4)
- **Reads**: Results from A1, A2, A3
- **Calculates**: Weighted scores, normalized rankings
- **Outputs**: Final scores, rank positions, aggregated findings
- **Collaborates with**: report-writer (provides complete evaluation)

### report-writer (A5)
- **Reads**: Scored projects from A4
- **Generates**: Markdown reports, JSON exports, feedback
- **Outputs**: Human-readable rankings, machine-readable data
- **Collaborates with**: Final output (files)

---

## Quick Reference Card

```
WHO DOES WHAT:

A1 repo-analyzer  → "What is this project made of?"
A2 git-forensics  → "Was this built during the hackathon?"
A3 x402-expert    → "Does it use X402 correctly?"
A4 scoring-engine → "How does it rank against others?"
A5 report-writer  → "How do we present the results?"

WHEN IN DOUBT:

- Code structure questions    → Ask A1
- Timeline/compliance issues  → Ask A2
- Protocol/domain questions   → Ask A3
- Scoring/ranking questions   → Ask A4
- Output/format questions     → Ask A5
```

---

*Last updated: 2025-01-07*
