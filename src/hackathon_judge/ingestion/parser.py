"""Parser for hackathon submissions CSV."""

import csv
import hashlib
import re
from pathlib import Path
from typing import Iterator

from hackathon_judge.models import Project


def extract_github_url(url_text: str) -> str | None:
    """Extract a valid GitHub URL from text that may contain multiple links."""
    if not url_text:
        return None

    # Common patterns
    patterns = [
        r'https?://github\.com/[\w\-]+/[\w\-\.]+',
        r'github\.com/[\w\-]+/[\w\-\.]+',
    ]

    for pattern in patterns:
        match = re.search(pattern, url_text)
        if match:
            url = match.group(0)
            if not url.startswith('http'):
                url = 'https://' + url
            # Remove trailing slashes or path components
            url = re.sub(r'/tree/.*$', '', url)
            url = re.sub(r'/blob/.*$', '', url)
            url = url.rstrip('/')
            return url

    return None


def generate_project_id(name: str, url: str) -> str:
    """Generate a unique project ID from name and URL."""
    content = f"{name}:{url}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def parse_submissions(file_path: str | Path) -> list[Project]:
    """Parse submissions CSV file and return list of Projects.

    Expected columns:
    - Project name
    - Project description
    - Link to Github repo
    - Other links
    - Link to 2 minute live product demo
    - Technologies used
    - Submission Date
    """
    projects = []
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Submissions file not found: {file_path}")

    # Handle BOM for UTF-8 files
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Extract project name
            name = row.get('Project name', '').strip()
            if not name:
                continue

            # Extract and validate GitHub URL
            github_raw = row.get('Link to Github repo', '')
            github_url = extract_github_url(github_raw)

            if not github_url:
                continue  # Skip projects without valid GitHub URL

            # Extract other fields
            description = row.get('Project description', '').strip()
            demo_url = row.get('Link to 2 minute live product demo', '').strip()
            other_links = row.get('Other links', '').strip()
            technologies = row.get('Technologies used', '').strip()
            submission_date = row.get('Submission Date', '').strip()

            # Generate unique ID
            project_id = generate_project_id(name, github_url)

            project = Project(
                id=project_id,
                name=name,
                github_url=github_url,
                description=description,
                demo_url=demo_url if demo_url else None,
                other_links=other_links if other_links else None,
                technologies=technologies if technologies else None,
                submission_date=submission_date if submission_date else None,
            )

            projects.append(project)

    return projects
