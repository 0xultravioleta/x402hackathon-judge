#!/usr/bin/env python3
"""Add video links from submissions.csv to rankings.md"""

import csv
import re

def normalize_name(name: str) -> str:
    """Normalize project name for matching."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_video_links(csv_path: str) -> dict:
    """Load project name -> video link mapping."""
    links = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Project name', '').strip()
            video = row.get('Link to 2 minute live product demo', '').strip()
            if name and video:
                # Handle multiple URLs separated by comma - take the first one
                if ',' in video:
                    video = video.split(',')[0].strip()
                links[normalize_name(name)] = video
    return links

def update_rankings(md_path: str, video_links: dict):
    """Update rankings.md with video column."""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_table = False
    header_done = False

    for line in lines:
        # Detect table header
        if '| Rank | Project |' in line:
            in_table = True
            # Add Video column after Project
            line = line.replace('| Project |', '| Project | Video |')
            new_lines.append(line)
            header_done = False
            continue

        # Detect separator line
        if in_table and not header_done and line.startswith('|---'):
            # Add separator for Video column
            line = line.replace('|---------|', '|---------|-------|')
            new_lines.append(line)
            header_done = True
            continue

        # Process data rows
        if in_table and line.startswith('|') and header_done:
            # Extract project name from markdown link
            match = re.search(r'\[([^\]]+)\]', line)
            if match:
                project_name = match.group(1)
                normalized = normalize_name(project_name)

                # Find video link
                video_url = video_links.get(normalized, '')

                if video_url:
                    video_cell = f'[Video]({video_url})'
                else:
                    video_cell = '-'

                # Insert video column after project column
                parts = line.split('|')
                if len(parts) >= 4:
                    # parts: ['', ' Rank ', ' Project ', ' Demo ', ...]
                    new_parts = parts[:3] + [f' {video_cell} '] + parts[3:]
                    line = '|'.join(new_parts)

            new_lines.append(line)
            continue

        # End of table
        if in_table and not line.startswith('|'):
            in_table = False

        new_lines.append(line)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    csv_path = '/mnt/z/ultravioleta/dao/hackathon-judge/submissions.csv'
    md_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/rankings.md'

    print("Loading video links from submissions.csv...")
    video_links = load_video_links(csv_path)
    print(f"  Found {len(video_links)} video links")

    print("Updating rankings.md...")
    update_rankings(md_path, video_links)
    print("Done!")

if __name__ == '__main__':
    main()
