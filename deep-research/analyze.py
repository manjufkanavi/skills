#!/usr/bin/env python3
import json

with open('skills/deep-research/research_data.json', 'r') as f:
    data = json.load(f)

print('Topic:', data['topic'])
print('Queries:', data['total_queries'])
print('Rounds:', data['rounds'])
print('Web:', data['web_count'], 'PDF:', data['pdf_count'], 'Research:', data['research_count'])
print('Theme keys:', list(data.get('themes', {}).keys()))
for k, v in data['themes'].items():
    print(f'  {k}: {len(v)} items')
print('Sources:', len(data.get('sources', [])))
print('Web items:', len(data.get('web_items', [])))
print('Research items:', len(data.get('research_items', [])))

# Print first few items from each theme for synthesis
for theme_name, items in data['themes'].items():
    print(f'\n=== {theme_name} ===')
    for item in items[:3]:
        print(f'  - {item.get("title", "N/A")}')
        content = item.get('content', '')
        print(f'    {content[:200]}')
