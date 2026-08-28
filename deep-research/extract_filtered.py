#!/usr/bin/env python3
import json

with open('skills/deep-research/research_data.json', 'r') as f:
    data = json.load(f)

# Extract key items from each theme - just titles and first 500 chars of content
for theme_name, items in data['themes'].items():
    print(f'\n### THEME: {theme_name} ({len(items)} items)')
    for i, item in enumerate(items):
        title = item.get('title', 'N/A')
        content = item.get('content', '')
        url = item.get('url', '')
        # Skip irrelevant items (job postings, etc.)
        if any(kw in content.lower() for kw in ['job summary', 'job description', 'required qualifications', 'birmingham', 'dallas', 'texas', 'alabama', 'contract to hire', 'direct hire', 'position summary', 'key responsibilities', 'job duties', 'what you will do', 'qualifications:', 'bachelor', 'degree in']):
            continue
        print(f'\n--- {i+1}. {title}')
        print(f'   URL: {url}')
        print(f'   Content: {content[:800]}')
