#!/usr/bin/env python3
"""Extract key content from research_data.json for synthesis - focused on relevant items."""
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

# Keywords to filter out irrelevant content
irrelevant_kws = [
    'job summary', 'job description', 'required qualifications', 'birmingham',
    'dallas', 'texas', 'alabama', 'contract to hire', 'direct hire',
    'position summary', 'key responsibilities', 'job duties', 'what you will do',
    'qualifications:', 'bachelor', 'degree in', 'hiring', 'apply now',
    'salary', 'compensation', 'benefits', 'remote work', 'work from home',
    'jooble', 'linkedin', 'indeed', 'glassdoor', 'career', 'recruiting'
]

def is_relevant(content):
    return not any(kw in content.lower() for kw in irrelevant_kws)

for theme_key in ['definition', 'evolution', 'mechanics', 'challenges', 'applications', 'future']:
    items = data['themes'].get(theme_key, [])
    relevant = [item for item in items if is_relevant(item['content'])]
    print(f"\n=== THEME: {theme_key} ({len(relevant)}/{len(items)} relevant) ===")
    for i, item in enumerate(relevant[:8]):
        title = item['title'][:200]
        content = item['content'][:2000]
        url = item['url'][:200]
        print(f"\n--- Source {i+1}: {title} ---")
        print(f"URL: {url}")
        print(f"CONTENT:\n{content}")
