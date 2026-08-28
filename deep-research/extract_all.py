#!/usr/bin/env python3
import json

with open('skills/deep-research/research_data.json', 'r') as f:
    data = json.load(f)

# Print ALL items from each theme with full content
for theme_name, items in data['themes'].items():
    print(f'\n=== {theme_name} ({len(items)} items) ===')
    for i, item in enumerate(items):
        title = item.get('title', 'N/A')
        content = item.get('content', '')
        url = item.get('url', '')
        print(f'\n--- Item {i+1}: {title} ---')
        print(f'URL: {url}')
        print(f'Content:\n{content}')
